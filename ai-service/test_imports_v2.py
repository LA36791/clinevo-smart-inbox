#!/usr/bin/env python
"""Test all imports and basic functionality."""
import sys
import os
import json

results = {}

# Test 1: providers
try:
    from providers import DeterministicProvider
    p = DeterministicProvider()
    results["providers"] = "OK"
    results["using_llm"] = p.using_llm
    results["using_rag"] = p.using_rag
except Exception as e:
    results["providers"] = f"FAIL: {e}"

# Test 2: llm_provider
try:
    from llm_provider import LLMProvider
    llm = LLMProvider()
    results["llm_provider"] = "OK"
    results["llm_available"] = llm.is_available()
except Exception as e:
    results["llm_provider"] = f"FAIL: {e}"

# Test 3: rag
try:
    from rag import HybridRAG, Chunk
    rag = HybridRAG()
    results["rag"] = "OK"
except Exception as e:
    results["rag"] = f"FAIL: {e}"

# Test 4: RAG indexing and retrieval
try:
    from rag import HybridRAG
    from models import PageResult
    rag = HybridRAG()
    pages = [
        PageResult(page=1, text="Patient P-100 had nausea after taking Product A. Batch B-001.", confidence=0.95),
        PageResult(page=2, text="Reporter: Dr. Smith. Severity: Serious.", confidence=0.95),
    ]
    rag.index_pages(pages)
    results["rag_chunks"] = len(rag.chunks)
    results["rag_retrieve"] = len(rag.retrieve("patient nausea", top_k=2))
except Exception as e:
    results["rag_test"] = f"FAIL: {e}"

# Test 5: extract_value fix
try:
    from main import extract_value
    # Test that greedy extraction is fixed
    text = "Patient: P-600\nProduit: Produit B\nRéaction: Nausee"
    val = extract_value(text, "Patient")
    results["extract_patient"] = val
    results["extract_fixed"] = val == "P-600"
except Exception as e:
    results["extract_value"] = f"FAIL: {e}"

# Write results
output_file = os.path.join(os.path.dirname(__file__), "import_test_results.json")
with open(output_file, "w") as f:
    json.dump(results, f, indent=2)

print("Results written to import_test_results.json")
for k, v in results.items():
    print(f"  {k}: {v}")
