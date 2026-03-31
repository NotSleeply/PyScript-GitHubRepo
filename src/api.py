import requests
from datetime import datetime
from src.logger import logger

def get_repos(username, token, language, min_stars, updated_after, max_repos=0):
    repos = []
    page = 1
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"token {token}"
        
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
        except requests.exceptions.RequestException as e:
            logger.error("Network error while accessing GitHub API: %s", e)
            break
            
        if resp.status_code == 404:
            logger.error("User not found: %s", username)
            break
        elif resp.status_code == 403 and "rate limit" in resp.text.lower():
            logger.error("GitHub API Rate limit exceeded. Please provide a Github Token (--token).")
            break
        elif resp.status_code != 200:
            logger.error("Failed to fetch repos: %s", resp.text)
            break
            
        data = resp.json()
        if not data:
            break
            
        for r in data:
            if language and r.get('language') != language:
                continue
            if r.get('stargazers_count', 0) < min_stars:
                continue
            if updated_after:
                r_date = datetime.strptime(r['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
                f_date = datetime.strptime(updated_after, "%Y-%m-%d")
                if r_date < f_date:
                    continue
            repos.append(r)
            if max_repos > 0 and len(repos) >= max_repos:
                break
        
        if max_repos > 0 and len(repos) >= max_repos:
            break
            
        page += 1
    return repos
