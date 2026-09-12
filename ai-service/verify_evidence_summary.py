import sys, json
sys.path.insert(0, '.')
from main import app
from fastapi.testclient import TestClient

c = TestClient(app)
pdf_path = 'C:/Users/vinod/Downloads/clinevo-smart-inbox-ai/data/synthetic_case.pdf'
with open(pdf_path, 'rb') as f:
    r = c.post('/analyze-document', files={'file': ('synthetic_case.pdf', f, 'application/pdf')})
d = r.json()
es = d.get('evidence_summary', {})

print('evidence_summary present:', 'evidence_summary' in d)
print('coverage_pct:', es.get('evidence_coverage', {}).get('coverage_percent'))
print('completeness_pct:', es.get('field_completeness', {}).get('completeness_percent'))
print('reliability:', es.get('ai_reliability'))
print('review_priority:', es.get('review_priority'))
print('contradictions:', len(es.get('contradictions', [])))
print('injection_detected:', es.get('prompt_injection', {}).get('injection_detected'))
print('route:', es.get('processing_route'))
print('rag_retrieval:', es.get('rag_retrieval'))
print('document_fingerprint:', es.get('document_fingerprint'))
print('prompt_injection:', json.dumps(es.get('prompt_injection')))
print('evidence_graph nodes:', len(es.get('evidence_graph', {}).get('nodes', [])))
print('validated_claims:', len(es.get('validated_claims', [])))
print('http_status:', r.status_code)
