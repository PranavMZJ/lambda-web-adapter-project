"""Unit tests for scripts/test_runner.py.

Tests recording logic, JSON serialization, error handling, and config reading.
Uses unittest.mock to mock urllib.request.urlopen for HTTP tests.
"""

import json
import os
import sys
import tempfile

import pytest
from unittest.mock import MagicMock, patch, mock_open
import urllib.error

# Add project root to path so we can import from scripts/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import scripts.test_runner as runner


# ---------------------------------------------------------------------------
# send_request — recording logic
# ---------------------------------------------------------------------------

class TestSendRequest:
    """Tests for the send_request function."""

    @patch("scripts.test_runner.urllib.request.urlopen")
    def test_records_successful_response(self, mock_urlopen):
        """A successful HTTP response records status_code and response_body."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        tc = {"method": "GET", "path": "/"}
        result = runner.send_request("https://example.com", tc)

        assert result["endpoint"] == "GET /"
        assert result["status_code"] == 200
        assert result["response_body"] == {"status": "ok"}
        assert result["error"] is None

    @patch("scripts.test_runner.urllib.request.urlopen")
    def test_records_http_error(self, mock_urlopen):
        """An HTTP error response records the status code and body."""
        error_body = b'{"error": "not found"}'
        http_error = urllib.error.HTTPError(
            url="https://example.com/items/x",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=MagicMock(read=MagicMock(return_value=error_body)),
        )
        mock_urlopen.side_effect = http_error

        tc = {"method": "GET", "path": "/items/x"}
        result = runner.send_request("https://example.com", tc)

        assert result["status_code"] == 404
        assert result["response_body"] is not None

    @patch("scripts.test_runner.urllib.request.urlopen")
    def test_records_connection_error(self, mock_urlopen):
        """A connection failure records the error and continues."""
        mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

        tc = {"method": "GET", "path": "/"}
        result = runner.send_request("https://example.com", tc)

        assert result["status_code"] is None
        assert result["response_body"] is None
        assert result["error"] is not None
        assert "Connection refused" in result["error"]

    @patch("scripts.test_runner.urllib.request.urlopen")
    def test_records_timeout_error(self, mock_urlopen):
        """A timeout records the error string."""
        mock_urlopen.side_effect = Exception("timed out")

        tc = {"method": "GET", "path": "/"}
        result = runner.send_request("https://example.com", tc)

        assert result["status_code"] is None
        assert "timed out" in result["error"]


# ---------------------------------------------------------------------------
# JSON serialization of results
# ---------------------------------------------------------------------------

class TestJsonSerialization:
    """Tests for write_results / run_all output structure."""

    @patch("scripts.test_runner.urllib.request.urlopen")
    def test_run_all_produces_valid_json_structure(self, mock_urlopen):
        """run_all returns a dict with timestamp, test1, and test2 keys."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        output = runner.run_all("https://test1.example.com", "https://test2.example.com")

        assert "timestamp" in output
        assert "test1" in output
        assert "test2" in output
        assert "base_url" in output["test1"]
        assert "results" in output["test1"]
        assert isinstance(output["test1"]["results"], list)

        # Verify it's JSON-serializable
        serialized = json.dumps(output)
        deserialized = json.loads(serialized)
        assert deserialized == output

    @patch("scripts.test_runner.urllib.request.urlopen")
    def test_write_results_creates_file(self, mock_urlopen):
        """write_results writes valid JSON to the results file."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = b'{"status": "ok"}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        output = runner.run_all("https://t1.example.com", "https://t2.example.com")

        with tempfile.TemporaryDirectory() as tmpdir:
            results_file = os.path.join(tmpdir, "results.json")
            original_file = runner.RESULTS_FILE
            original_dir = runner.RESULTS_DIR
            try:
                runner.RESULTS_FILE = results_file
                runner.RESULTS_DIR = tmpdir
                runner.write_results(output)

                with open(results_file, "r") as f:
                    loaded = json.load(f)
                assert loaded["timestamp"] == output["timestamp"]
            finally:
                runner.RESULTS_FILE = original_file
                runner.RESULTS_DIR = original_dir


# ---------------------------------------------------------------------------
# Config file reading
# ---------------------------------------------------------------------------

class TestLoadConfig:
    """Tests for load_config."""

    def test_load_config_from_env_vars(self):
        """Environment variables take precedence over config file."""
        with patch.dict(os.environ, {"TEST1_URL": "https://t1.test", "TEST2_URL": "https://t2.test"}):
            t1, t2 = runner.load_config()
            assert t1 == "https://t1.test"
            assert t2 == "https://t2.test"

    def test_load_config_from_file(self):
        """Falls back to config.json when env vars are not set."""
        config_data = json.dumps({"test1_url": "https://file-t1.test", "test2_url": "https://file-t2.test"})

        with patch.dict(os.environ, {"TEST1_URL": "", "TEST2_URL": ""}, clear=False):
            with patch("builtins.open", mock_open(read_data=config_data)):
                with patch("os.path.isfile", return_value=True):
                    t1, t2 = runner.load_config()
                    assert t1 == "https://file-t1.test"
                    assert t2 == "https://file-t2.test"

    def test_load_config_missing_file_exits(self):
        """Exits with error when config file is missing and env vars are not set."""
        with patch.dict(os.environ, {"TEST1_URL": "", "TEST2_URL": ""}, clear=False):
            with patch("os.path.isfile", return_value=False):
                with pytest.raises(SystemExit):
                    runner.load_config()


# ---------------------------------------------------------------------------
# Non-JSON response body handling
# ---------------------------------------------------------------------------

class TestParseBody:
    """Tests for _parse_body helper."""

    def test_parses_valid_json(self):
        assert runner._parse_body('{"key": "value"}') == {"key": "value"}

    def test_returns_raw_text_for_invalid_json(self):
        assert runner._parse_body("not json") == "not json"

    def test_parses_json_array(self):
        assert runner._parse_body('[1, 2, 3]') == [1, 2, 3]
