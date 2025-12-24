from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
import os
import textwrap
from datetime import datetime, timezone

# === Constants for bilingual labels ===
LABELS = {
    "invoice_title": ("請求書", "INVOICE"),
    "invoice_number": ("請求番号", "Invoice No."),
    "issue_date": ("発行日", "Issue Date"),
    "transaction_date": ("取引日", "Transaction Date"),
    "registration_number": ("登録番号", "Registration No."),
    "qualified_issuer": ("適格請求書発行事業者", "Qualified Invoice Issuer"),
    "seller": ("請求元", "Seller"),
    "buyer": ("請求先", "Buyer"),
    "address": ("住所", "Address"),
    "phone": ("電話", "Phone"),
    "email": ("メール", "Email"),
    "description": ("品目", "Description"),
    "quantity": ("数量", "Quantity"),
    "unit_price": ("単価", "Unit Price"),
    "tax_rate": ("税率", "Tax Rate"),
    "amount": ("金額", "Amount"),
    "subtotal": ("小計", "Subtotal"),
    "tax": ("税額", "Tax"),
    "total": ("合計", "Total"),
    "notes": ("備考", "Notes"),
    "issuer": ("発行者", "Issuer"),
    "reduced_rate_note": ("※ 軽減税率対象商品を含む場合があります。", "※ May include reduced tax rate items."),
}

# === Helper functions ===
def format_currency(amount):
    """Format amount as Japanese currency with commas and two decimals."""
    return f"¥{float(amount):,.2f}"

def format_bilingual_label(ja, en):
    """Format bilingual label with Japanese first, English subtitle."""
    return f"{ja} / {en}"

def get_label(key, language="en"):
    """Get label based on language preference. Returns Japanese, English, or bilingual."""
    if key not in LABELS:
        return ""
    ja, en = LABELS[key]
    if language == "ja":
        return ja
    elif language == "en":
        return en
    else:
        # Default to bilingual
        return format_bilingual_label(ja, en)

def draw_bilingual_text(pdf, x, y, ja, en, font_name="NotoSansJP", font_size=11, align="LEFT"):
    """Draw bilingual text with Japanese and English subtitle."""
    if align == "RIGHT":
        pdf.drawRightString(x, y, format_bilingual_label(ja, en))
    elif align == "CENTER":
        pdf.drawCentredString(x, y, format_bilingual_label(ja, en))
    else:
        pdf.drawString(x, y, format_bilingual_label(ja, en))

def wrap_text(text, max_width_chars=50):
    """Wrap text preserving whitespace."""
    if not text:
        return ""
    # Preserve newlines and wrap long lines
    lines = []
    for line in text.split('\n'):
        if len(line) <= max_width_chars:
            lines.append(line)
        else:
            wrapped = textwrap.wrap(line, width=max_width_chars, break_long_words=False)
            lines.extend(wrapped)
    return '\n'.join(lines)


def generate_invoice_pdf(
    buffer,
    seller,
    buyer,
    items,
    prices,
    quantities,
    tax_rate,
    invoice_number,
    issue_date,
    registration_number,
    address,
    phone,
    email,
    transaction_date,
    reduced_rate,
    remarks,
    validation_result=None,
    language="en"
):
    # === Setup ===
    base_dir = os.path.dirname(__file__)
    pdfmetrics.registerFont(
        TTFont(
            "NotoSansJP",
            os.path.join(base_dir, "..", "fonts", "NotoSansJP-Regular.ttf"),
        )
    )
    pdfmetrics.registerFont(
        TTFont(
            "NotoSansJP-Bold",
            os.path.join(base_dir, "..", "fonts", "NotoSansJP-Bold.ttf"),
        )
    )

    pdf = canvas.Canvas(buffer, pagesize=A4)
    pdf.setTitle("日本インボイス / Japanese Invoice")

    width, height = A4
    left_margin = 20 * mm
    right_margin = 20 * mm
    top = height - 20 * mm
    line_gap = 5 * mm
    section_gap = 10 * mm

    # === Header ===
    # Title (left-aligned, larger)
    pdf.setFont("NotoSansJP-Bold", 24)
    title_label = get_label("invoice_title", language)
    pdf.drawString(left_margin, top, title_label)
    
    # Header block with invoice details (right-aligned, compact)
    header_y = top - 2 * mm
    pdf.setFont("NotoSansJP-Bold", 11)
    inv_label = get_label("invoice_number", language)
    pdf.drawRightString(width - right_margin, header_y, f"{inv_label}: {invoice_number}")
    
    header_y -= (line_gap * 0.7)
    pdf.setFont("NotoSansJP", 10)
    issue_label = get_label("issue_date", language)
    pdf.drawRightString(width - right_margin, header_y, f"{issue_label}: {issue_date}")
    
    header_y -= (line_gap * 0.7)
    if registration_number:
        reg_label = get_label("registration_number", language)
        pdf.drawRightString(width - right_margin, header_y, f"{reg_label}: {registration_number}")
    
    header_y -= (line_gap * 0.7)
    qual_label = get_label("qualified_issuer", language)
    pdf.setFont("NotoSansJP-Bold", 9)
    pdf.drawRightString(width - right_margin, header_y, qual_label)
    
    # Header separator line (thicker)
    header_y -= (line_gap * 0.8)
    pdf.setStrokeColor(colors.HexColor("#000000"))
    pdf.setLineWidth(1)
    pdf.line(left_margin, header_y, width - right_margin, header_y)

    # === Seller info ===
    y = header_y - section_gap
    pdf.setFont("NotoSansJP-Bold", 12)
    seller_label = get_label("seller", language)
    pdf.drawString(left_margin, y, seller_label)
    
    y -= (line_gap * 0.9)
    pdf.setFont("NotoSansJP", 11)
    pdf.drawString(left_margin + 3 * mm, y, seller)
    
    if address:
        y -= (line_gap * 0.85)
        pdf.setFont("NotoSansJP", 10)
        pdf.drawString(left_margin + 3 * mm, y, address)
    
    if phone or email:
        y -= (line_gap * 0.85)
        pdf.setFont("NotoSansJP", 9)
        contact_parts = []
        if phone:
            phone_label = get_label("phone", language)
            contact_parts.append(f"{phone_label}: {phone}")
        if email:
            email_label = get_label("email", language)
            contact_parts.append(f"{email_label}: {email}")
        if contact_parts:
            pdf.drawString(left_margin + 3 * mm, y, "  ".join(contact_parts))

    # === Buyer info ===
    y -= section_gap
    pdf.setFont("NotoSansJP-Bold", 12)
    buyer_label = get_label("buyer", language)
    pdf.drawString(left_margin, y, buyer_label)
    
    y -= (line_gap * 0.9)
    pdf.setFont("NotoSansJP", 11)
    pdf.drawString(left_margin + 3 * mm, y, f"{buyer} 御中")

    # Separator line before table (thicker)
    y -= (line_gap * 1.5)
    pdf.setStrokeColor(colors.HexColor("#000000"))
    pdf.setLineWidth(1)
    pdf.line(left_margin, y, width - right_margin, y)
    y -= (line_gap * 0.8)

    # === Item Table ===
    # Language-aware table headers
    desc_label = get_label("description", language)
    qty_label = get_label("quantity", language)
    price_label = get_label("unit_price", language)
    amount_label = get_label("amount", language)
    
    table_data = [[
        desc_label,
        qty_label,
        price_label,
        amount_label
    ]]
    
    total = 0
    for item, qty, price in zip(items, quantities, prices):
        subtotal = float(qty) * float(price)
        total += subtotal
        table_data.append([
            str(item),
            f"{float(qty):.2f}" if float(qty) != int(float(qty)) else f"{int(float(qty))}",
            format_currency(price),
            format_currency(subtotal)
        ])

    tax = total * (tax_rate / 100)
    grand_total = total + tax

    # NTA-compliant table styling
    table = Table(table_data, colWidths=[90 * mm, 25 * mm, 30 * mm, 35 * mm])
    table.setStyle(
        TableStyle(
            [
                # Header row styling - prominent and clear
                ("FONT", (0, 0), (-1, 0), "NotoSansJP-Bold", 11),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F5F5F5")),  # Light gray background
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#000000")),
                ("LINEBELOW", (0, 0), (-1, 0), 1.5, colors.HexColor("#000000")),  # Strong border
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                
                # Data rows styling - clean and readable
                ("FONT", (0, 1), (-1, -1), "NotoSansJP", 10),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),  # Right-align numbers
                ("ALIGN", (0, 1), (0, -1), "LEFT"),  # Left-align description
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                
                # Borders - clear and professional
                ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#000000")),  # Strong outer border
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),  # Visible inner grid
                
                # Padding for readability
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 1), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
            ]
        )
    )

    # Render the table
    table_y = y - 8 * mm
    table.wrapOn(pdf, width, height)
    table_height = len(table_data) * 6.5 * mm
    table.drawOn(pdf, left_margin, table_y - table_height)

    # === Totals section === (NTA-compliant, prominent)
    totals_y = table_y - table_height - section_gap
    
    # Top separator line
    pdf.setStrokeColor(colors.HexColor("#000000"))
    pdf.setLineWidth(1)
    pdf.line(left_margin, totals_y + 6 * mm, width - right_margin, totals_y + 6 * mm)
    
    # Subtotal
    totals_y += 1 * mm
    pdf.setFont("NotoSansJP", 11)
    sub_label = get_label("subtotal", language)
    pdf.drawRightString(width - right_margin, totals_y, sub_label)
    pdf.drawRightString(width - right_margin - 50 * mm, totals_y, format_currency(total))
    
    # Tax
    totals_y -= (line_gap * 0.9)
    tax_label = get_label("tax", language)
    pdf.drawRightString(width - right_margin, totals_y, f"{tax_label} ({tax_rate}%)")
    pdf.drawRightString(width - right_margin - 50 * mm, totals_y, format_currency(tax))
    
    # Grand Total - prominent
    totals_y -= (line_gap * 1.3)
    pdf.setFont("NotoSansJP-Bold", 14)
    total_label = get_label("total", language)
    pdf.drawRightString(width - right_margin, totals_y, total_label)
    pdf.drawRightString(width - right_margin - 50 * mm, totals_y, format_currency(grand_total))
    
    # Strong separator line below total
    totals_y -= (line_gap * 1.0)
    pdf.setLineWidth(1.5)
    pdf.line(left_margin, totals_y, width - right_margin, totals_y)

    # === Optional reduced tax note ===
    if tax_rate < 10:
        totals_y -= (line_gap * 1.5)
        pdf.setFont("NotoSansJP", 8)
        pdf.setFillColor(colors.HexColor("#666666"))
        note_label = get_label("reduced_rate_note", language)
        pdf.drawString(left_margin, totals_y, note_label)
        pdf.setFillColor(colors.black)

    # === Footer / Remarks ===
    if remarks and remarks.strip():
        # Calculate available space for remarks
        remarks_y = totals_y - (section_gap * 1.5)
        min_y = 50 * mm  # Minimum space from bottom
        
        if remarks_y > min_y:
            pdf.setFont("NotoSansJP-Bold", 10)
            notes_label = get_label("notes", language)
            pdf.drawString(left_margin, remarks_y, f"{notes_label}:")
            
            remarks_y -= (line_gap * 0.8)
            pdf.setFont("NotoSansJP", 9)
            pdf.setFillColor(colors.HexColor("#333333"))
            
            # Wrap and render remarks with whitespace preservation
            wrapped_remarks = wrap_text(remarks.strip(), max_width_chars=70)
            remarks_lines = wrapped_remarks.split('\n')
            
            for line in remarks_lines:
                if remarks_y < min_y:
                    break
                pdf.drawString(left_margin + 5 * mm, remarks_y, line)
                remarks_y -= (line_gap * 0.9)
            
            pdf.setFillColor(colors.black)
    
    # === Compliance Stamp ===
    if validation_result:
        compliant = validation_result.get("overall", {}).get("compliant", False)
        status_en = validation_result["overall"]["summary"]["en"]
        status_ja = validation_result["overall"]["summary"]["ja"]

        # Generate timestamp at PDF generation time (UTC)
        timestamp_utc = datetime.now(timezone.utc)
        timestamp_str = timestamp_utc.strftime("%Y-%m-%d %H:%M UTC")

        pdf.setFont("NotoSansJP-Bold", 9)

        # ✅ Green if compliant, 🔴 Red if failed
        if compliant:
            pdf.setFillColorRGB(0, 0.6, 0)  # green
            stamp_text = f"PASS – {timestamp_str} / 検証成功 – {timestamp_str}"
        else:
            pdf.setFillColorRGB(1, 0, 0)    # red
            stamp_text = f"FAIL – {timestamp_str} / 検証失敗 – {timestamp_str}"

        # Draw bilingual stamp at bottom left
        pdf.drawString(20 * mm, 15 * mm, stamp_text)

        # Reset color to black for rest of document
        pdf.setFillColorRGB(0, 0, 0)
        
        # === Auto-format Footer ===
        auto_fix_summary = validation_result.get("auto_fix_summary", {})
        auto_fixed = auto_fix_summary.get("auto_fixed", [])
        
        if auto_fixed:
            # Set subtle gray color
            pdf.setFillColorRGB(0.5, 0.5, 0.5)  # gray
            pdf.setFont("NotoSansJP", 7)  # small font
            
            # Build footer text
            footer_text = "Auto-formatted: " + ", ".join(auto_fixed)
            
            # Draw footer below stamp (at 10mm from bottom)
            pdf.drawString(20 * mm, 10 * mm, footer_text)
            
            # Reset color to black
            pdf.setFillColorRGB(0, 0, 0)

    
    pdf.showPage()
    pdf.save()

    # === Save ===
    os.makedirs("output", exist_ok=True)
    with open("output/invoice_latest.pdf", "wb") as f:
        f.write(buffer.getbuffer())

      

    