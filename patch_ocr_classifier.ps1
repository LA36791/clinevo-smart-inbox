from pathlib import Path

p = Path(".\ai-service\main.py")
s = p.read_text(encoding="utf-8")

s = s.replace(
    'patient = extract_value(text, "Patient ID")',
    'patient = extract_value(text, "Patient")\n    if patient == "Not stated":\n        patient = extract_value(text, "Patient ID")'
)

s = s.replace(
    '    pqc_terms = [\n        "quality complaint",\n        "complaint",\n        "defect",\n        "damaged",\n        "broken",\n        "leak",\n        "batch",\n        "lot",\n        "packaging",\n    ]',
    '    pqc_terms = [\n        "quality complaint",\n        "complaint",\n        "product defect",\n        "defective",\n        "damaged",\n        "broken",\n        "leak",\n        "leaking",\n        "missing tablet",\n        "packaging defect",\n        "wrong label",\n    ]'
)

p.write_text(s, encoding="utf-8")
print("Patch applied successfully.")
