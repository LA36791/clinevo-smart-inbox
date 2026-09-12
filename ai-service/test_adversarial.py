import sys, json
sys.path.insert(0, '.')
from main import app, analyze_text
from fastapi.testclient import TestClient

# Test 1: Does analyze_text work on adversarial text?
adv_text = "Tricky Report\nPatient developed nausea after Product A.\nPatient experienced headache.\nPatient received Product B for 5 days.\n"
print("=== analyze_text on adversarial narrative ===")
try:
    r = analyze_text(adv_text, "adversarial", source_type="PDF", page=1)
    print('status: OK')
    print('document_type:', r.document_type)
    print('categories:', [(c.category, c.confidence) for c in r.categories])
    print('facts:')
    for f in r.facts:
        print(f"   {f.field:20s} = {str(f.value):30s} conf={f.confidence:.2f} ev={len(f.evidence)}")
    print('evidence_summary present:', r.evidence_summary is not None)
except Exception as e:
    print('ERROR:', type(e).__name__, e)

print()

# Test 2: Full PDF processing via TestClient
print("=== Full adversarial PDF via TestClient ===")
c = TestClient(app)
with open('C:/Users/vinod/Downloads/clinevo-smart-inbox-ai/data/adversarial_001.pdf', 'rb') as f:
    r = c.post('/analyze-document', files={'file': ('adversarial_001.pdf', f, 'application/pdf')})
d = r.json()
print('status:', r.status_code)
print('document_type:', d.get('document_type'))
print('categories:', [(x['category'], x['confidence']) for x in d.get('categories', [])])
es = d.get('evidence_summary')
print('evidence_summary:', 'present' if es is not None else 'NONE')
if es:
    print('  coverage:', es.get('evidence_coverage'))
    print('  contradictions:', es.get('contradictions'))
    print('  review_priority:', es.get('review_priority'))


