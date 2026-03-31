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
    target_ref = opts.get('target_ref')
    if not target_ref:
        target_ref = repo.get('default_branch', 'main')
    fallback_ref = repo.get('default_branch', 'main')
    
    save_path = opts['save_path']
    
    headers = {}
    if opts.get('token'):
        headers["Authorization"] = f"token {opts['token']}"
        
    def try_download(ref):
        urls_to_try = [
            f"https://github.com/{repo['owner']['login']}/{repo_name}/archive/refs/heads/{ref}.zip",
            f"https://github.com/{repo['owner']['login']}/{repo_name}/archive/refs/tags/{ref}.zip"
        ]
        for url in urls_to_try:
            resp = requests.get(url, headers=headers, stream=True)
            if resp.status_code == 200:
                return resp
            if resp.status_code in [500, 502, 503, 504]:
                raise RetryableError(f"Server error {resp.status_code}")
        return None

    try:
        resp = try_download(target_ref)
        # 如果指定的 target_ref 没找到，而且和仓库的默认分支不同，则退化尝试默认分支
        if not resp and target_ref != fallback_ref:
            progress.update(task_id, description=f"Target {target_ref} missed, trying fallback: {fallback_ref}")
            resp = try_download(fallback_ref)
            
        if not resp:
            raise NonRetryableError(f"Branch or Tag '{target_ref}' (and fallback '{fallback_ref}') not found for {repo_name}.")
            
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
    target_ref = opts.get('target_ref')
    if not target_ref:
        target_ref = repo.get('default_branch', 'main')
    fallback_ref = repo.get('default_branch', 'main')
    
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
            try:
                git_repo.git.checkout(target_ref)
            except GitCommandError:
                if target_ref != fallback_ref:
                    git_repo.git.checkout(fallback_ref)
                else:
                    raise
        else:
            try:
                git_repo = Repo.clone_from(clone_url, repo_path, branch=target_ref)
            except GitCommandError as e:
                # Checkout original default fallback if specific ref not found
                if ('not found' in str(e).lower() or 'could not read from remote' in str(e).lower() or 'remote branch' in str(e).lower()) and target_ref != fallback_ref:
                    git_repo = Repo.clone_from(clone_url, repo_path, branch=fallback_ref)
                else:
                    raise e
        return "Success"
    except GitCommandError as e:
        if 'not found' in str(e).lower() or 'could not read from remote' in str(e).lower():
            raise NonRetryableError(f"Branch/Tag issue or permission error: {e}")
        raise RetryableError(f"Git execution error: {e}")
    except Exception as e:
        raise RetryableError(f"Unknown git error: {e}")
