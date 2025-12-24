from datetime import datetime, date
from typing import Dict, Any
from .invoice_schema import InvoiceSchema


def format_invoice(inv: dict) -> Dict[str, Any]:
    """
    Normalize and format an invoice into a Qualified Invoice System–compliant structure.
    Automatically calculates tax, applies reduced-rate flags, and formats currency.
    """
    if isinstance(inv.get("subtotal_display"), str) and inv.get("subtotal"):
        return inv  # already formatted

    # --- 1️⃣ Validate and normalize using the schema ---
    try:
        model = InvoiceSchema(**inv)
        inv = model.dict()
    except Exception as e:
        print(f"⚠️ Schema warning: {e}")

    # --- 2️⃣ Helper for currency formatting ---
    def fmt_yen(value) -> str:
        try:
            return f"¥{int(round(float(value))):,}"
        except Exception:
            return "¥0"

        # --- 🧹 Auto-corrections for common issues ---
    # Fix non-ISO date format
    if "date" in inv:
        try:
            datetime.fromisoformat(inv["date"])
        except Exception:
            from batch_runner import parse_date  # reuse your helper
            inv["date"] = parse_date(inv.get("date", ""))

    # Ensure tax_rate has a % if given as plain number
    if "tax_rate" in inv:
        rate_str = str(inv["tax_rate"]).strip()
        if not rate_str.endswith("%"):
            try:
                # Convert numeric strings like '8' or '10' to '8%' / '10%'
                num = float(rate_str)
                inv["tax_rate"] = f"{int(num)}%"
            except Exception:
                inv["tax_rate"] = "10%"

    # Normalize issuer_id capitalization (e.g., 't123...' → 'T123...')
    if "issuer_id" in inv and isinstance(inv["issuer_id"], str):
        if inv["issuer_id"].lower().startswith("t"):
            inv["issuer_id"] = "T" + inv["issuer_id"][1:]

    # Trim whitespace in key text fields
    for field in ["invoice_number", "issuer_name", "address", "email", "phone"]:
        if field in inv and isinstance(inv[field], str):
            inv[field] = inv[field].strip()

    # --- 3️⃣ Determine correct tax rate (8% or 10%) ---
    try:
        rate = float(inv.get("tax_rate", 10))
        if rate not in (8, 10):
            print(f"⚠️ Unknown tax rate {rate} — defaulting to 10%")
            rate = 10.0
    except Exception:
        rate = 10.0

    # --- 4️⃣ Core calculations ---
    subtotal = float(inv.get("subtotal", 0))
    tax_amount = float(inv.get("tax_amount", subtotal * rate / 100))
    total = float(inv.get("total", subtotal + tax_amount))

    # --- 5️⃣ Reduced-rate flag ---
    reduced_rate_flag = "※軽減税率対象" if rate == 8 else inv.get("reduced_rate_flag", "")

    # --- 6️⃣ Build final formatted dictionary ---
    invoice: Dict[str, Any] = {
        # Identifiers
        "invoice_number": inv.get("invoice_number", ""),
        "issue_date": inv.get("issue_date", datetime.now().strftime("%Y-%m-%d")),
        "transaction_date": inv.get("transaction_date", ""),
        # Issuer
        "issuer_name": inv.get("issuer_name", ""),
        "issuer_id": inv.get("issuer_id", ""),
        "address": inv.get("address", ""),
        "phone": inv.get("phone", ""),
        "email": inv.get("email", ""),
        # Buyer
        "buyer_name": inv.get("buyer_name", ""),
        # Amounts
        "subtotal": subtotal,
        "subtotal_display": fmt_yen(subtotal),
        "tax_rate": rate,
        "tax_amount": tax_amount,
        "tax_amount_display": fmt_yen(tax_amount),
        "total": total,
        "total_display": fmt_yen(total),
        # Compliance
        "reduced_rate_flag": reduced_rate_flag,
        "remarks": inv.get("remarks", ""),
        # Validation info
        "validation_status": inv.get("validation_status", ""),
        "validation_message": inv.get("validation_message", ""),
    }

    return invoice

