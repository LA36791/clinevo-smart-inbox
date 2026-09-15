"""Generate ambiguous + article-style + multi-page scanned synthetic fixtures.

All content is fictional. No PHI. Run from ai-service/ with the project venv.
"""
import os

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

OUT = os.path.join("..", "data")

def make(path, pages):
    c = canvas.Canvas(os.path.join(OUT, path), pagesize=letter)
    for draw in pages:
        draw(c)
        c.showPage()
    c.save()

def lines(c, items, x=72, y=740, step=16):
    for t in items:
        c.drawString(x, y, t)
        y -= step
    return y

# 1) Ambiguous case: MI-shaped question that also mentions a possible adverse event.
def ambiguous(c):
    y = lines(c, [
        "Product Information Inquiry (Internal Ref: AMB-001)",
        "Date: 2026-09-20",
        "",
        "Dear Medical Information Team,",
        "",
        "I read online that CardioRelax may cause dizziness in some patients.",
        "A colleague who takes CardioRelax mentioned she felt dizzy once last",
        "week after her evening dose. Could you clarify whether dizziness is a",
        "known side effect, and whether she should stop taking it?",
        "",
        "She has not reported this to any doctor. No batch number available.",
        "",
        "Regards,",
        "Dana Whitfield",
    ])

make("ambiguous_001.pdf", [ambiguous])

# 2) Article-style multi-column PDF (two columns, fictional journal).
def article(c):
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(306, 760, "Journal of Fictional Therapeutics (2026) 12(3): 45-52")
    c.setFont("Helvetica", 11)
    c.drawCentredString(306, 742, "Observational Cohort of Once-Daily CardioRelax in Fictional Patients")
    c.setFont("Helvetica", 9)
    c.drawCentredString(306, 728, "A. Author, B. Author - Fictional University Press. DOI: 10.0000/fict.2026.0045")
    mid = 306
    col1 = [
        "Abstract", "", "We reviewed 40 fictional patients taking",
        "CardioRelax 10 mg once daily. Two cases",
        "reported mild nausea after the first dose.",
        "No serious adverse events were recorded",
        "in the fictional cohort.", "",
        "Methods", "", "Records were abstracted from the",
        "fictional registry between January and",
        "March 2026. Demographics, dose and",
        "onset were tabulated.",
    ]
    col2 = [
        "Case vignette", "", "Patient P-17, age 52, female,",
        "developed nausea within 2 hours of the",
        "first dose of CardioRelax 10 mg",
        "(Batch CR-4402). The event resolved by",
        "the next day without treatment.", "",
        "Discussion", "", "Product quality was normal for the",
        "batch; the event is consistent with a",
        "known tolerance effect. Complaints",
        "about tablet discoloration were not",
        "confirmed on inspection.",
    ]
    lines(c, col1, x=60, y=700)
    lines(c, col2, x=mid + 20, y=700)

make("article_001.pdf", [article])

# 3) Multi-page scanned-style ICSR: page 1 patient/reporter/product, page 2 reaction, page 3 missing info.
def mp_page1(c):
    lines(c, [
        "SERIOUS ADVERSE EVENT REPORT (SCANNED COPY)",
        "Report ID: MP-OCR-001          Page 1 of 3",
        "",
        "Reporter: Dr. Elena Ruiz (Hospital)",
        "Patient ID: P-901",
        "Patient Age: 67",
        "Sex: F",
        "Weight: 70 kg",
        "Product: CardioRelax",
        "Dose: 5 mg",
        "Route: Oral",
        "Batch/Lot: CR-7712",
    ])

def mp_page2(c):
    lines(c, [
        "SERIOUS ADVERSE EVENT REPORT (SCANNED COPY)",
        "Report ID: MP-OCR-001          Page 2 of 3",
        "",
        "Reaction: Syncope",
        "Onset: 2026-09-14 (2 days after start)",
        "Outcome: Recovered",
        "Severity: Serious",
        "",
        "Narrative: Patient collapsed at home two days after",
        "starting CardioRelax 5 mg once daily. Hospitalized",
        "overnight for observation. Recovered fully.",
    ])

def mp_page3(c):
    lines(c, [
        "SERIOUS ADVERSE EVENT REPORT (SCANNED COPY)",
        "Report ID: MP-OCR-001          Page 3 of 3",
        "",
        "Medical history: not stated in this copy",
        "Stop date: not stated in this copy",
        "Additional documents requested from reporter.",
    ])

make("scanned_multipage_001.pdf", [mp_page1, mp_page2, mp_page3])

print("fixtures written: ambiguous_001.pdf, article_001.pdf, scanned_multipage_001.pdf")
