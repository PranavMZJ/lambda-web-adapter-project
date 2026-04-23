"""Unit tests for scripts/report_generator.py.

Tests report generation with sample results, section presence, comparison
table row counts, conclusion content, and N/A fallback for missing fields.
"""

import json
import os
import sys
import tempfile

import pytest

# Add project root to path so we can import from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import scripts.report_generator as rg


# ---------------------------------------------------------------------------
# Fixtures — sample results data
# ---------------------------------------------------------------------------

@pytest.fixture()
def sample_results_success():
    """Sample results where all Test 2 endpoints succeed."""
    return {
        "timestamp": "2025-01-15T10:00:00Z",
        "test1": {
            "base_url": "https://api.example.com/test1",
            "results": [
                {"endpoint": "GET /", "status_code": None, "response_body": None, "error": "Runtime.HandlerNotFound"},
                {"endpoint": "GET /items", "status_code": None, "response_body": None, "error": "Runtime.HandlerNotFound"},
                {"endpoint": "POST /items", "status_code": None, "response_body": None, "error": "Runtime.HandlerNotFound"},
                {"endpoint": "GET /items/abc", "status_code": None, "response_body": None, "error": "Runtime.HandlerNotFound"},
            ],
        },
        "test2": {
            "base_url": "https://api.example.com/test2",
            "results": [
                {"endpoint": "GET /", "status_code": 200, "response_body": {"status": "ok"}, "error": None},
                {"endpoint": "GET /items", "status_code": 200, "response_body": [], "error": None},
                {"endpoint": "POST /items", "status_code": 201, "response_body": {"id": "x", "name": "test"}, "error": None},
                {"endpoint": "GET /items/abc", "status_code": 200, "response_body": {"id": "abc", "name": "test"}, "error": None},
            ],
        },
    }


@pytest.fixture()
def sample_results_failure():
    """Sample results where some Test 2 endpoints fail."""
    return {
        "timestamp": "2025-01-15T10:00:00Z",
        "test1": {
            "base_url": "https://api.example.com/test1",
            "results": [
                {"endpoint": "GET /", "status_code": None, "response_body": None, "error": "Runtime.HandlerNotFound"},
            ],
        },
        "test2": {
            "base_url": "https://api.example.com/test2",
            "results": [
                {"endpoint": "GET /", "status_code": 500, "response_body": None, "error": "Internal Server Error"},
            ],
        },
    }


@pytest.fixture()
def sample_results_missing_fields():
    """Sample results with missing fields to test N/A fallback."""
    return {
        "timestamp": "2025-01-15T10:00:00Z",
        "test1": {
            "base_url": "https://api.example.com/test1",
            "results": [
                {"endpoint": "GET /"},  # missing status_code, response_body, error
            ],
        },
        "test2": {
            "base_url": "https://api.example.com/test2",
            "results": [
                {"endpoint": "GET /"},  # missing status_code, response_body, error
            ],
        },
    }


# ---------------------------------------------------------------------------
# Report generation produces both files
# ---------------------------------------------------------------------------

class TestReportGeneration:
    """Tests that both report.md and report_en.md are produced."""

    def test_generates_both_reports(self, sample_results_success, tmp_path):
        """Both report.md and report_en.md are written."""
        ja_path = str(tmp_path / "report.md")
        en_path = str(tmp_path / "report_en.md")

        report_ja = rg.generate_report_ja(sample_results_success)
        report_en = rg.generate_report_en(sample_results_success)

        rg.write_report(ja_path, report_ja)
        rg.write_report(en_path, report_en)

        assert os.path.isfile(ja_path)
        assert os.path.isfile(en_path)
        assert len(report_ja) > 0
        assert len(report_en) > 0


# ---------------------------------------------------------------------------
# All five sections are present
# ---------------------------------------------------------------------------

class TestSectionPresence:
    """Tests that all five required sections appear in both reports."""

    def test_japanese_report_has_all_sections(self, sample_results_success):
        report = rg.generate_report_ja(sample_results_success)
        assert "## 概要" in report
        assert "## テスト 1 結果" in report
        assert "## テスト 2 結果" in report
        assert "## 比較表" in report
        assert "## 結論" in report

    def test_english_report_has_all_sections(self, sample_results_success):
        report = rg.generate_report_en(sample_results_success)
        assert "## Overview" in report
        assert "## Test 1 Results" in report
        assert "## Test 2 Results" in report
        assert "## Comparison Table" in report
        assert "## Conclusion" in report


# ---------------------------------------------------------------------------
# Comparison table row count matches endpoint count
# ---------------------------------------------------------------------------

class TestComparisonTable:
    """Tests that the comparison table has the correct number of rows."""

    def test_comparison_table_row_count(self, sample_results_success):
        """Comparison table has one row per unique endpoint."""
        report = rg.generate_report_en(sample_results_success)

        # Find the comparison table section
        lines = report.split("\n")
        in_table = False
        data_rows = 0
        for line in lines:
            if "## Comparison Table" in line:
                in_table = True
                continue
            if in_table and line.startswith("## "):
                break
            if in_table and line.startswith("|") and "---" not in line and "Endpoint" not in line:
                data_rows += 1

        # 4 unique endpoints in sample data
        assert data_rows == 4

    def test_comparison_table_row_count_single_endpoint(self, sample_results_failure):
        """Comparison table has 1 row for single-endpoint results."""
        report = rg.generate_report_en(sample_results_failure)

        lines = report.split("\n")
        in_table = False
        data_rows = 0
        for line in lines:
            if "## Comparison Table" in line:
                in_table = True
                continue
            if in_table and line.startswith("## "):
                break
            if in_table and line.startswith("|") and "---" not in line and "Endpoint" not in line:
                data_rows += 1

        assert data_rows == 1


# ---------------------------------------------------------------------------
# Conclusion content
# ---------------------------------------------------------------------------

class TestConclusion:
    """Tests for the conclusion section content."""

    def test_success_conclusion_en(self, sample_results_success):
        """Success case states 'No application code changes were required'."""
        report = rg.generate_report_en(sample_results_success)
        assert "No application code changes were required" in report

    def test_failure_conclusion_en(self, sample_results_failure):
        """Failure case states 'Application code changes were required'."""
        report = rg.generate_report_en(sample_results_failure)
        assert "Application code changes were required" in report

    def test_success_conclusion_ja(self, sample_results_success):
        """Success case in Japanese states the equivalent message."""
        report = rg.generate_report_ja(sample_results_success)
        assert "アプリケーションコードの変更は不要でした" in report

    def test_failure_conclusion_ja(self, sample_results_failure):
        """Failure case in Japanese states the equivalent message."""
        report = rg.generate_report_ja(sample_results_failure)
        assert "アプリケーションコードの変更が必要でした" in report


# ---------------------------------------------------------------------------
# Handling of missing fields (N/A fallback)
# ---------------------------------------------------------------------------

class TestMissingFields:
    """Tests that missing fields fall back to N/A."""

    def test_missing_status_code_shows_na(self, sample_results_missing_fields):
        """Missing status_code renders as N/A in the report."""
        report = rg.generate_report_en(sample_results_missing_fields)
        assert "N/A" in report

    def test_missing_response_body_shows_na(self, sample_results_missing_fields):
        """Missing response_body renders as N/A in the report."""
        report = rg.generate_report_en(sample_results_missing_fields)
        # The Test 2 results table includes response body column
        assert "N/A" in report

    def test_safe_helper_returns_default(self):
        """The safe() helper returns 'N/A' for None values."""
        assert rg.safe(None) == "N/A"
        assert rg.safe(None, default="missing") == "missing"
        assert rg.safe(200) == 200
        assert rg.safe("hello") == "hello"

    def test_format_body_none(self):
        """format_body returns 'N/A' for None."""
        assert rg.format_body(None) == "N/A"

    def test_format_body_dict(self):
        """format_body returns JSON string for dicts."""
        result = rg.format_body({"key": "value"})
        assert '"key"' in result
        assert '"value"' in result
