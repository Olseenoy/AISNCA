# pdf_generator.py
from fpdf import FPDF
from io import BytesIO

def make_report_pdf(payload: dict) -> bytes:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 8, "Non-Conformance Analysis Report", ln=True, align="C")
    pdf.ln(4)

    pdf.set_font("Arial", "", 10)
    def add_kv(k, v):
        pdf.set_font("Arial", "B", 10)
        pdf.cell(40, 6, f"{k}:")
        pdf.set_font("Arial", "", 10)
        pdf.multi_cell(0, 6, str(v))
    add_kv("Timestamp", payload.get("timestamp"))
    add_kv("Factory", payload.get("factory"))
    add_kv("Shift", payload.get("shift"))
    add_kv("Machine", payload.get("machine"))
    add_kv("Issue", payload.get("issue"))
    add_kv("Additional Notes", payload.get("additional_notes") or "None")
    pdf.ln(4)

    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, "Historical Evidence:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, payload.get("evidence_text") or "None found")

    pdf.ln(2)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, "Expanded Root Cause:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, payload.get("expanded_root_cause") or "")

    pdf.ln(2)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 6, "Suggested CAPA:", ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.multi_cell(0, 6, payload.get("capa") or "")

    pdf.ln(8)
    pdf.cell(0, 6, "Prepared by Smart NC Analyzer", ln=True)

    buf = BytesIO()
    pdf.output(buf)
    return buf.getvalue()
