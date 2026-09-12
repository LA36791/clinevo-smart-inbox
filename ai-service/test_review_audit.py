#!/usr/bin/env python
"""Test review and audit functionality."""
import json
import os
import time
import urllib.request

BACKEND_URL = "http://127.0.0.1:8080"
RESULTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "review_audit_results.json")

results = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "tests": {}}

def log(msg):
    print(msg, flush=True)

def post_json(path, payload):
    data = json.dumps(payload).encode()
    req = urllib.request.Request(f"{BACKEND_URL}{path}", data=data,
        headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def get(path):
    try:
        resp = urllib.request.urlopen(f"{BACKEND_URL}{path}", timeout=10)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def main():
    log("=" * 60)
    log("REVIEW AND AUDIT TEST")
    log("=" * 60)

    # Test 1: ACCEPT review
    log("Test 1: ACCEPT review...")
    data = post_json("/api/review", {
        "analysisId": 74,
        "action": "ACCEPT",
        "originalCategory": "SAFETY_REPORT_ICSR",
        "finalCategory": "SAFETY_REPORT_ICSR",
        "reviewer": "Test Reviewer",
        "notes": "Test accept",
    })
    if data.get("id"):
        results["tests"]["accept"] = {"status": "PASS", "reviewId": data["id"]}
        log(f"  PASS: reviewId={data['id']}")
    else:
        results["tests"]["accept"] = {"status": "FAIL", "data": data}
        log(f"  FAIL: {data}")

    # Test 2: OVERRIDE review
    log("Test 2: OVERRIDE review...")
    data = post_json("/api/review", {
        "analysisId": 74,
        "action": "OVERRIDE",
        "originalCategory": "SAFETY_REPORT_ICSR",
        "finalCategory": "QUALITY_COMPLAINT_PQC",
        "reviewer": "Test Reviewer",
        "notes": "Test override",
    })
    if data.get("id"):
        results["tests"]["override"] = {"status": "PASS", "reviewId": data["id"]}
        log(f"  PASS: reviewId={data['id']}")
    else:
        results["tests"]["override"] = {"status": "FAIL", "data": data}
        log(f"  FAIL: {data}")

    # Test 3: Audit trail
    log("Test 3: Audit trail...")
    audit_data = get("/api/audit?analysisId=74")
    if isinstance(audit_data, list) and len(audit_data) > 0:
        results["tests"]["audit"] = {"status": "PASS", "entries": len(audit_data)}
        log(f"  PASS: {len(audit_data)} audit entries")
    else:
        results["tests"]["audit"] = {"status": "FAIL", "data": audit_data}
        log(f"  FAIL: {audit_data}")

    # Summary
    total = len(results["tests"])
    passed = sum(1 for t in results["tests"].values() if t.get("status") == "PASS")
    log(f"\nREVIEW/AUDIT RESULTS: {passed}/{total} passed")

    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)

if __name__ == "__main__":
    main()
