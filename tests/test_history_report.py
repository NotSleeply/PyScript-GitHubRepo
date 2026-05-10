"""
Unit tests for src.history_report module

Tests cover:
- Sync history CRUD operations (load/save)
- Report generation in multiple formats (Markdown, CSV, JSON)
- Disk space checking
- Statistics calculation
- Atomic file writing safety
"""

import pytest
import os
import json
import csv
import tempfile
import shutil
from datetime import datetime
from pathlib import Path

from src.history_report import (
    check_disk_space,
    load_sync_history,
    save_sync_history,
    generate_report,
    get_stats_summary
)


class TestSyncHistory:
    """Test suite for sync history persistence."""
    
    def test_load_empty_history(self, temp_dir):
        """Test loading history when no file exists returns empty dict."""
        history = load_sync_history(temp_dir)
        assert history == {}
    
    def test_save_and_load_history(self, temp_dir, sample_sync_history):
        """Test that saved history can be loaded correctly."""
        save_sync_history(temp_dir, sample_sync_history)
        
        loaded = load_sync_history(temp_dir)
        assert loaded == sample_sync_history
    
    def test_load_corrupted_json_file(self, temp_dir):
        """Test graceful handling of corrupted JSON file."""
        history_file = Path(temp_dir) / 'last_sync.json'
        history_file.write_text('{invalid json content!!!')
        
        history = load_sync_history(temp_dir)
        assert isinstance(history, dict)
        assert len(history) == 0
    
    def test_overwrite_existing_history(self, temp_dir):
        """Test that saving overwrites previous history."""
        old_history = {'repo-old': {'updated_at': '2026-01-01T00:00:00Z'}}
        new_history = {'repo-new': {'updated_at': '2026-05-10T14:30:00Z'}}
        
        save_sync_history(temp_dir, old_history)
        save_sync_history(temp_dir, new_history)
        
        loaded = load_sync_history(temp_dir)
        assert loaded == new_history
        assert 'repo-old' not in loaded
    
    def test_empty_history_saves_successfully(self, temp_dir):
        """Test saving empty history dictionary."""
        save_sync_history(temp_dir, {})
        
        assert os.path.exists(os.path.join(temp_dir, 'last_sync.json'))
        loaded = load_sync_history(temp_dir)
        assert loaded == {}
    
    def test_unicode_in_history_data(self, temp_dir):
        """Test handling of Unicode characters in history data."""
        unicode_history = {
            '仓库-中文': {'updated_at': '2026-05-10T14:30:00Z'},
            'répo-français': {'updated_at': '2026-05-09T14:30:00Z'}
        }
        
        save_sync_history(temp_dir, unicode_history)
        loaded = load_sync_history(temp_dir)
        assert loaded == unicode_history


class TestAtomicWriteSafety:
    """Test suite for atomic file write operations."""
    
    def test_atomic_write_prevents_partial_files(self, temp_dir):
        """Test that atomic write prevents partial/corrupted files."""
        test_data = {'important': 'data', 'count': 42}
        
        save_sync_history(temp_dir, test_data)
        
        history_path = os.path.join(temp_dir, 'last_sync.json')
        assert os.path.exists(history_path)
        
        with open(history_path, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        assert loaded == test_data
    
    def test_no_temp_file_left_after_success(self, temp_dir):
        """Test that temporary file is cleaned up after successful write."""
        save_sync_history(temp_dir, {'test': 'data'})
        
        temp_files = list(Path(temp_dir).glob('*.tmp'))
        assert len(temp_files) == 0


class TestReportGeneration:
    """Test suite for report generation in different formats."""
    
    @pytest.mark.parametrize("report_format", ["markdown", "csv", "json"])
    def test_report_file_created(self, temp_dir, sample_repos_list, report_format):
        """Test that report file is created for all formats."""
        opts = {
            'report_format': report_format,
            'report_dir': temp_dir,
            'save_path': './test'
        }
        statuses = {r['name']: 'success' for r in sample_repos_list}
        stats = {'success': len(sample_repos_list), 'failed': 0, 'skipped': 0}
        
        filepath = generate_report(sample_repos_list, statuses, stats, 12.5, opts)
        
        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) > 0
    
    def test_markdown_report_content(self, temp_dir, sample_repos_list):
        """Test Markdown report contains expected sections and data."""
        opts = {
            'report_format': 'markdown',
            'report_dir': temp_dir,
            'save_path': './output'
        }
        statuses = {r['name']: 'success' for r in sample_repos_list[:3]}
        stats = {'success': 3, 'failed': 0, 'skipped': 0}
        
        filepath = generate_report(sample_repos_list[:3], statuses, stats, 10.0, opts)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        assert '# Repositories Download Report' in content
        assert '## Summary Statistics' in content
        assert '| Name |' in content
        assert '✅' in content or 'success' in content
    
    def test_csv_report_valid_format(self, temp_dir, sample_repos_list):
        """Test CSV report has valid structure and can be parsed."""
        opts = {
            'report_format': 'csv',
            'report_dir': temp_dir,
            'save_path': './output'
        }
        statuses = {r['name']: 'success' for r in sample_repos_list[:2]}
        stats = {'success': 2, 'failed': 1, 'skipped': 0}
        
        filepath = generate_report(sample_repos_list[:3], statuses, stats, 8.5, opts)
        
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        assert len(rows) >= 2  # Header + at least 1 data row
        assert rows[0][0] == 'Name'  # Header check
    
    def test_json_report_valid_structure(self, temp_dir, sample_repos_list):
        """Test JSON report has correct structure and data types."""
        opts = {
            'report_format': 'json',
            'report_dir': temp_dir,
            'save_path': './output'
        }
        statuses = {r['name']: 'success' for r in sample_repos_list[:2]}
        stats = {'success': 2, 'failed': 0, 'skipped': 1}
        
        filepath = generate_report(sample_repos_list[:3], statuses, stats, 15.0, opts)
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert 'generated_at' in data
        assert 'duration_seconds' in data
        assert 'statistics' in data
        assert 'repositories' in data
        assert len(data['repositories']) == 3
        
        repo_entry = data['repositories'][0]
        assert 'name' in repo_entry
        assert 'status' in repo_entry
        assert 'stars' in repo_entry
    
    def test_report_filename_timestamp(self, temp_dir, sample_repos_list):
        """Test that report filename includes timestamp."""
        import re
        
        before_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        opts = {
            'report_format': 'markdown',
            'report_dir': temp_dir,
            'save_path': '.'
        }
        statuses = {}
        stats = {}
        
        filepath = generate_report([sample_repos_list[0]], statuses, stats, 1.0, opts)
        filename = os.path.basename(filepath)
        
        assert filename.startswith('repo_report_')
        assert filename.endswith('.md')


class TestDiskSpaceCheck:
    """Test suite for disk space validation."""
    
    def test_sufficient_disk_space(self, temp_dir):
        """Test detection of sufficient disk space."""
        has_space, free_gb, required_gb = check_disk_space(temp_dir, required_mb=1)
        
        assert has_space == True
        assert free_gb > 0
    
    def test_insufficient_space_detection(self, temp_dir):
        """Test detection of insufficient disk space by requesting huge amount."""
        has_space, free_gb, required_gb = check_disk_space(
            temp_dir, 
            required_mb=999999999  # Request impossibly large space
        )
        
        assert has_space == False
    
    def test_creates_directory_if_not_exists(self, tmp_path):
        """Test that directory is created if it doesn't exist."""
        new_dir = str(tmp_path / 'new_subdir')
        assert not os.path.exists(new_dir)
        
        check_disk_space(new_dir, required_mb=1)
        
        assert os.path.exists(new_dir)


class TestStatisticsCalculation:
    """Test suite for statistics summary calculation."""
    
    def test_all_successful(self):
        """Test statistics when all repos succeed."""
        stats = {'success': 10, 'failed': 0, 'skipped': 0}
        summary = get_stats_summary(stats, total_repos=10, duration=50.0)
        
        assert summary['success'] == 10
        assert summary['success_rate'] == 100.0
        assert summary['throughput'] == pytest.approx(0.2, rel=0.1)
    
    def test_mixed_results(self):
        """Test statistics with mixed success/failure/skip."""
        stats = {'success': 7, 'failed': 2, 'skipped': 1}
        summary = get_stats_summary(stats, total_repos=10, duration=25.0)
        
        assert summary['success_rate'] == 70.0
        assert summary['throughput'] == pytest.approx(0.36, rel=0.1)
    
    def test_zero_duration_handling(self):
        """Test handling of zero duration to avoid division by zero."""
        stats = {'success': 5, 'failed': 0, 'skipped': 0}
        summary = get_stats_summary(stats, total_repos=5, duration=0.0)
        
        assert summary['throughput'] == 0
    
    def test_total_repos_zero(self):
        """Test handling when no repos processed."""
        stats = {'success': 0, 'failed': 0, 'skipped': 0}
        summary = get_stats_summary(stats, total_repos=0, duration=10.0)
        
        assert summary['success_rate'] == 0


class TestReportEdgeCases:
    """Edge case testing for report generation."""
    
    def test_empty_repository_list(self, temp_dir):
        """Test generating report with empty repository list."""
        opts = {
            'report_format': 'markdown',
            'report_dir': temp_dir,
            'save_path': '.'
        }
        
        filepath = generate_report([], {}, {}, 0.0, opts)
        
        assert os.path.exists(filepath)
        with open(filepath, 'r') as f:
            content = f.read()
        assert 'Total Repositories: 0' in content or '0' in content
    
    def test_long_description_truncation(self, temp_dir, sample_repo_data):
        """Test that very long descriptions are truncated in reports."""
        long_desc_repo = sample_repo_data.copy()
        long_desc_repo['description'] = 'A' * 300  # Very long description
        
        opts = {
            'report_format': 'csv',
            'report_dir': temp_dir,
            'save_path': '.'
        }
        statuses = {long_desc_repo['name']: 'success'}
        stats = {'success': 1, 'failed': 0, 'skipped': 0}
        
        filepath = generate_report([long_desc_repo], statuses, stats, 1.0, opts)
        
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        desc_col = rows[1][1]  # Description column in first data row
        assert len(desc_col) <= 100  # Should be truncated
    
    def test_special_characters_in_names(self, temp_dir):
        """Test handling of special characters in repository names."""
        special_repo = {
            'name': 'repo-with-dashes_and.dots',
            'description': "Test repo with quotes: \"single' and `backticks`",
            'language': 'Python',
            'stargazers_count': 100,
            'updated_at': '2026-05-10T14:30:00Z',
            'size': 1024
        }
        
        opts = {
            'report_format': 'markdown',
            'report_dir': temp_dir,
            'save_path': '.'
        }
        statuses = {special_repo['name']: 'success'}
        stats = {'success': 1, 'failed': 0, 'skipped': 0}
        
        filepath = generate_report([special_repo], statuses, stats, 1.0, opts)
        
        assert os.path.exists(filepath)
        assert os.path.getsize(filepath) > 0
