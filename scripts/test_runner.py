#!/usr/bin/env python3
"""
Test Runner for lambda-web-adapter-migration-test.

Sends identical HTTP requests to both Test 1 (no-adapter) and Test 2 (with-adapter)
Lambda endpoints via API Gateway, records the results, and writes them to
results/results.json.

Uses only Python standard library (no external dependencies).
"""

import json
import os
import sys
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

CONFIG_FILE = "config.json"
RESULTS_DIR = "results"
RESULTS_FILE = os.path.join(RESULTS_DIR, "results.json")

# Timeout in seconds for each HTTP request
REQUEST_TIMEOUT = 30


def load_config():
    """Load endpoint URLs from environment variables or config.json.

    Environment variables TEST1_URL / TEST2_URL take precedence over the
    config file.  Returns a tuple (test1_url, test2_url).
    """
    test1_url = os.environ.get("TEST1_URL", "").strip()
    test2_url = os.environ.get("TEST2_URL", "").strip()

    if test1_url and test2_url:
        return test1_url, test2_url

    # Fall back to config.json
    if not os.path.isfile(CONFIG_FILE):
        print(f"ERROR: Configuration file '{CONFIG_FILE}' not found and "
              "environment variables TEST1_URL / TEST2_URL are not set.",
              file=sys.stderr)
        sys.exit(1)

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: Failed to read '{CONFIG_FILE}': {exc}", file=sys.stderr)
        sys.exit(1)

    test1_url = test1_url or (config.get("test1_url") or "").strip()
    test2_url = test2_url or (config.get("test2_url") or "").strip()

    if not test1_url or not test2_url:
        print("ERROR: Both 'test1_url' and 'test2_url' must be set "
              f"(in environment variables or '{CONFIG_FILE}').",
              file=sys.stderr)
        sys.exit(1)

    return test1_url, test2_url


# ---------------------------------------------------------------------------
# Test case definitions
# ---------------------------------------------------------------------------

# Placeholder UUID for GET /items/{id} — intentionally non-existent
PLACEHOLDER_UUID = "00000000-0000-0000-0000-000000000000"


def get_test_cases():
    """Return the list of test cases to execute against each endpoint.

    Each test case is a dict with keys: method, path, body (optional).
    """
    return [
        {"method": "GET", "path": "/"},
        {"method": "GET", "path": "/items"},
        {"method": "POST", "path": "/items", "body": {"name": "test-item"}},
        {"method": "GET", "path": f"/items/{PLACEHOLDER_UUID}"},
    ]


# ---------------------------------------------------------------------------
# HTTP request helper
# ---------------------------------------------------------------------------

def send_request(base_url, test_case):
    """Send a single HTTP request and return a result dict.

    Returns:
        dict with keys: endpoint, status_code, response_body, error
    """
    method = test_case["method"]
    path = test_case["path"]
    body = test_case.get("body")

    endpoint_label = f"{method} {path}"

    # Build the full URL — strip trailing slash from base to avoid double-slash
    url = base_url.rstrip("/") + path

    result = {
        "endpoint": endpoint_label,
        "status_code": None,
        "response_body": None,
        "error": None,
    }

    try:
        data = None
        headers = {}
        if body is not None:
            data = json.dumps(body).encode("utf-8")
            headers["Content-Type"] = "application/json"

        req = urllib.request.Request(
            url, data=data, headers=headers, method=method
        )

        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            result["status_code"] = resp.status
            raw_body = resp.read().decode("utf-8", errors="replace")
            result["response_body"] = _parse_body(raw_body)

    except urllib.error.HTTPError as exc:
        result["status_code"] = exc.code
        try:
            raw_body = exc.read().decode("utf-8", errors="replace")
            result["response_body"] = _parse_body(raw_body)
        except Exception:
            result["response_body"] = None
        # For HTTP errors, also capture the reason in the error field
        # when the response body contains an error message
        body_val = result["response_body"]
        if isinstance(body_val, dict) and "message" in body_val:
            result["error"] = body_val["message"]
        elif isinstance(body_val, dict) and "errorMessage" in body_val:
            result["error"] = body_val["errorMessage"]
        elif isinstance(body_val, dict) and "errorType" in body_val:
            result["error"] = f"{body_val['errorType']}: {body_val.get('errorMessage', '')}"
        elif isinstance(body_val, str) and body_val:
            result["error"] = body_val

    except urllib.error.URLError as exc:
        # Connection refused, DNS failure, etc.
        result["error"] = str(exc.reason)

    except Exception as exc:
        # Timeout or any other unexpected error
        result["error"] = str(exc)

    return result


def _parse_body(raw_body):
    """Try to parse a response body as JSON; fall back to raw text."""
    try:
        return json.loads(raw_body)
    except (json.JSONDecodeError, ValueError):
        return raw_body


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_tests(base_url, test_cases):
    """Execute all test cases against a single base URL.

    Returns a list of result dicts.
    """
    results = []
    for tc in test_cases:
        result = send_request(base_url, tc)
        results.append(result)
    return results


def run_all(test1_url, test2_url):
    """Run the full test suite against both endpoints and return the output dict."""
    test_cases = get_test_cases()

    print(f"Running tests against Test 1: {test1_url}")
    test1_results = run_tests(test1_url, test_cases)

    print(f"Running tests against Test 2: {test2_url}")
    test2_results = run_tests(test2_url, test_cases)

    output = {
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "test1": {
            "base_url": test1_url,
            "results": test1_results,
        },
        "test2": {
            "base_url": test2_url,
            "results": test2_results,
        },
    }
    return output


def write_results(output):
    """Write the test output to results/results.json."""
    os.makedirs(RESULTS_DIR, exist_ok=True)

    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"Results written to {RESULTS_FILE}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    test1_url, test2_url = load_config()
    output = run_all(test1_url, test2_url)
    write_results(output)

    # Print a quick summary
    for label in ("test1", "test2"):
        section = output[label]
        print(f"\n--- {label.upper()} ({section['base_url']}) ---")
        for r in section["results"]:
            status = r["status_code"] if r["status_code"] is not None else "N/A"
            error = r["error"] or ""
            print(f"  {r['endpoint']}: status={status}  {error}")


if __name__ == "__main__":
    main()
