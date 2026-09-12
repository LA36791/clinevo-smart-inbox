#!/usr/bin/env python
"""Create synthetic test data PDFs."""
import os
import json
import time

DATA_DIR = r"C:\Users\vinod\Downloads\clinevo-smart-inbox-ai\data"

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False

def create_pdf(filename, title, content_lines):
    if not HAS_REPORTLAB:
        return None
    filepath = os.path.join(DATA_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, title)
    c.setFont("Helvetica", 11)
    y = height - 108
    for line in content_lines:
        if y < 72:
            c.showPage()
            y = height - 72
            c.setFont("Helvetica", 11)
        c.drawString(72, y, line)
        y -= 16
    c.save()
    print(f"  Created: {filename}")
    return filepath

def create_table_pdf(filename, title, headers, rows):
    if not HAS_REPORTLAB:
        return None
    filepath = os.path.join(DATA_DIR, filename)
    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, height - 72, title)
    y = height - 108
    c.setFont("Helvetica-Bold", 9)
    x = 72
    for h in headers:
        c.drawString(x, y, h)
        x += 90
    y -= 20
    c.setFont("Helvetica", 9)
    for row in rows:
        if y < 72:
            c.showPage()
            y = letter[1] - 72
        x = 72
        for cell in row:
            c.drawString(x, y, str(cell)[:12])
            x += 90
        y -= 14
    c.save()
    print(f"  Created: {filename}")
    return filepath

def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    created = []
    print("Creating safety report PDFs...")
    create_pdf("safety_001.pdf", "Adverse Event Report", [
        "Patient: P-100", "Product: Product A", "Reaction: Severe headache",
        "Severity: Serious", "Batch: BATCH-100", "Reporter: Dr. Smith",
        "Narrative: Patient reported severe headache within 2 hours.",
    ])
    created.append("safety_001.pdf")
    create_pdf("safety_002.pdf", "Safety Report", [
        "Patient: P-200", "Product: Product B", "Reaction: Nausea and vomiting",
        "Severity: Non-serious", "Batch: BATCH-200", "Reporter: Dr. Jones",
    ])
    created.append("safety_002.pdf")
    create_pdf("safety_003.pdf", "ICSR Report", [
        "Patient ID: PAT-300", "Product: Product C", "Reaction: Rash",
        "Severity: Non-serious", "Batch: BATCH-300",
    ])
    created.append("safety_003.pdf")
    print("Creating quality complaint PDFs...")
    create_pdf("pqc_001.pdf", "Quality Complaint", [
        "Product: Product B", "Batch: BATCH-99",
        "Problem: Damaged packaging, tablets broken",
        "Photo: attached image of damaged box",
    ])
    created.append("pqc_001.pdf")
    create_pdf("pqc_002.pdf", "Product Complaint", [
        "Product: Product D", "Batch: BATCH-50",
        "Problem: Discoloration of tablets, unusual odor",
        "Photo: see attached photograph",
    ])
    created.append("pqc_002.pdf")
    print("Creating MI request PDFs...")
    create_pdf("mi_001.pdf", "Medical Information Request", [
        "Question: What is the recommended dosage for Product C?",
        "Topic: Dosage adjustment", "Reporter: Dr. Williams",
    ])
    created.append("mi_001.pdf")
    create_pdf("mi_002.pdf", "Information Request", [
        "Question: Contraindications for Product A with warfarin?",
        "Topic: Drug interaction", "Reporter: Pharmacist Brown",
    ])
    created.append("mi_002.pdf")
    print("Creating not-relevant PDFs...")
    create_pdf("notrel_001.pdf", "Conference Registration", [
        "Thank you for registering for the Annual Healthcare Conference 2026.",
    ])
    created.append("notrel_001.pdf")
    create_pdf("notrel_002.pdf", "Invoice", [
        "Invoice #INV-2026-001", "Amount: $1,500.00",
    ])
    created.append("notrel_002.pdf")
    print("Creating table PDF...")
    create_table_pdf("table_001.pdf", "Batch Quality Data",
        ["Batch", "Product", "Result", "Date"],
        [["B-001", "Product A", "Pass", "2026-01-15"],
         ["B-002", "Product A", "Pass", "2026-01-16"],
         ["B-003", "Product B", "Fail", "2026-01-17"],
         ["B-004", "Product B", "Pass", "2026-01-18"]])
    created.append("table_001.pdf")
    print("Creating non-English PDFs...")
    create_pdf("spanish_001.pdf", "Informe de Evento Adverso", [
        "Paciente: P-500", "Producto: Producto A",
        "Reaccion: Dolor de cabeza", "Gravedad: Grave", "Lote: LOTE-500",
    ])
    created.append("spanish_001.pdf")
    create_pdf("french_001.pdf", "Rapport d'Effet Indesirable", [
        "Patient: P-600", "Produit: Produit B",
        "Reaction: Nausee", "Gravite: Serieux", "Lot: LOT-600",
    ])
    created.append("french_001.pdf")
    print("Creating adversarial test PDFs...")
    create_pdf("adversarial_001.pdf", "Tricky Report", [
        "Patient developed nausea after Product A.",
        "Patient experienced headache.",
        "Patient received Product B for 5 days.",
    ])
    created.append("adversarial_001.pdf")
    print(f"\nCreated {len(created)} PDFs")
    manifest = {"created": time.strftime("%Y-%m-%dT%H:%M:%SZ"), "files": created, "count": len(created)}
    with open(os.path.join(DATA_DIR, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=2)

if __name__ == "__main__":
    main()
