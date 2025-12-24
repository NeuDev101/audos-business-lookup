import os
import io
import uuid
import json
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation

from validator.validator import InvoiceValidator
from pdf_generator.pdf.pdf_generator import generate_invoice_pdf
from db.models import insert_invoice
from .formatter import format_invoice
from .validation_helpers import validate_totals_and_tax

# Initialize shared validator
validator = InvoiceValidator()

# ===============================
# 🧩 Helpers
# ===============================

def sha256_json(obj) -> str:
    s = json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(s).hexdigest()

def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def parse_decimal(x):
    """Safely parse numbers like '￥1,000' or '（123）' into Decimal."""
    if x is None:
        return Decimal("0")
    s = str(x).replace("¥", "").replace(",", "").strip()
    s = s.replace("（", "-").replace("）", "")
    try:
        return Decimal(s)
    except InvalidOperation:
        return Decimal("0")

def parse_date(x):
    """Try to parse date strings in multiple formats to ISO (YYYY-MM-DD)."""
    from datetime import datetime
    if not x:
        return datetime.now().date().isoformat()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d-%m-%Y", "%Y.%m.%d", "%Y%m%d"):
        try:
            return datetime.strptime(x, fmt).date().isoformat()
        except Exception:
            continue
    return datetime.now().date().isoformat()

# ===============================
# 🧠 Core Batch Logic
# ===============================

from .errors import ValidationError, PDFGenerationError, StorageError, BatchProcessingError

def run_batch(invoices: list[dict], user_id: int, ruleset_version: str = "2025-10", language: str = "en") -> dict:
    """
    Runs full normalization + validation + PDF generation for a batch of invoices.
    Returns a summary dict with status counts and manifest path.
    
    Args:
        invoices: List of invoice dictionaries to process.
        user_id: ID of the user creating this batch.
        ruleset_version: Version of validation rules to use.
        language: Language for PDF generation ('en' or 'ja', default 'en').
    """

    batch_id = str(uuid.uuid4())
    # Use absolute path relative to audos_console directory
    audos_console_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    batch_dir = os.path.join(audos_console_dir, "output", "batches", batch_id)
    os.makedirs(batch_dir, exist_ok=True)

    summary = {
        "batch_id": batch_id,
        "ruleset_version": ruleset_version,
        "created_at": datetime.now().isoformat(),
        "invoices": [],
        "counts": {"pass": 0, "fail": 0, "warn": 0},
    }

    try:
        for inv in invoices:
            try:
                # --- Normalize basic fields ---
                invoice_number = inv.get("invoice_number") or f"INV-{uuid.uuid4().hex[:6]}"
                issue_date = parse_date(inv.get("date"))
                issuer_name = inv.get("issuer_name", "").strip()
                buyer = inv.get("buyer", "").strip()
                issuer_id = inv.get("issuer_id", "").strip()

                # --- Normalize item lines ---
                items = []
                for item in inv.get("items", []):
                    desc = item.get("description", "")
                    qty = parse_decimal(item.get("quantity", 1))
                    price = parse_decimal(item.get("price") or item.get("amount_excl_tax") or 0)
                    rate = item.get("tax_rate", "10%")
                    amount = qty * price
                    items.append({
                        "description": desc,
                        "amount_excl_tax": float(amount),
                        "tax_rate": rate,
                    })

                normalized_invoice = {
                    "invoice_number": invoice_number,
                    "issuer_name": issuer_name,
                    "issuer_id": issuer_id,
                    "buyer": buyer,
                    "date": issue_date,
                    "items": items,
                    "phone": inv.get("phone", "").strip(),
                    "email": inv.get("email", "").strip(),
                    "address": inv.get("address", "").strip(),
                }

                # --- Validate totals/tax if provided ---
                totals_errors = []
                if inv.get("totals"):
                    totals_errors = validate_totals_and_tax(items, inv.get("totals"))
                    if totals_errors:
                        # Add totals errors to validation result
                        # We'll merge these into the validator result below
                        pass

                # --- Validate with validator (rules.json) ---
                try:
                    invoice_language = inv.get("language") or language
                    result = validator.validate(normalized_invoice, language=invoice_language)
                except Exception as e:
                    raise ValidationError(invoice_number, {"error": str(e)})
                
                # --- Merge totals/tax errors into validation result ---
                if totals_errors:
                    # Mark overall as non-compliant if totals don't match
                    result["overall"]["compliant"] = False
                    result["overall"]["status"] = "fail"
                    result["issues_count"] = result.get("issues_count", 0) + len(totals_errors)
                    
                    # Add totals errors to fields
                    if "totals" not in result.get("fields", {}):
                        result.setdefault("fields", {})["totals"] = {
                            "status": "fail",
                            "messages": {"ja": [], "en": []},
                        }
                    
                    for error_msg in totals_errors:
                        result["fields"]["totals"]["messages"]["ja"].append(error_msg)
                        result["fields"]["totals"]["messages"]["en"].append(error_msg)

                                # --- 🧠 Auto-heal pass ---
                if not result.get("overall", {}).get("compliant", False):
                    # Try to automatically correct and re-validate
                    try:
                        print(f"🩹 Attempting auto-format for {invoice_number} (first validation failed)")
                        auto_fixed = format_invoice(normalized_invoice)
                        auto_language = inv.get("language") or language
                        result = validator.validate(auto_fixed, language=auto_language)
                        normalized_invoice = auto_fixed
                    except Exception as e:
                        print(f"⚠️ Auto-format failed for {invoice_number}: {e}")

                # --- Auto-format after validation ---

                try:
                    formatted_invoice = format_invoice(result.get("normalized", normalized_invoice))
                except Exception as e:
                    print(f"⚠️ Formatter warning for {invoice_number}: {e}")
                    formatted_invoice = normalized_invoice

                # --- Generate PDF ---
                try:
                    pdf_buffer = io.BytesIO()
                    invoice_language = inv.get("language") or language
                    generate_invoice_pdf(
                        pdf_buffer,
                        issuer_name,
                        buyer,
                        [i["description"] for i in items],
                        [str(i["amount_excl_tax"]) for i in items],
                        [1 for _ in items],
                        formatted_invoice.get("tax_rate", 10),
                        invoice_number,
                        issue_date,
                        issuer_id,
                        inv.get("address", ""),
                        inv.get("phone", ""),
                        inv.get("email", ""),
                        inv.get("transaction_date", issue_date),
                        "",
                        inv.get("remarks", ""),
                        validation_result=result,
                        language=invoice_language,
                    )
                except Exception as e:
                    raise PDFGenerationError(f"{invoice_number}: {e}")

                pdf_path = os.path.join(batch_dir, f"{invoice_number}.pdf")
                try:
                    with open(pdf_path, "wb") as f:
                        f.write(pdf_buffer.getbuffer())
                except Exception as e:
                    raise StorageError(f"Failed to save PDF for {invoice_number}: {e}")

                                # --- Phase 5: strict DB + counter logic ---
                compliant = result.get("overall", {}).get("compliant", False)
                status = "pass" if compliant else "fail"

                # Separate compliant/failed directories
                if compliant:
                    pdf_dir = os.path.join(batch_dir, "compliant")
                else:
                    pdf_dir = os.path.join(batch_dir, "failed")
                os.makedirs(pdf_dir, exist_ok=True)

                # Move file into proper directory
                final_pdf_path = os.path.join(pdf_dir, f"{invoice_number}.pdf")
                os.replace(pdf_path, final_pdf_path)

                # --- Compute hash AFTER moving file ---
                pdf_hash = sha256_file(final_pdf_path)

                # --- Insert into database (includes PDF hash) ---
                insert_invoice(
                    invoice_number=invoice_number,
                    status=status,
                    issues_count=result["issues_count"],
                    pdf_path=final_pdf_path if compliant else None,
                    pdf_hash=pdf_hash,
                    user_id=user_id,
                    ruleset_version=ruleset_version,
                    batch_id=batch_id,
                )

                # --- Accurate pass/fail counts ---
                if compliant:
                    summary["counts"]["pass"] += 1
                else:
                    summary["counts"]["fail"] += 1

                # --- Manifest entry ---
                summary["invoices"].append({
                    "invoice_number": invoice_number,
                    "status": status,
                    "compliant": compliant,
                    "issues": result["issues_count"],
                    "pdf_path": final_pdf_path,
                    "pdf_sha256": pdf_hash,
                })


            except (ValidationError, PDFGenerationError, StorageError) as e:
                summary["invoices"].append({
                    "invoice_number": inv.get("invoice_number", "unknown"),
                    "status": "fail",
                    "error": str(e),
                })
                summary["counts"]["fail"] += 1

    except Exception as e:
        raise BatchProcessingError(f"Batch-level failure: {e}")

    # --- Write manifest and optional zip ---
    manifest_path = os.path.join(batch_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    try:
        import shutil
        zip_path = shutil.make_archive(batch_dir, "zip", batch_dir)
        summary["zip_path"] = zip_path
    except Exception as e:
        summary["zip_path"] = None
        summary["zip_error"] = str(e)

    return summary
