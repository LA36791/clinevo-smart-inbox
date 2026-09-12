#!/usr/bin/env python
"""Final comprehensive E2E test."""
import json
import os
import time
import urllib.request

AI_URL = "http://127.0.0.1:8002"
BACKEND_URL = "http://127.0.0.1:8080"
DATA_DIR = r"C:\Users\vinod\Downloads\clinevo-smart-inbox-ai\data"
RESULTS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "final_e2e_results.json")

results = {"timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "tests": {}}

def log(msg):
    print(msg, flush=True)

def post_file_ai(path, filepath):
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    boundary = "Boundary7MA4YWxkTrZu0gW"
    filename = os.path.basename(filepath)
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{AI_URL}{path}", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def post_file_backend(path, filepath):
    with open(filepath, "rb") as f:
        file_bytes = f.read()
    boundary = "Boundary7MA4YWxkTrZu0gW"
    filename = os.path.basename(filepath)
    body = (
        f"--{boundary}\r\n"
        f"Content-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(f"{BACKEND_URL}{path}", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def main():
    log("=" * 60)
    log("FINAL COMPREHENSIVE E2E TEST")
    log("=" * 60)

    # Test AI Service
    log("\n--- AI Service Tests ---")
    
    # Health
    try:
        req = urllib.request.Request(f"{AI_URL}/health")
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        results["tests"]["ai_health"] = {"status": "PASS", "data": data}
        log(f"  AI Health: PASS ({data})")
    except Exception as e:
        results["tests"]["ai_health"] = {"status": "FAIL", "error": str(e)}
        log(f"  AI Health: FAIL ({e})")

    # Test each PDF
    pdfs = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.pdf')])
    pdf_results = []
    
    for pdf_name in pdfs:
        pdf_path = os.path.join(DATA_DIR, pdf_name)
        data = post_file_ai("/analyze-document", pdf_path)
        
        if data.get("error"):
            pdf_results.append({"file": pdf_name, "status": "ERROR", "error": data["error"]})
            log(f"  {pdf_name}: ERROR - {data['error']}")
        else:
            cat = data.get("categories", [{}])[0].get("category", "NONE") if data.get("categories") else "NONE"
            conf = data.get("categories", [{}])[0].get("confidence", 0) if data.get("categories") else 0
            review = data.get("human_review_required", True)
            pdf_results.append({"file": pdf_name, "status": "OK", "category": cat, "confidence": conf, "review": review})
            log(f"  {pdf_name}: {cat} (conf={conf:.2f}, review={review})")
    
    results["tests"]["pdf_results"] = pdf_results
    results["tests"]["pdf_total"] = len(pdfs)
    results["tests"]["pdf_success"] = sum(1 for r in pdf_results if r["status"] == "OK")
    
    # Test Backend
    log("\n--- Backend Tests ---")
    
    # Health
    try:
        req = urllib.request.Request(f"{BACKEND_URL}/api/health")
        resp = urllib.request.urlopen(req, timeout=5)
        data = json.loads(resp.read().decode())
        results["tests"]["backend_health"] = {"status": "PASS", "data": data}
        log(f"  Backend Health: PASS ({data})")
    except Exception as e:
        results["tests"]["backend_health"] = {"status": "FAIL", "error": str(e)}
        log(f"  Backend Health: FAIL ({e})")
    
    # Analyze through backend
    pdf = os.path.join(DATA_DIR, "safety_001.pdf")
    data = post_file_backend("/api/analyze", pdf)
    if data.get("categories"):
        results["tests"]["backend_analyze"] = {"status": "PASS", "analysisId": data.get("analysisId")}
        log(f"  Backend Analyze: PASS (analysisId={data.get('analysisId')})")
    else:
        results["tests"]["backend_analyze"] = {"status": "FAIL", "data": data}
        log(f"  Backend Analyze: FAIL")
    
    # Summary
    log("\n" + "=" * 60)
    log(f"PDFs: {results['tests']['pdf_success']}/{results['tests']['pdf_total']} processed successfully")
    log("=" * 60)
    
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=2, default=str)

if __name__ == "__main__":
    main()
