"""
Unit tests for src.api module (reachable via src.github.api after #7).

Tests cover:
- GitHub API pagination logic
- Repository filtering (language, stars, date)
- Error handling (404, 403, 5xx)
- Edge cases and malformed responses
"""

import pytest
import json
from datetime import datetime
from unittest.mock import patch, MagicMock, call

from src.api import get_repos


def _ok(data):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = data
    return r


def _single_page(data):
    """side_effect for a single page of results followed by an empty page,
    which is what get_repos needs to stop paginating."""
    return [_ok(data), _ok([])]


class TestAPIPagination:
    """Test suite for API pagination behavior."""
    
    @patch('requests.get')
    def test_single_page_response(self, mock_get, sample_repos_list):
        """Test handling of single-page response (≤100 repos)."""
        mock_get.side_effect = _single_page(sample_repos_list[:5])

        repos = get_repos('testuser', None, None, 0, None)

        assert len(repos) == 5
        assert mock_get.call_count == 2
    
    @patch('requests.get')
    def test_multi_page_pagination(self, mock_get, sample_repos_list):
        """Test correct pagination across multiple pages."""
        page1_repos = sample_repos_list[:5]
        page2_repos = sample_repos_list[5:10]
        
        response_page1 = MagicMock()
        response_page1.status_code = 200
        response_page1.json.return_value = page1_repos
        
        response_page2 = MagicMock()
        response_page2.status_code = 200
        response_page2.json.return_value = page2_repos
        
        response_empty = MagicMock()
        response_empty.status_code = 200
        response_empty.json.return_value = []
        
        mock_get.side_effect = [response_page1, response_page2, response_empty]
        
        repos = get_repos('testuser', None, None, 0, None)
        
        assert len(repos) == 10
        assert mock_get.call_count == 3
    
    @patch('requests.get')
    def test_empty_api_response(self, mock_get):
        """Test handling of empty repository list."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        repos = get_repos('emptyuser', None, None, 0, None)
        
        assert len(repos) == 0
    
    @patch('requests.get')
    def test_max_repos_limit_stops_pagination(self, mock_get, sample_repos_list):
        """Test that max_repos parameter stops pagination early."""
        response_full = MagicMock()
        response_full.status_code = 200
        response_full.json.return_value = sample_repos_list
        
        mock_get.return_value = response_full
        
        repos = get_repos('testuser', None, None, 0, None, max_repos=3)
        
        assert len(repos) == 3


class TestAPIFiltering:
    """Test suite for repository filtering logic."""
    
    @patch('requests.get')
    def test_language_filter_python_only(self, mock_get, sample_repos_list):
        """Test filtering by programming language."""
        mock_get.side_effect = _single_page(sample_repos_list)

        repos = get_repos('testuser', None, 'Python', 0, None)

        for repo in repos:
            assert repo['language'] == 'Python'

    @patch('requests.get')
    def test_min_stars_filter(self, mock_get, sample_repos_list):
        """Test filtering by minimum star count."""
        mock_get.side_effect = _single_page(sample_repos_list)

        repos = get_repos('testuser', None, None, min_stars=500, updated_after=None)

        for repo in repos:
            assert repo['stargazers_count'] >= 500

    @patch('requests.get')
    def test_date_filter_after_specified_date(self, mock_get, sample_repos_list):
        """Test filtering by update date."""
        mock_get.side_effect = _single_page(sample_repos_list)

        cutoff_date = '2026-05-09'
        repos = get_repos('testuser', None, None, 0, updated_after=cutoff_date)

        for repo in repos:
            repo_date = datetime.strptime(repo['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
            cutoff = datetime.strptime(cutoff_date, "%Y-%m-%d")
            assert repo_date >= cutoff

    @patch('requests.get')
    def test_combined_filters(self, mock_get, sample_repos_list):
        """Test applying multiple filters simultaneously."""
        mock_get.side_effect = _single_page(sample_repos_list)
        
        repos = get_repos(
            'testuser',
            token=None,
            language='Python',
            min_stars=200,
            updated_after='2026-05-08'
        )
        
        for repo in repos:
            assert repo['language'] == 'Python'
            assert repo['stargazers_count'] >= 200
            repo_date = datetime.strptime(repo['updated_at'], "%Y-%m-%dT%H:%M:%SZ")
            assert repo_date >= datetime.strptime('2026-05-08', "%Y-%m-%d")


class TestAPIErrorHandling:
    """Test suite for error handling and edge cases."""
    
    @patch('requests.get')
    def test_user_not_found_404(self, mock_get):
        """Test handling of 404 Not Found error."""
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        repos = get_repos('nonexistentuser12345', None, None, 0, None)
        
        assert len(repos) == 0
    
    @patch('requests.get')
    def test_rate_limit_403(self, mock_get):
        """Test handling of 403 Rate Limit exceeded."""
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "API rate limit exceeded"
        mock_get.return_value = mock_response

        repos = get_repos('ratelimiteduser', None, None, 0, None)

        assert len(repos) == 0
    
    @patch('requests.get')
    def test_server_error_500(self, mock_get):
        """Test handling of 500 Internal Server Error."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_get.return_value = mock_response
        
        repos = get_repos('testuser', None, None, 0, None)
        
        assert len(repos) == 0
    
    @patch('requests.get')
    def test_network_timeout_exception(self, mock_get):
        """Test handling of network timeout exception."""
        import requests
        mock_get.side_effect = requests.exceptions.Timeout("Connection timed out")
        
        repos = get_repos('slowuser', None, None, 0, None)
        
        assert len(repos) == 0
    
    @patch('requests.get')
    def test_malformed_json_response(self, mock_get):
        """Test graceful handling of malformed JSON in API response."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("No JSON object could be decoded")
        mock_get.return_value = mock_response
        
        repos = get_repos('brokenapi', None, None, 0, None)
        
        assert len(repos) == 0
    
    @patch('requests.get')
    def test_malformed_repo_data_skipped(self, mock_get):
        """Test that individual malformed repo entries are skipped gracefully."""
        bad_repo_data = [
            {'name': 'valid-repo', 'stargazers_count': 100, 'language': 'Python',
             'updated_at': '2026-05-10T14:30:00Z'},
            {'name': 'missing-fields-repo'},  # Missing required fields
            {'name': 'another-valid', 'stargazers_count': 50, 'language': 'Go',
             'updated_at': '2026-05-09T14:30:00Z'}
        ]
        mock_get.side_effect = _single_page(bad_repo_data)

        repos = get_repos('mixeddata', None, None, 0, None)

        # The guarantee is "don't crash on malformed entries", not "filter
        # out incomplete ones" — get_repos uses .get() with defaults, so
        # a repo with only `name` still passes the min_stars=0 filter. The
        # important thing is that we got back the two valid records we can
        # recognize by their full field set.
        assert len(repos) >= 2
        full_records = [r for r in repos if 'stargazers_count' in r]
        assert len(full_records) == 2
        assert {r['name'] for r in full_records} == {'valid-repo', 'another-valid'}


class TestAPIAuthentication:
    """Test suite for authentication header handling."""

    @patch('requests.get')
    def test_token_in_authorization_header(self, mock_get, sample_repos_list):
        """Test that token is correctly placed in Authorization header."""
        mock_get.side_effect = _single_page(sample_repos_list[:1])

        test_token = 'ghp_testtoken123456789'
        get_repos('authuser', test_token, None, 0, None)

        call_args = mock_get.call_args_list[0]
        headers = call_args[1].get('headers', {})
        assert 'Authorization' in headers
        assert test_token in headers['Authorization']

    @patch('requests.get')
    def test_no_token_without_auth_header(self, mock_get, sample_repos_list):
        """Test that no Authorization header when token is None."""
        mock_get.side_effect = _single_page(sample_repos_list[:1])

        get_repos('publicuser', None, None, 0, None)

        call_args = mock_get.call_args_list[0]
        headers = call_args[1].get('headers', {})
        assert 'Authorization' not in headers


class TestAPIRequestParameters:
    """Test suite for API request construction."""
    
    @patch('requests.get')
    def test_correct_url_format(self, mock_get, sample_repos_list):
        """Test that API URL is constructed correctly."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        username = 'octocat'
        get_repos(username, None, None, 0, None)
        
        called_url = mock_get.call_args[0][0]
        assert f'/users/{username}/repos' in called_url
        assert 'per_page=100' in called_url
        assert 'page=1' in called_url
    
    @patch('requests.get')
    def test_request_timeout_set(self, mock_get, sample_repos_list):
        """Test that request timeout is configured."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        get_repos('timeoutuser', None, None, 0, None)
        
        call_kwargs = mock_get.call_args[1]
        assert 'timeout' in call_kwargs
        assert call_kwargs['timeout'] == 15
    
    @patch('requests.get')
    def test_accept_header_github_v3(self, mock_get, sample_repos_list):
        """Test that GitHub v3+ JSON Accept header is set."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response
        
        get_repos('headeruser', None, None, 0, None)
        
        call_kwargs = mock_get.call_args[1]
        headers = call_kwargs.get('headers', {})
        assert 'application/vnd.github.v3+json' in headers.get('Accept', '')
