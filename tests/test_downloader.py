"""
Unit tests for src.downloader module

Tests cover:
- ZIP download mode (with mocked HTTP)
- Git clone mode (with mocked GitPython)
- Branch fallback mechanism
- Retry logic on errors
- File extraction and cleanup
"""

import pytest
import os
import tempfile
import shutil
import zipfile
from io import BytesIO
from unittest.mock import patch, MagicMock, call

from src.downloader import (
    download_zip,
    clone_git,
    RetryableError,
    NonRetryableError
)


def _create_test_zip(repo_name, branch_suffix=''):
    """Build an in-memory zip whose top-level dir is `{repo_name}{branch_suffix}`,
    mimicking what github.com/.../archive/refs/heads/<ref>.zip returns."""
    buffer = BytesIO()
    top_level = f"{repo_name}{branch_suffix}"
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{top_level}/README.md", f"# {repo_name}\n")
        zf.writestr(f"{top_level}/main.py", "print('Hello')\n")
    buffer.seek(0)
    return buffer.getvalue()


class TestRetryableErrors:
    """Test suite for custom exception classes."""
    
    def test_retryable_error_creation(self):
        """Test RetryableError can be created with message."""
        error = RetryableError("Temporary failure")
        assert str(error) == "Temporary failure"
        assert isinstance(error, Exception)
    
    def test_non_retryable_error_creation(self):
        """Test NonRetryableError can be created with message."""
        error = NonRetryableError("Permanent failure")
        assert str(error) == "Permanent failure"
        assert isinstance(error, Exception)


class TestZipDownload:
    """Test suite for ZIP download mode."""
    
    @patch('requests.get')
    def test_successful_zip_download(self, mock_get, sample_repo_data, temp_dir, mock_progress_bar):
        """Test successful ZIP file download and extraction."""
        progress, task_id = mock_progress_bar
        
        zip_content = _create_test_zip(sample_repo_data['name'])
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(len(zip_content))}
        mock_response.iter_content.return_value = [zip_content]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        opts = {
            'save_path': temp_dir,
            'token': None,
            'target_ref': 'main',
            'keep_zip': False
        }
        
        result = download_zip(sample_repo_data, opts, progress, task_id)
        
        assert result == "Success"
        extracted_path = os.path.join(temp_dir, sample_repo_data['name'])
        assert os.path.exists(extracted_path)
    
    @patch('requests.get')
    def test_branch_fallback_on_404(self, mock_get, sample_repo_data, temp_dir, mock_progress_bar):
        """Test fallback to default branch when target branch not found."""
        progress, task_id = mock_progress_bar
        
        zip_content_main = _create_test_zip(sample_repo_data['name'])
        
        response_not_found = MagicMock()
        response_not_found.status_code = 404
        
        response_success = MagicMock()
        response_success.status_code = 200
        response_success.headers = {'content-length': str(len(zip_content_main))}
        response_success.iter_content.return_value = [zip_content_main]
        response_success.raise_for_status = MagicMock()
        
        mock_get.side_effect = [response_not_found, response_success]
        
        opts = {
            'save_path': temp_dir,
            'token': None,
            'target_ref': 'nonexistent-branch',
            'keep_zip': False
        }
        
        sample_repo_data['default_branch'] = 'main'
        result = download_zip(sample_repo_data, opts, progress, task_id)
        
        assert result == "Success"
    
    @patch('requests.get')
    def test_keep_zip_option(self, mock_get, sample_repo_data, temp_dir, mock_progress_bar):
        """Test that --keep-zip preserves the ZIP file."""
        progress, task_id = mock_progress_bar
        
        zip_content = _create_test_zip(sample_repo_data['name'])
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(len(zip_content))}
        mock_response.iter_content.return_value = [zip_content]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        opts = {
            'save_path': temp_dir,
            'token': None,
            'target_ref': 'main',
            'keep_zip': True
        }
        
        download_zip(sample_repo_data, opts, progress, task_id)
        
        zip_path = os.path.join(temp_dir, f"{sample_repo_data['name']}.zip")
        assert os.path.exists(zip_path)
    
    @patch('requests.get')
    def test_token_in_download_headers(self, mock_get, sample_repo_data, temp_dir, mock_progress_bar):
        """Test that authentication token is included in download request."""
        progress, task_id = mock_progress_bar
        
        zip_content = _create_test_zip(sample_repo_data['name'])
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(len(zip_content))}
        mock_response.iter_content.return_value = [zip_content]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        opts = {
            'save_path': temp_dir,
            'token': 'ghp_testtoken123',
            'target_ref': 'main',
            'keep_zip': False
        }
        
        download_zip(sample_repo_data, opts, progress, task_id)
        
        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs.get('headers', {})
        assert 'Authorization' in headers
    
    @patch('requests.get')
    def test_server_error_triggers_retry(self, mock_get, sample_repo_data, temp_dir, mock_progress_bar):
        """Test that 5xx server errors trigger retry mechanism."""
        progress, task_id = mock_progress_bar
        
        zip_content = _create_test_zip(sample_repo_data['name'])
        
        error_response = MagicMock()
        error_response.status_code = 502
        
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.headers = {'content-length': str(len(zip_content))}
        success_response.iter_content.return_value = [zip_content]
        success_response.raise_for_status = MagicMock()
        
        mock_get.side_effect = [
            error_response,  # First attempt fails
            error_response,  # Second attempt fails  
            success_response  # Third attempt succeeds
        ]
        
        opts = {
            'save_path': temp_dir,
            'token': None,
            'target_ref': 'main',
            'keep_zip': False
        }
        
        result = download_zip(sample_repo_data, opts, progress, task_id)
        assert result == "Success"
        assert mock_get.call_count == 3
    
    @patch('requests.get')
    def test_extracts_and_renames_correctly(self, mock_get, sample_repo_data, temp_dir, mock_progress_bar):
        """Test that ZIP is extracted and renamed properly (removes branch suffix)."""
        progress, task_id = mock_progress_bar
        
        repo_name = sample_repo_data['name']
        zip_content = _create_test_zip(repo_name, branch_suffix='-main')
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {'content-length': str(len(zip_content))}
        mock_response.iter_content.return_value = [zip_content]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        opts = {
            'save_path': temp_dir,
            'token': None,
            'target_ref': 'main',
            'keep_zip': False
        }
        
        download_zip(sample_repo_data, opts, progress, task_id)
        
        expected_path = os.path.join(temp_dir, repo_name)
        unexpected_path = os.path.join(temp_dir, f"{repo_name}-main")
        
        assert os.path.exists(expected_path)
        assert not os.path.exists(unexpected_path)


class TestGitClone:
    """Test suite for Git clone mode."""
    
    @patch('git.Repo')
    def test_fresh_clone_new_repository(self, MockRepoClass, sample_repo_data, temp_dir, mock_progress_bar):
        """Test cloning a repository that doesn't exist locally yet."""
        progress, task_id = mock_progress_bar
        
        mock_git_repo = MagicMock()
        MockRepoClass.clone_from.return_value = mock_git_repo
        MockRepoClass.side_effect = [False]  # os.path.exists returns False
        
        opts = {
            'save_path': temp_dir,
            'token': None,
            'target_ref': 'main'
        }
        
        repo_path = os.path.join(temp_dir, sample_repo_data['name'])
        with patch('os.path.exists', return_value=False):
            result = clone_git(sample_repo_data, opts, progress, task_id)
        
        assert result == "Success"
        MockRepoClass.clone_from.assert_called_once()
    
    @patch('git.Repo')
    def test_pull_existing_repository(self, MockRepoClass, sample_repo_data, temp_dir, mock_progress_bar):
        """Test pulling updates for an existing local repository."""
        progress, task_id = mock_progress_bar
        
        mock_git_repo = MagicMock()
        mock_origin = MagicMock()
        mock_git_repo.remotes.origin = mock_origin
        MockRepoClass.return_value = mock_git_repo
        
        opts = {
            'save_path': temp_dir,
            'token': None,
            'target_ref': 'main'
        }
        
        repo_path = os.path.join(temp_dir, sample_repo_data['name'], '.git')
        with patch('os.path.exists', return_value=True):
            result = clone_git(sample_repo_data, opts, progress, task_id)
        
        assert result == "Success"
        mock_origin.pull.assert_called_once()
    
    @patch('git.Repo')
    def test_branch_checkout_after_pull(self, MockRepoClass, sample_repo_data, temp_dir, mock_progress_bar):
        """Test checking out specific branch after pulling."""
        progress, task_id = mock_progress_bar
        
        mock_git_repo = MagicMock()
        mock_origin = MagicMock()
        mock_git_repo.remotes.origin = mock_origin
        MockRepoClass.return_value = mock_git_repo
        
        opts = {
            'save_path': temp_dir,
            'token': None,
            'target_ref': 'develop'  # Non-default branch
        }
        
        with patch('os.path.exists', return_value=True):
            result = clone_git(sample_repo_data, opts, progress, task_id)
        
        mock_git_repo.git.checkout.assert_called_with('develop')
    
    @patch('git.Repo')
    def test_branch_fallback_on_clone_failure(self, MockRepoClass, sample_repo_data, temp_dir, mock_progress_bar):
        """Test falling back to default branch when target branch clone fails."""
        from git.exc import GitCommandError
        
        progress, task_id = mock_progress_bar
        
        mock_git_repo = MagicMock()
        MockRepoClass.clone_from.side_effect = [
            GitCommandError("Branch 'feature' not found"),
            mock_git_repo  # Fallback to main succeeds
        ]
        
        opts = {
            'save_path': temp_dir,
            'token': None,
            'target_ref': 'feature'  # Non-existent branch
        }
        
        sample_repo_data['default_branch'] = 'main'
        
        with patch('os.path.exists', return_value=False):
            result = clone_git(sample_repo_data, opts, progress, task_id)
        
        assert result == "Success"
        assert MockRepoClass.clone_from.call_count == 2
    
    @patch('git.Repo')
    def test_token_embedded_in_clone_url(self, MockRepoClass, sample_repo_data, temp_dir, mock_progress_bar):
        """Test that token is embedded in HTTPS clone URL for authentication."""
        progress, task_id = mock_progress_bar
        
        mock_git_repo = MagicMock()
        MockRepoClass.clone_from.return_value = mock_git_repo
        
        opts = {
            'save_path': temp_dir,
            'token': 'ghp_auth_token_xyz',
            'target_ref': 'main'
        }
        
        with patch('os.path.exists', return_value=False):
            clone_git(sample_repo_data, opts, progress, task_id)
        
        call_args = MockRepoClass.clone_from.call_args[0]
        clone_url = call_args[0]
        
        assert 'ghp_auth_token_xyz' in clone_url


class TestDownloaderEdgeCases:
    """Edge case testing for downloader functions."""
    pass

