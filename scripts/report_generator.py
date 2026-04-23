#!/usr/bin/env python3
"""
Report Generator for lambda-web-adapter-migration-test.

Reads results/results.json and produces:
  - report.md    (Japanese)
  - report_en.md (English)

Both reports contain: Overview, Test 1 results, Test 2 results,
side-by-side comparison table, and conclusion.

Uses only Python standard library.
"""

import json
import os
import sys

RESULTS_FILE = os.path.join("results", "results.json")
REPORT_JA = "report.md"
REPORT_EN = "report_en.md"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def load_results():
    """Load and validate results/results.json.

    Returns the parsed dict or exits with a clear error.
    """
    if not os.path.isfile(RESULTS_FILE):
        print(f"ERROR: Results file '{RESULTS_FILE}' not found.", file=sys.stderr)
        sys.exit(1)

    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        print(
            f"ERROR: Results file '{RESULTS_FILE}' is malformed JSON: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)
    except OSError as exc:
        print(
            f"ERROR: Could not read '{RESULTS_FILE}': {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Basic structure validation
    if not isinstance(data, dict):
        print(
            f"ERROR: Results file '{RESULTS_FILE}' does not contain a JSON object.",
            file=sys.stderr,
        )
        sys.exit(1)

    for key in ("timestamp", "test1", "test2"):
        if key not in data:
            print(
                f"ERROR: Results file '{RESULTS_FILE}' is missing required key '{key}'.",
                file=sys.stderr,
            )
            sys.exit(1)

    return data


def safe(value, default="N/A"):
    """Return *value* if it is not None, otherwise *default*."""
    if value is None:
        return default
    return value


def format_body(body):
    """Format a response body for display in the report."""
    if body is None:
        return "N/A"
    if isinstance(body, (dict, list)):
        return json.dumps(body, ensure_ascii=False)
    return str(body)


def is_success(status_code):
    """Return True if *status_code* is a non-server-error HTTP status.

    2xx and 4xx are considered successful application responses (the app is
    running and responding correctly).  Only 5xx, None, or other unexpected
    codes indicate that the application failed to run.
    """
    if status_code is None:
        return False
    return 200 <= status_code < 500


def all_test2_success(data):
    """Return True if every Test 2 result has a non-5xx status and no error.

    4xx responses (e.g. 404 for non-existent items) are expected application
    behaviour and do NOT indicate failure.
    """
    test2 = data.get("test2", {})
    results = test2.get("results", [])
    if not results:
        return False
    for r in results:
        if not is_success(r.get("status_code")):
            return False
        if r.get("error"):
            return False
    return True


def result_summary(r):
    """One-line summary of a single test result for the comparison table."""
    status = safe(r.get("status_code"))
    error = r.get("error")
    if error:
        return f"{status} / {error}"
    return str(status)


# ---------------------------------------------------------------------------
# Report generation — Japanese
# ---------------------------------------------------------------------------

def generate_report_ja(data):
    """Return the Japanese report as a string."""
    timestamp = safe(data.get("timestamp"))
    test1 = data.get("test1", {})
    test2 = data.get("test2", {})
    test1_url = safe(test1.get("base_url"))
    test2_url = safe(test2.get("base_url"))
    test1_results = test1.get("results", [])
    test2_results = test2.get("results", [])

    lines = []

    # --- Overview ---
    lines.append("# Lambda Web Adapter 移行テスト レポート")
    lines.append("")
    lines.append("## 概要")
    lines.append("")
    lines.append("本レポートは、Flask アプリケーションを AWS Lambda にデプロイした際の動作比較結果をまとめたものです。")
    lines.append("")
    lines.append("- **テスト 1（アダプターなし）**: aws-lambda-web-adapter を使用せずにデプロイ")
    lines.append("- **テスト 2（アダプターあり）**: aws-lambda-web-adapter を Lambda Layer として追加してデプロイ")
    lines.append("")
    lines.append(f"- **実行日時**: {timestamp}")
    lines.append(f"- **テスト 1 エンドポイント**: {test1_url}")
    lines.append(f"- **テスト 2 エンドポイント**: {test2_url}")
    lines.append("")

    # --- Test 1 results ---
    lines.append("## テスト 1 結果（アダプターなし）")
    lines.append("")
    lines.append("| エンドポイント | ステータスコード | エラー |")
    lines.append("|---|---|---|")
    for r in test1_results:
        endpoint = safe(r.get("endpoint"))
        status = safe(r.get("status_code"))
        error = safe(r.get("error"), default="なし")
        lines.append(f"| {endpoint} | {status} | {error} |")
    lines.append("")

    # --- Test 2 results ---
    lines.append("## テスト 2 結果（アダプターあり）")
    lines.append("")
    lines.append("| エンドポイント | ステータスコード | レスポンスボディ | エラー |")
    lines.append("|---|---|---|---|")
    for r in test2_results:
        endpoint = safe(r.get("endpoint"))
        status = safe(r.get("status_code"))
        body = format_body(r.get("response_body"))
        error = safe(r.get("error"), default="なし")
        lines.append(f"| {endpoint} | {status} | {body} | {error} |")
    lines.append("")

    # --- Comparison table ---
    lines.append("## 比較表")
    lines.append("")
    lines.append("| エンドポイント | テスト 1 結果 | テスト 2 結果 |")
    lines.append("|---|---|---|")

    # Build a map from endpoint to result for each test
    t1_map = {r.get("endpoint"): r for r in test1_results}
    t2_map = {r.get("endpoint"): r for r in test2_results}
    all_endpoints = _ordered_unique_endpoints(test1_results, test2_results)

    for ep in all_endpoints:
        r1 = t1_map.get(ep, {})
        r2 = t2_map.get(ep, {})
        lines.append(f"| {ep} | {result_summary(r1)} | {result_summary(r2)} |")
    lines.append("")

    # --- Conclusion ---
    lines.append("## 結論")
    lines.append("")
    if all_test2_success(data):
        lines.append("テスト 2 の全エンドポイントが正常に応答しました。**アプリケーションコードの変更は不要でした。**")
    else:
        lines.append("テスト 2 の一部のエンドポイントでエラーが発生しました。**アプリケーションコードの変更が必要でした。**")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Report generation — English
# ---------------------------------------------------------------------------

def generate_report_en(data):
    """Return the English report as a string."""
    timestamp = safe(data.get("timestamp"))
    test1 = data.get("test1", {})
    test2 = data.get("test2", {})
    test1_url = safe(test1.get("base_url"))
    test2_url = safe(test2.get("base_url"))
    test1_results = test1.get("results", [])
    test2_results = test2.get("results", [])

    lines = []

    # --- Overview ---
    lines.append("# Lambda Web Adapter Migration Test Report")
    lines.append("")
    lines.append("## Overview")
    lines.append("")
    lines.append("This report summarizes the comparison results of deploying a Flask application to AWS Lambda.")
    lines.append("")
    lines.append("- **Test 1 (No Adapter)**: Deployed without aws-lambda-web-adapter")
    lines.append("- **Test 2 (With Adapter)**: Deployed with aws-lambda-web-adapter as a Lambda Layer")
    lines.append("")
    lines.append(f"- **Execution Time**: {timestamp}")
    lines.append(f"- **Test 1 Endpoint**: {test1_url}")
    lines.append(f"- **Test 2 Endpoint**: {test2_url}")
    lines.append("")

    # --- Test 1 results ---
    lines.append("## Test 1 Results (No Adapter)")
    lines.append("")
    lines.append("| Endpoint | Status Code | Error |")
    lines.append("|---|---|---|")
    for r in test1_results:
        endpoint = safe(r.get("endpoint"))
        status = safe(r.get("status_code"))
        error = safe(r.get("error"), default="None")
        lines.append(f"| {endpoint} | {status} | {error} |")
    lines.append("")

    # --- Test 2 results ---
    lines.append("## Test 2 Results (With Adapter)")
    lines.append("")
    lines.append("| Endpoint | Status Code | Response Body | Error |")
    lines.append("|---|---|---|---|")
    for r in test2_results:
        endpoint = safe(r.get("endpoint"))
        status = safe(r.get("status_code"))
        body = format_body(r.get("response_body"))
        error = safe(r.get("error"), default="None")
        lines.append(f"| {endpoint} | {status} | {body} | {error} |")
    lines.append("")

    # --- Comparison table ---
    lines.append("## Comparison Table")
    lines.append("")
    lines.append("| Endpoint | Test 1 Result | Test 2 Result |")
    lines.append("|---|---|---|")

    t1_map = {r.get("endpoint"): r for r in test1_results}
    t2_map = {r.get("endpoint"): r for r in test2_results}
    all_endpoints = _ordered_unique_endpoints(test1_results, test2_results)

    for ep in all_endpoints:
        r1 = t1_map.get(ep, {})
        r2 = t2_map.get(ep, {})
        lines.append(f"| {ep} | {result_summary(r1)} | {result_summary(r2)} |")
    lines.append("")

    # --- Conclusion ---
    lines.append("## Conclusion")
    lines.append("")
    if all_test2_success(data):
        lines.append("All Test 2 endpoints responded successfully. **No application code changes were required.**")
    else:
        lines.append("Some Test 2 endpoints returned errors. **Application code changes were required.**")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ordered_unique_endpoints(test1_results, test2_results):
    """Return a list of unique endpoint labels preserving first-seen order."""
    seen = set()
    ordered = []
    for r in test1_results + test2_results:
        ep = r.get("endpoint")
        if ep and ep not in seen:
            seen.add(ep)
            ordered.append(ep)
    return ordered


def write_report(path, content):
    """Write report content to a file."""
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Report written to {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    data = load_results()

    report_ja = generate_report_ja(data)
    write_report(REPORT_JA, report_ja)

    report_en = generate_report_en(data)
    write_report(REPORT_EN, report_en)

    print("Done.")


if __name__ == "__main__":
    main()
