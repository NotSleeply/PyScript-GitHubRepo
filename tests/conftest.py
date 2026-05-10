"""
Global Pytest Configuration and Fixtures

This module provides shared fixtures and configuration for all test modules.
"""

import pytest
import os
import tempfile
import shutil
import json
from datetime import datetime
from unittest.mock import MagicMock, patch
from pathlib import Path


@pytest.fixture
def temp_dir():
    """Create a temporary directory that is automatically cleaned up."""
    dirpath = tempfile.mkdtemp()
    yield dirpath
    shutil.rmtree(dirpath, ignore_errors=True)


@pytest.fixture
def sample_repo_data():
    """Standard repository data fixture matching GitHub API response format."""
    return {
        'id': 123456789,
        'name': 'test-repo',
        'full_name': 'octocat/test-repo',
        'description': 'A test repository for unit testing purposes',
        'language': 'Python',
        'stargazers_count': 1000,
        'updated_at': '2026-05-10T14:30:00Z',
        'pushed_at': '2026-05-09T10:20:00Z',
        'size': 1024,
        'default_branch': 'main',
        'clone_url': 'https://github.com/octocat/test-repo.git',
        'svn_url': 'https://github.com/octocat/test-repo',
        'homepage': 'https://example.com',
        'private': False,
        'archived': False,
        'owner': {
            'login': 'octocat',
            'id': 583231,
            'type': 'User'
        }
    }


@pytest.fixture
def sample_repos_list(sample_repo_data):
    """Generate a list of multiple repositories for pagination/filtering tests."""
    repos = []
    languages = ['Python', 'JavaScript', 'TypeScript', 'Go', 'Rust']
    
    for i in range(10):
        repo = sample_repo_data.copy()
        repo['id'] = 1000 + i
        repo['name'] = f'repo-{i:02d}'
        repo['full_name'] = f'octocat/repo-{i:02d}'
        repo['stargazers_count'] = (i + 1) * 100
        repo['size'] = (i + 1) * 512
        repo['language'] = languages[i % len(languages)]
        repo['updated_at'] = f'2026-05-{10 - i//3}T14:30:00Z'
        repos.append(repo)
    
    return repos


@pytest.fixture
def valid_config():
    """Valid configuration dictionary with all options set."""
    return {
        'username': 'testuser',
        'token': 'ghp_testtoken123456789',
        'mode': 'git',
        'save_path': './test_repos',
        'target_ref': 'main',
        'keep_zip': False,
        'language': None,
        'min_stars': 0,
        'updated_after': None,
        'max_repos': 0,
        'exclude': set(),
        'max_workers': 5,
        'report_format': 'markdown',
        'report_dir': './reports',
        'dry_run': False,
        'verbose': True
    }


@pytest.fixture
def minimal_config():
    """Minimal valid configuration with only required fields."""
    return {
        'username': 'testuser',
        'token': None,
        'mode': 'git',
        'save_path': './repos',
        'target_ref': 'main',
        'keep_zip': False,
        'language': None,
        'min_stars': 0,
        'updated_after': None,
        'max_repos': 0,
        'exclude': set(),
        'max_workers': 5,
        'report_format': 'markdown',
        'report_dir': '.',
        'dry_run': False,
        'verbose': False
    }


@pytest.fixture
def mock_github_api_response(success=True, status_code=200):
    """Create a mock GitHub API response object."""
    response = MagicMock()
    response.status_code = status_code
    response.headers = {'Content-Type': 'application/json'}
    
    if success:
        response.json.return_value = []
        response.raise_for_status.return_value = None
    
    return response


@pytest.fixture
def sample_sync_history():
    """Sample sync history data structure."""
    return {
        'repo-01': {'updated_at': '2026-05-10T14:30:00Z'},
        'repo-02': {'updated_at': '2026-05-09T10:20:00Z'},
        'repo-03': {'updated_at': '2026-05-08T08:15:00Z'}
    }


@pytest.fixture
def sample_yaml_config_file(temp_dir):
    """Create a temporary YAML config file for testing."""
    config_content = """
github:
  username: testuser
  token: ghp_testtoken123

download:
  mode: git
  save_path: ./test_output
  target_ref: main

filter:
  language: Python
  min_stars: 100
  max_repos: 10

concurrency:
  max_workers: 5

report:
  format: markdown
"""
    config_path = Path(temp_dir) / 'config.yaml'
    config_path.write_text(config_content)
    return str(config_path)


@pytest.fixture
def sample_csv_report_data():
    """Sample data for CSV report generation tests."""
    return [
        {'name': 'repo-alpha', 'description': 'First repo', 'language': 'Python',
         'stars': 1000, 'updated': '2026-05-10', 'status': 'success'},
        {'name': 'repo-beta', 'description': 'Second repo', 'language': 'Go',
         'stars': 500, 'updated': '2026-05-09', 'status': 'skipped'},
        {'name': 'repo-gamma', 'description': 'Third repo', 'language': 'TypeScript',
         'stars': 200, 'updated': '2026-05-08', 'status': 'failed'}
    ]


@pytest.fixture
def mock_progress_bar():
    """Mock Rich progress bar for testing downloader functions."""
    progress = MagicMock()
    task_id = MagicMock()
    
    def add_task(description, **kwargs):
        return task_id
    
    progress.add_task.side_effect = add_task
    progress.update = MagicMock()
    progress.advance = MagicMock()
    
    return progress, task_id
