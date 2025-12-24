from flask import Flask, render_template, request, send_file, jsonify
from pdf.pdf_generator import generate_invoice_pdf
import io
import os
import csv
import json
from validator.validator import InvoiceValidator
from db.models import init_db, insert_invoice
init_db()

app = Flask(__name__)
validator = InvoiceValidator()


@app.route("/")
def index():
    return render_template("invoice.html")


@app.route("/generate", methods=["POST"])
def generate():
    # Basic seller/buyer info
    issuer_name = request.form["issuer_name"]
    buyer = request.form["buyer"]

    # Header fields
    invoice_number = request.form["invoice_number"]
    issue_date = request.form["date"]
    registration_number = request.form["issuer_id"]
    address = request.form["address"]
    phone = request.form["phone"]
    email = request.form["email"]

    # Additional compliance fields
    transaction_date = request.form.get("transaction_date", "")
    reduced_rate = "※軽減税率対象" if "reduced_rate" in request.form else ""
    remarks = request.form.get("remarks", "")

    # Item details
    items = request.form.getlist("item")
    prices = request.form.getlist("price")
    quantities = request.form.getlist("quantity")
    tax_rate = float(request.form["tax_rate"])

    # --- Build invoice dict for validator ---
    invoice_data = {
        "invoice_number": invoice_number,
        "issuer_id": registration_number,
        "issuer_name": issuer_name,
        "buyer": buyer,
        "date": issue_date,
        "phone": phone,
        "email": email,
        "address": address,
        "items": [],
    }

    for item, price, qty in zip(items, prices, quantities):
        try:
            amt = float(price) * float(qty)
        except ValueError:
            amt = 0
        invoice_data["items"].append({
            "description": item,
            "amount_excl_tax": amt,
            "tax_rate": f"{int(tax_rate)}%"
        })

    # --- Run validator automatically ---
    validation_result = validator.validate(invoice_data, language="both")
    compliant = validation_result["overall"]["compliant"]

    # --- Generate PDF buffer ---
    pdf_buffer = io.BytesIO()
    generate_invoice_pdf(
        pdf_buffer,
        issuer_name,
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
        validation_result=validation_result,
    )

    # --- Log to database (Phase 5 logic) ---
    from db.models import insert_invoice
    status = "pass" if compliant else "fail"
    pdf_path = f"output/invoice_{invoice_number}.pdf" if compliant else None

    insert_invoice(
        invoice_number=invoice_number,
        status=status,
        issues_count=validation_result["issues_count"],
        pdf_path=pdf_path,
        ruleset_version="2025-10",
    )

    # --- Save PDF only if compliant ---
    if compliant:
        import os
        os.makedirs("output", exist_ok=True)
        with open(f"output/invoice_{invoice_number}.pdf", "wb") as f:
            f.write(pdf_buffer.getbuffer())

    # --- Always return the generated file to the browser ---
    pdf_buffer.seek(0)
    return send_file(
        pdf_buffer,
        as_attachment=True,
        download_name=f"invoice_{invoice_number}.pdf",
        mimetype="application/pdf",
    )

@app.route("/validate_field", methods=["POST"])
def validate_field():
    data = request.get_json()
    field_name = data.get("field")
    field_value = data.get("value")

    result = validator.validate_field_only(field_name, field_value)
    return result



# =======================
# 📦 Batch Processing API
# =======================
@app.route("/validate_batch", methods=["POST"])
def validate_batch():
    """
    Accepts a JSON array of invoices.
    Runs full normalization, validation, PDF generation, and creates a manifest.
    Returns a JSON summary including invoice-level errors and metadata.
    """
    from batch_runner import run_batch
    from errors import BatchProcessingError, ValidationError, PDFGenerationError, StorageError

    if not request.is_json:
        return {"error": "Expected a JSON array of invoices."}, 400

    data = request.get_json()

    # ✅ Support both formats: {"invoices": [...]} or a direct list
    if isinstance(data, dict) and "invoices" in data:
        invoices = data["invoices"]
    elif isinstance(data, list):
        invoices = data
    else:
        return {
            "error": "Invalid format. Expected a JSON array or an 'invoices' key."
        }, 400

    try:
        summary = run_batch(invoices)
        return summary, 200

    except (ValidationError, PDFGenerationError, StorageError) as e:
        return {
            "error_type": e.__class__.__name__,
            "error": str(e),
            "message": "An error occurred while processing one or more invoices.",
        }, 422

    except BatchProcessingError as e:
        return {
            "error_type": "BatchProcessingError",
            "error": str(e),
            "message": "Batch-level failure — no invoices were processed successfully.",
        }, 500

    except Exception as e:
        return {
            "error_type": "UnexpectedError",
            "error": str(e),
            "message": "An unknown error occurred during batch validation.",
        }, 500


# =======================
# 📤 CSV Batch Upload
# =======================

# Full-width → Half-width normalization
try:
    import jaconv
    def normalize_text(s):
        return jaconv.z2h(s or "", ascii=True, digit=True)
except:
    def normalize_text(s):
        return s or ""

def normalize_tax_rate(rate):
    """Normalize tax rate to format like '10%' or '8%'."""
    r = str(rate or "").strip().replace("％", "%")
    if r.endswith("%"):
        return r
    if r.isdigit():
        return r + "%"
    return "10%"

def clean_number(n):
    """Clean number fields by removing commas and yen symbols."""
    if not n:
        return "0"
    return str(n).replace(",", "").replace("¥", "").strip()

def parse_csv_items(row):
    """Parse items from CSV row with multiple format support."""
    items = []
    
    # Format 1: items column with JSON array
    if 'items' in row and row.get('items', '').strip():
        try:
            items_data = json.loads(row['items'])
            if isinstance(items_data, list):
                items = items_data
            elif isinstance(items_data, dict):
                items = [items_data]
        except json.JSONDecodeError:
            pass  # Fall through to other formats
    
    # Format 2: Individual item columns
    if not items:
        item_desc = (row.get('item_description') or row.get('description') or 
                    row.get('item') or '').strip()
        item_desc = normalize_text(item_desc)
        
        qty = row.get('quantity')
        item_qty = qty.strip() if qty and qty.strip() else "1"
        item_qty = clean_number(item_qty)
        
        item_price = clean_number(row.get('price') or row.get('amount_excl_tax') or 
                                 row.get('amount', '0'))
        item_tax_rate = normalize_tax_rate(row.get('tax_rate', '10%'))
        
        if item_desc or item_price:
            items = [{
                "description": item_desc,
                "quantity": item_qty,
                "price": item_price,
                "tax_rate": item_tax_rate
            }]
    
    # Format 3: Multiple items with numbered columns (item_1, item_2, etc.)
    if not items:
        item_index = 1
        while True:
            desc_key = f'item_{item_index}_description'
            simple_key = f'item_{item_index}'
            qty_key = f'item_{item_index}_quantity'
            price_key = f'item_{item_index}_price'
            
            if desc_key not in row and simple_key not in row:
                break
            
            item_desc = (row.get(desc_key) or row.get(simple_key, '')).strip()
            item_desc = normalize_text(item_desc)
            
            if item_desc:
                qty = row.get(qty_key)
                item_qty = qty.strip() if qty and qty.strip() else "1"
                item_qty = clean_number(item_qty)
                
                item_price = clean_number(row.get(price_key, '0'))
                item_tax_rate = normalize_tax_rate(
                    row.get(f'item_{item_index}_tax_rate') or row.get('tax_rate', '10%')
                )
                items.append({
                    "description": item_desc,
                    "quantity": item_qty,
                    "price": item_price,
                    "tax_rate": item_tax_rate
                })
            item_index += 1
    
    # Normalize tax_rate in all items
    for item in items:
        if 'tax_rate' in item:
            item['tax_rate'] = normalize_tax_rate(item['tax_rate'])
        else:
            item['tax_rate'] = '10%'
    
    # Always return a list (even if empty)
    return items

@app.route("/upload_batch", methods=["POST"])
def upload_batch():
    """
    Accepts multipart/form-data with a field named `csv_file`.
    Parses CSV into invoices list and processes batch.
    Returns JSON with batch_id, counts, invoices[], and zip_path.
    """
    from batch_runner import run_batch
    from errors import BatchProcessingError, ValidationError, PDFGenerationError, StorageError
    
    if 'csv_file' not in request.files:
        return jsonify({"error": "No CSV file provided"}), 400
    
    file = request.files['csv_file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400
    
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "File must be a CSV file"}), 400
    
    try:
        # Read and parse CSV
        stream = io.TextIOWrapper(file.stream, encoding='utf-8')
        csv_reader = csv.DictReader(stream)
        
        # Group rows by invoice_number (in case CSV has multiple rows per invoice)
        invoice_map = {}
        required_columns = ['invoice_number', 'issuer_name', 'buyer']
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            # Ignore fully empty rows
            if not any(v and v.strip() for v in row.values()):
                continue
            
            invoice_number = row.get('invoice_number', '').strip()
            if not invoice_number:
                continue  # Skip rows without invoice_number
            
            # Parse items for this row
            row_items = parse_csv_items(row)
            
            # Group by invoice_number - merge items if invoice already exists
            if invoice_number not in invoice_map:
                # Create new invoice entry
                invoice = {
                    "invoice_number": invoice_number,
                    "date": normalize_text(row.get('date', '')).strip(),
                    "issuer_name": normalize_text(row.get('issuer_name', '')).strip(),
                    "buyer": normalize_text(row.get('buyer', '')).strip(),
                    "issuer_id": normalize_text(row.get('issuer_id', '')).strip(),
                    "email": normalize_text(row.get('email', '')).strip(),
                    "phone": normalize_text(row.get('phone', '')).strip(),
                    "address": normalize_text(row.get('address', '')).strip(),
                    "items": row_items
                }
                
                # Preserve optional fields
                if 'transaction_date' in row and row.get('transaction_date'):
                    invoice["transaction_date"] = normalize_text(row.get('transaction_date', '')).strip()
                if 'remarks' in row and row.get('remarks'):
                    invoice["remarks"] = row.get('remarks', '').strip()
                if 'reduced_rate_flag' in row and row.get('reduced_rate_flag'):
                    invoice["reduced_rate_flag"] = row.get('reduced_rate_flag', '').strip()
                
                invoice_map[invoice_number] = invoice
                
                # Warn about missing required columns (but don't fail)
                missing_required = [col for col in required_columns if not invoice.get(col)]
                if missing_required:
                    print(f"Warning: row {row_num} missing required columns: {missing_required}")
            else:
                # Merge items into existing invoice
                invoice_map[invoice_number]["items"].extend(row_items)
        
        # Return final invoice list
        invoices = list(invoice_map.values())
        
        if not invoices:
            return jsonify({"error": "No invoices found in CSV file"}), 400
        
        # Process batch
        summary = run_batch(invoices)
        
        # Format response to match expected structure
        response = {
            "batch_id": summary.get("batch_id"),
            "counts": summary.get("counts", {"pass": 0, "fail": 0}),
            "invoices": [
                {
                    "invoice_number": inv.get("invoice_number"),
                    "status": inv.get("status"),
                    "issues": inv.get("issues") or inv.get("issues_count", 0),
                    "pdf_path": inv.get("pdf_path")
                }
                for inv in summary.get("invoices", [])
            ]
        }
        
        # Add zip_path if available
        if summary.get("zip_path"):
            response["zip_path"] = summary["zip_path"]
        
        return jsonify(response), 200
        
    except csv.Error as e:
        return jsonify({"error": f"CSV parsing error: {str(e)}"}), 400
    except (ValidationError, PDFGenerationError, StorageError) as e:
        return jsonify({
            "error_type": e.__class__.__name__,
            "error": str(e),
            "message": "An error occurred while processing one or more invoices.",
        }), 422
    except BatchProcessingError as e:
        return jsonify({
            "error_type": "BatchProcessingError",
            "error": str(e),
            "message": "Batch-level failure — no invoices were processed successfully.",
        }), 500
    except Exception as e:
        return jsonify({
            "error_type": "UnexpectedError",
            "error": str(e),
            "message": "An unknown error occurred during batch processing.",
        }), 500


# =======================
# 📥 Download Routes
# =======================
@app.route("/download_batch/<batch_id>", methods=["GET"])
def download_batch(batch_id):
    """
    Download the ZIP file for a batch.
    """
    zip_path = os.path.join("output", "batches", f"{batch_id}.zip")
    if os.path.exists(zip_path):
        return send_file(
            zip_path,
            as_attachment=True,
            download_name=f"batch_{batch_id}.zip",
            mimetype="application/zip"
        )
    else:
        return jsonify({"error": "Batch ZIP file not found"}), 404


@app.route("/download_pdf/<path:pdf_path>", methods=["GET"])
def download_pdf(pdf_path):
    """
    Download an individual PDF file.
    pdf_path is expected to be relative to output directory (e.g., "batches/xxx/compliant/INV-001.pdf")
    """
    # Security: ensure path is within output directory
    # Remove leading slashes and normalize
    clean_path = pdf_path.lstrip("/")
    normalized_path = os.path.normpath(os.path.join("output", clean_path))
    
    # Verify it's still within output directory (prevent directory traversal)
    output_dir = os.path.normpath("output")
    if not normalized_path.startswith(output_dir):
        return jsonify({"error": "Invalid path"}), 400
    
    if os.path.exists(normalized_path) and os.path.isfile(normalized_path):
        return send_file(
            normalized_path,
            as_attachment=True,
            download_name=os.path.basename(normalized_path),
            mimetype="application/pdf"
        )
    else:
        return jsonify({"error": "PDF file not found"}), 404


if __name__ == "__main__":
    app.run(debug=True)
