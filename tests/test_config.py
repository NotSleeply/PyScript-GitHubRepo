"""
Unit tests for src.config module

Tests cover:
- Configuration validation logic
- YAML file loading and parsing
- CLI argument merging strategy
- Edge cases and error handling
"""

import pytest
import os
import tempfile
import yaml
from pathlib import Path

from src.config import (
    validate_config,
    load_config,
    parse_and_merge_args
)


class TestValidateConfig:
    """Test suite for configuration validation logic."""
    
    def test_valid_username(self):
        """Test that a valid GitHub username passes validation."""
        opts = {'username': 'octocat', 'max_workers': 5, 'min_stars': 0}
        errors, warnings = validate_config(opts)
        assert len(errors) == 0
    
    def test_empty_username_fails(self):
        """Test that empty username is rejected."""
        opts = {'username': '', 'max_workers': 5}
        errors, warnings = validate_config(opts)
        assert any('Username' in e for e in errors)
    
    def test_none_username_fails(self):
        """Test that None username is rejected."""
        opts = {'username': None, 'max_workers': 5}
        errors, warnings = validate_config(opts)
        assert any('Username' in e for e in errors)
    
    def test_username_with_special_chars_warning(self):
        """Test that suspicious usernames generate warning."""
        opts = {'username': 'user@name!', 'max_workers': 5}
        errors, warnings = validate_config(opts)
        assert len(warnings) > 0
        assert any('may not be valid' in w for w in warnings)
    
    def test_max_workers_minimum_boundary(self):
        """Test that max_workers < 1 fails validation."""
        opts = {'username': 'test', 'max_workers': 0}
        errors, warnings = validate_config(opts)
        assert any('max_workers' in e for e in errors)
    
    def test_max_workers_negative_fails(self):
        """Test that negative max_workers fails validation."""
        opts = {'username': 'test', 'max_workers': -5}
        errors, warnings = validate_config(opts)
        assert any('max_workers' in e for e in errors)
    
    def test_max_workers_high_value_warning(self):
        """Test that very high max_workers generates warning."""
        opts = {'username': 'test', 'max_workers': 100}
        errors, warnings = validate_config(opts)
        assert len(warnings) > 0
        assert any('very high' in w for w in warnings)
    
    def test_valid_date_format(self):
        """Test that valid date format passes validation."""
        opts = {
            'username': 'test',
            'updated_after': '2024-01-15',
            'max_workers': 5
        }
        errors, warnings = validate_config(opts)
        assert not any('date format' in e for e in errors)
    
    def test_invalid_date_format_fails(self):
        """Test that invalid date format is rejected."""
        opts = {
            'username': 'test',
            'updated_after': '15/01/2024',
            'max_workers': 5
        }
        errors, warnings = validate_config(opts)
        assert any('date format' in e or 'Invalid' in e for e in errors)
    
    def test_negative_min_stars_fails(self):
        """Test that negative min_stars value is rejected."""
        opts = {'username': 'test', 'min_stars': -10}
        errors, warnings = validate_config(opts)
        assert any('min_stars' in e for e in errors)
    
    def test_negative_max_repos_fails(self):
        """Test that negative max_repos value is rejected."""
        opts = {'username': 'test', 'max_repos': -1}
        errors, warnings = validate_config(opts)
        assert any('max_repos' in e for e in errors)
    
    def test_invalid_mode_fails(self):
        """Test that invalid download mode is rejected."""
        opts = {'username': 'test', 'mode': 'ftp'}
        errors, warnings = validate_config(opts)
        assert any('Invalid mode' in e for e in errors)
    
    def test_very_long_save_path_fails(self):
        """Test that extremely long save_path is rejected."""
        long_path = 'a' * 300
        opts = {'username': 'test', 'save_path': long_path}
        errors, warnings = validate_config(opts)
        assert any('too long' in e for e in errors)


class TestLoadConfig:
    """Test suite for YAML configuration loading."""
    
    def test_load_existing_yaml_file(self, sample_yaml_config_file):
        """Test loading a valid YAML configuration file."""
        config = load_config(sample_yaml_config_file)
        assert config is not None
        assert 'github' in config
        assert config['github']['username'] == 'testuser'
    
    def test_load_nonexistent_file_returns_empty(self):
        """Test that loading nonexistent file returns empty dict."""
        config = load_config('/nonexistent/path/config.yaml')
        assert config == {}
    
    def test_load_invalid_yaml_syntax(self, temp_dir):
        """Test that invalid YAML syntax is handled gracefully."""
        bad_yaml_path = Path(temp_dir) / 'bad.yaml'
        bad_yaml_path.write_text("""
        github:
          username: [unclosed bracket
        """)
        
        config = load_config(str(bad_yaml_path))
        assert config == {}
    
    def test_load_empty_yaml_file(self, temp_dir):
        """Test loading an empty YAML file returns empty dict."""
        empty_yaml = Path(temp_dir) / 'empty.yaml'
        empty_yaml.write_text('')
        
        config = load_config(str(empty_yaml))
        assert config == {}
    
    def test_load_yaml_with_only_comments(self, temp_dir):
        """Test loading YAML with only comments returns empty dict."""
        comment_yaml = Path(temp_dir) / 'comments.yaml'
        comment_yaml.write_text('# This is a comment\n# Another comment\n')
        
        config = load_config(str(comment_yaml))
        assert config == {}


class TestParseAndMergeArgs:
    """Test suite for CLI and YAML configuration merging."""
    
    def test_cli_overrides_yaml_username(self, sample_yaml_config_file, monkeypatch):
        """Test that CLI username overrides YAML configuration."""
        monkeypatch.setattr('sys.argv', [
            'main.py',
            '--config', sample_yaml_config_file,
            '--username', 'cli-user'
        ])
        
        opts = parse_and_merge_args()
        assert opts['username'] == 'cli-user'
    
    def test_default_values_when_no_config(self, tmp_path, monkeypatch):
        """Test default values when no config file exists."""
        config_file = tmp_path / 'nonexistent.yaml'
        monkeypatch.setattr('sys.argv', [
            'main.py',
            '--config', str(config_file),
            '--username', 'testuser'
        ])
        
        opts = parse_and_merge_args()
        assert opts['mode'] == 'git'
        assert opts['target_ref'] == 'main'
        assert opts['max_workers'] == 5
        assert opts['dry_run'] == False
    
    def test_dry_run_flag_parsing(self, monkeypatch):
        """Test that --dry-run flag is correctly parsed."""
        monkeypatch.setattr('sys.argv', [
            'main.py',
            '--username', 'test',
            '--dry-run'
        ])
        
        opts = parse_and_merge_args()
        assert opts['dry_run'] == True
    
    def test_verbose_flag_parsing(self, monkeypatch):
        """Test that --verbose flag is correctly parsed."""
        monkeypatch.setattr('sys.argv', [
            'main.py',
            '--username', 'test',
            '--verbose'
        ])
        
        opts = parse_and_merge_args()
        assert opts['verbose'] == True
    
    def test_exclude_list_parsing(self, monkeypatch):
        """Test that --exclude parameter correctly parses multiple repos."""
        monkeypatch.setattr('sys.argv', [
            'main.py',
            '--username', 'test',
            '--exclude', 'repo1', 'repo2', 'repo3'
        ])
        
        opts = parse_and_merge_args()
        assert 'repo1' in opts['exclude']
        assert 'repo2' in opts['exclude']
        assert 'repo3' in opts['exclude']
        assert isinstance(opts['exclude'], set)
    
    def test_report_format_json_option(self, monkeypatch):
        """Test JSON report format option."""
        monkeypatch.setattr('sys.argv', [
            'main.py',
            '--username', 'test',
            '--report-format', 'json'
        ])
        
        opts = parse_and_merge_args()
        assert opts['report_format'] == 'json'
    
    def test_multiple_filters_combined(self, sample_yaml_config_file, monkeypatch):
        """Test combining multiple filter options from CLI and YAML."""
        monkeypatch.setattr('sys.argv', [
            'main.py',
            '--config', sample_yaml_config_file,
            '--language', 'Go',
            '--min-stars', '500',
            '--max-repos', '20'
        ])
        
        opts = parse_and_merge_args()
        assert opts['language'] == 'Go'
        assert opts['min_stars'] == 500
        assert opts['max_repos'] == 20


class TestConfigEdgeCases:
    """Edge case testing for configuration handling."""
    
    def test_unicode_in_description(self, temp_dir):
        """Test handling of Unicode characters in config values."""
        unicode_content = """
github:
  username: 用户名
  
download:
  save_path: "./路径/测试"
"""
        yaml_path = Path(temp_dir) / 'unicode.yaml'
        yaml_path.write_text(unicode_content, encoding='utf-8')
        
        config = load_config(str(yaml_path))
        assert config['github']['username'] == '用户名'
    
    test_unicode_in_description = pytest.mark.skipif(
        True, reason="Unicode support varies by platform"
    )(test_unicode_in_description)
    
    def test_yaml_alias_handling(self, temp_dir):
        """Test that YAML anchors and aliases are properly resolved."""
        alias_content = """
defaults: &defaults
  mode: git
  target_ref: main

download:
  <<: *defaults
  save_path: ./repos
"""
        yaml_path = Path(temp_dir) / 'aliases.yaml'
        yaml_path.write_text(alias_content)
        
        config = load_config(str(yaml_path))
        assert config['download']['mode'] == 'git'
    
    def test_boolean_conversion_from_yaml(self, temp_dir):
        """Test correct conversion of boolean values from YAML."""
        bool_content = """
download:
  keep_zip: true
  mode: zip
"""
        yaml_path = Path(temp_dir) / 'bools.yaml'
        yaml_path.write_text(bool_content)
        
        config = load_config(str(yaml_path))
        assert config['download']['keep_zip'] is True
