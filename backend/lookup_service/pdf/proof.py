import io
import zipfile
from datetime import datetime, timezone
from typing import Any, Dict, List

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


def generate_pdf(result: Dict[str, Any]) -> bytes:
    """Generate a single PDF verification report from a lookup result."""
    buffer = io.BytesIO()
    
    try:
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Title
        c.setFont("Helvetica-Bold", 20)
        c.drawString(1 * inch, height - 1 * inch, "Audos Lookup — Verification Report")
        
        y_pos = height - 1.5 * inch
        
        # Business ID
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1 * inch, y_pos, "Business ID:")
        c.setFont("Helvetica", 12)
        business_id = result.get("business_id", "N/A")
        c.drawString(2.5 * inch, y_pos, str(business_id))
        y_pos -= 0.3 * inch
        
        # Company Name
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1 * inch, y_pos, "Company Name:")
        c.setFont("Helvetica", 12)
        company_name = result.get("company_name", "N/A")
        c.drawString(2.5 * inch, y_pos, str(company_name))
        y_pos -= 0.3 * inch
        
        # Address
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1 * inch, y_pos, "Address:")
        c.setFont("Helvetica", 12)
        address = result.get("address") or "N/A"
        c.drawString(2.5 * inch, y_pos, str(address))
        y_pos -= 0.3 * inch
        
        # Timestamp
        c.setFont("Helvetica-Bold", 12)
        c.drawString(1 * inch, y_pos, "Timestamp:")
        c.setFont("Helvetica", 12)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        c.drawString(2.5 * inch, y_pos, timestamp)
        y_pos -= 0.5 * inch
        
        # Footer
        c.setFont("Helvetica", 10)
        c.drawString(1 * inch, 0.5 * inch, "Verified via Japan NTA Corporate Number API")
        
        c.save()
        buffer.seek(0)
        return buffer.getvalue()
    except Exception:
        return b""


def generate_pdf_zip(results: List[Dict[str, Any]]) -> bytes:
    """Generate multiple PDFs and package them into a ZIP file."""
    zip_buffer = io.BytesIO()
    
    try:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for idx, result in enumerate(results):
                try:
                    pdf_bytes = generate_pdf(result)
                    if not pdf_bytes:
                        continue
                    
                    business_id = result.get("business_id", f"unknown_{idx}")
                    filename = f"verification_{business_id}.pdf"
                    zip_file.writestr(filename, pdf_bytes)
                except Exception:
                    continue
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    except Exception:
        return b""

