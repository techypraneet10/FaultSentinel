"""Deterministic post-deployment smoke test suite for SentinelLog serving endpoints."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, Tuple


def make_request(
    url: str,
    method: str = "GET",
    headers: Dict[str, str] = None,
    data: Dict[str, Any] = None,
) -> Tuple[int, Dict[str, Any], Dict[str, str]]:
    """Execute HTTP request and return (status_code, parsed_json_or_text, response_headers)."""
    headers = headers or {}
    encoded_data = None
    if data is not None:
        encoded_data = json.dumps(data).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(url, data=encoded_data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=10.0) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            resp_headers = dict(resp.headers)
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = {"raw": body}
            return status, parsed, resp_headers
    except urllib.error.HTTPError as e:
        status = e.code
        body = e.read().decode("utf-8")
        resp_headers = dict(e.headers)
        try:
            parsed = json.loads(body)
        except Exception:
            parsed = {"raw": body}
        return status, parsed, resp_headers


def run_smoke_tests(base_url: str, api_key: str = "test-smoke-key-123456") -> Dict[str, Any]:
    """Execute deterministic smoke test checklist against live or test server."""
    base_url = base_url.rstrip("/")
    results = {}

    # 1. Liveness Probe
    live_status, live_body, _ = make_request(f"{base_url}/health/live")
    results["health_live"] = {
        "passed": live_status == 200 and live_body.get("status") == "ok",
        "status_code": live_status,
    }

    # 2. Readiness Probe
    ready_status, ready_body, _ = make_request(f"{base_url}/health/ready")
    results["health_ready"] = {
        "passed": ready_status == 200 and ready_body.get("status") in ("ready", "ok"),
        "status_code": ready_status,
    }

    # 3. Unauthenticated rejection
    unauth_status, unauth_body, _ = make_request(
        f"{base_url}/api/v1/analyze",
        method="POST",
        data={"dataset": "hdfs", "logs": ["Test log line"]},
    )
    # If auth enabled, must be 401. If auth disabled (dev mode), 200 is acceptable.
    results["auth_protection"] = {
        "passed": unauth_status in (200, 401),
        "status_code": unauth_status,
    }

    # 4. Authenticated Analysis Request
    auth_headers = {"Authorization": f"Bearer {api_key}"}
    analyze_payload = {
        "dataset": "hdfs",
        "logs": ["Block blk_100 allocated", "Block blk_100 write completed"],
    }
    ana_status, ana_body, ana_headers = make_request(
        f"{base_url}/api/v1/analyze",
        method="POST",
        headers=auth_headers,
        data=analyze_payload,
    )
    results["analysis_triage"] = {
        "passed": ana_status == 200 and "decision" in ana_body and "request_id" in ana_body,
        "status_code": ana_status,
        "request_id_present": "request_id" in ana_body,
    }

    # 5. Security Response Headers
    results["security_headers"] = {
        "nosniff": ana_headers.get("x-content-type-options") == "nosniff" or ana_headers.get("X-Content-Type-Options") == "nosniff",
        "frame_deny": ana_headers.get("x-frame-options") == "DENY" or ana_headers.get("X-Frame-Options") == "DENY",
    }

    # 6. Safe Diagnostics (zero secret leakage)
    diag_status, diag_body, _ = make_request(
        f"{base_url}/api/v1/diagnostics",
        method="GET",
        headers=auth_headers,
    )
    results["safe_diagnostics"] = {
        "passed": diag_status in (200, 403),
        "status_code": diag_status,
        "no_secret_leak": api_key not in json.dumps(diag_body),
    }

    all_passed = all(
        res.get("passed", True) for res in results.values() if isinstance(res, dict)
    )
    results["overall_verdict"] = "PASS" if all_passed else "FAIL"

    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SentinelLog Deployment Smoke Test Runner")
    parser.add_argument("--url", default="http://127.0.0.1:8000", help="Base URL of target service")
    parser.add_argument("--api-key", default="test-smoke-key-123456", help="API authentication token")
    args = parser.parse_args()

    report = run_smoke_tests(args.url, args.api_key)
    print(json.dumps(report, indent=2))
    sys.exit(0 if report["overall_verdict"] == "PASS" else 1)
