import os
import requests
import zipfile
import shutil
from git import Repo
from git.exc import GitCommandError
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

class RetryableError(Exception):
    pass

class NonRetryableError(Exception):
    pass

@retry(retry=retry_if_exception_type(RetryableError), stop=stop_after_attempt(3), wait=wait_fixed(2))
def download_zip(repo, opts, progress, task_id):
    repo_name = repo['name']
    target_ref = opts['target_ref']
    save_path = opts['save_path']
    zip_url = f"https://github.com/{repo['owner']['login']}/{repo_name}/archive/refs/heads/{target_ref}.zip"
    
    headers = {}
    if opts.get('token'):
        headers["Authorization"] = f"token {opts['token']}"
        
    try:
        resp = requests.get(zip_url, headers=headers, stream=True)
        if resp.status_code == 404:
            zip_url_tag = f"https://github.com/{repo['owner']['login']}/{repo_name}/archive/refs/tags/{target_ref}.zip"
            resp = requests.get(zip_url_tag, headers=headers, stream=True)
            if resp.status_code == 404:
                raise NonRetryableError(f"Branch or Tag '{target_ref}' not found for {repo_name}.")
                
        if resp.status_code in [500, 502, 503, 504]:
            raise RetryableError(f"Server error {resp.status_code}")
        resp.raise_for_status()
        
        total_size = int(resp.headers.get('content-length', 0))
        progress.update(task_id, total=total_size if total_size > 0 else 100, description=f"Downloading {repo_name}.zip")
        
        zip_path = os.path.join(save_path, f"{repo_name}.zip")
        with open(zip_path, 'wb') as f:
            for chunk in resp.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    if total_size > 0:
                        progress.advance(task_id, len(chunk))
                    
        extract_dir = os.path.join(save_path, repo_name)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            top_level = next(iter(zip_ref.namelist())).split('/')[0]
            zip_ref.extractall(save_path)
            
        unzipped_folder = os.path.join(save_path, top_level)
        if os.path.exists(extract_dir):
            if unzipped_folder != extract_dir:
                shutil.rmtree(extract_dir)
                os.rename(unzipped_folder, extract_dir)
        else:
            os.rename(unzipped_folder, extract_dir)
        
        if not opts['keep_zip']:
            os.remove(zip_path)
            
        return "Success"
    except NonRetryableError as e:
        raise e
    except Exception as e:
        raise RetryableError(str(e))

@retry(retry=retry_if_exception_type(RetryableError), stop=stop_after_attempt(3), wait=wait_fixed(2))
def clone_git(repo, opts, progress, task_id):
    repo_name = repo['name']
    target_ref = opts['target_ref']
    save_path = opts['save_path']
    clone_url = repo['clone_url'] 
    
    if opts.get('token') and clone_url.startswith("https://"):
        clone_url = clone_url.replace("https://", f"https://{opts['token']}@")
        
    repo_path = os.path.join(save_path, repo_name)
    progress.update(task_id, total=None, description=f"Git operation: {repo_name}")
    
    try:
        if os.path.exists(os.path.join(repo_path, '.git')):
            git_repo = Repo(repo_path)
            origin = git_repo.remotes.origin
            origin.pull()
            git_repo.git.checkout(target_ref)
        else:
            git_repo = Repo.clone_from(clone_url, repo_path)
            git_repo.git.checkout(target_ref)
        return "Success"
    except GitCommandError as e:
        if 'not found' in str(e).lower() or 'Could not read from remote' in str(e):
            raise NonRetryableError(f"Branch/Tag {target_ref} issue or permission error: {e}")
        raise RetryableError(f"Git execution error: {e}")
    except Exception as e:
        raise RetryableError(f"Unknown git error: {e}")
