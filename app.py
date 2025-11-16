import io
import csv
import json
import os
import traceback
from datetime import datetime
from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd

from lookup.csv_handler import process_csv
from lookup.japan import lookup_japan
from pdf.proof import generate_pdf, generate_pdf_zip

app = Flask(__name__)

# In-memory storage for bulk results
CACHE = {"bulk_results": []}

# Japanese corporate number is 13 digits
CORPORATE_NUMBER_LENGTH = 13


def validate_id_format(business_id: str) -> dict:
    """Validate business ID format. Returns error dict if invalid, None if valid."""
    if not business_id or not isinstance(business_id, str):
        return {
            "business_id": str(business_id) if business_id else "",
            "error": "Business ID is required",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    business_id = business_id.strip()
    
    if not business_id:
        return {
            "business_id": "",
            "error": "Business ID cannot be empty",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    if not business_id.isdigit():
        return {
            "business_id": business_id,
            "error": "Business ID must be numeric",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    if len(business_id) != CORPORATE_NUMBER_LENGTH:
        return {
            "business_id": business_id,
            "error": f"Business ID must be {CORPORATE_NUMBER_LENGTH} digits",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    
    return None


def lookup_business(business_id: str) -> dict:
    """Lookup business and return normalized result dict."""
    timestamp = datetime.utcnow().isoformat() + "Z"
    
    try:
        result = lookup_japan(business_id)
        
        if "error" in result:
            return {
                "business_id": business_id,
                "error": result.get("error", "Not found"),
                "timestamp": timestamp
            }
        
        return {
            "business_id": result.get("business_id", business_id),
            "name": result.get("company_name", ""),
            "address": result.get("address") or "",
            "registration_status": "active",  # Default status
            "timestamp": timestamp
        }
    except Exception as e:
        return {
            "business_id": business_id,
            "error": f"Lookup failed: {str(e)}",
            "timestamp": timestamp
        }


def log_lookup(event: str, input_data: str, output: dict, status: str):
    """Log lookup event to file-based log."""
    try:
        log_dir = os.path.join("logs", "lookups")
        os.makedirs(log_dir, exist_ok=True)
        
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"{date_str}.log")
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        output_str = json.dumps(output) if isinstance(output, dict) else str(output)
        
        log_line = f"{timestamp} | {event} | {input_data} | {output_str} | {status}\n"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        pass  # Silently fail if logging fails


def log_error(exception: Exception, context: str = ""):
    """Log error to error log file."""
    try:
        log_dir = os.path.join("logs", "errors")
        os.makedirs(log_dir, exist_ok=True)
        
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        log_file = os.path.join(log_dir, f"{date_str}.log")
        
        timestamp = datetime.utcnow().isoformat() + "Z"
        error_msg = str(exception)
        error_trace = traceback.format_exc()
        
        log_line = f"{timestamp} | {context} | {error_msg}\n{error_trace}\n---\n"
        
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(log_line)
    except Exception:
        pass  # Silently fail if error logging fails


# Logging helper
def write_log(term, status):
    """Write a log entry to logs.json, keeping only the last 500 entries."""
    log_file = "logs.json"
    
    # Read existing logs or initialize empty list
    logs = []
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = []
        except (json.JSONDecodeError, IOError):
            logs = []
    
    # Add new log entry
    log_entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "term": str(term),
        "status": str(status)
    }
    logs.append(log_entry)
    
    # Keep only last 500 entries
    if len(logs) > 500:
        logs = logs[-500:]
    
    # Write back to file
    try:
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(logs, f, indent=2)
    except IOError:
        pass  # Silently fail if we can't write logs


@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")


@app.route("/lookup", methods=["POST"])
def lookup():
    business_id = request.form.get("business_id")

    if not business_id:
        return render_template("index.html", error="Corporate number is required.")

    result = lookup_japan(business_id)

    if "error" in result:
        write_log(business_id, "error")
        return render_template("index.html", error=result["error"])

    write_log(business_id, "ok")
    # Add timestamp for UI display
    result["timestamp"] = datetime.utcnow().isoformat() + "Z"

    pdf_url = f"/download/pdf/{business_id}"

    return render_template("index.html", result=result, pdf_url=pdf_url)


@app.route("/download/pdf/<business_id>", methods=["GET"])
def download_pdf(business_id):
    result = lookup_japan(business_id)

    if "error" in result:
        return f"Cannot generate PDF: {result['error']}", 404

    pdf_bytes = generate_pdf(result)

    return send_file(
        io.BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"{business_id}.pdf"
    )


@app.route("/bulk", methods=["GET"])
def bulk():
    return render_template("bulk.html")


@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    file = request.files.get("file")

    if not file:
        return render_template("bulk.html", error="CSV file is required.")

    file_bytes = file.read()
    results = process_csv(file_bytes)

    if not results:
        return render_template("bulk.html", error="No valid IDs found in CSV.")

    # Lookup each ID
    full_results = []
    for item in results:
        business_id = item.get("business_id") or ""
        result = lookup_japan(business_id)
        result["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Log each lookup attempt
        if "error" in result:
            write_log(business_id or "unknown", "error")
        else:
            write_log(business_id or "unknown", "ok")
        
        full_results.append(result)

    # Cache results for ZIP download
    CACHE["bulk_results"] = full_results

    zip_url = "/download/zip"
    csv_url = "/download/results.csv"

    return render_template("bulk.html", results=full_results, zip_url=zip_url, csv_url=csv_url)


@app.route("/download/zip", methods=["GET"])
def download_zip():
    results = CACHE.get("bulk_results", [])

    if not results:
        return "No results to download.", 400

    zip_bytes = generate_pdf_zip(results)

    return send_file(
        io.BytesIO(zip_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name="audos_lookup_results.zip"
    )


@app.route("/download/results.csv", methods=["GET"])
def download_results_csv():
    results = CACHE.get("bulk_results", [])

    if not results:
        return "No CSV available.", 400

    # Build CSV in memory
    buffer = io.StringIO()
    fieldnames = ["business_id", "company_name", "address", "error", "timestamp"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()

    for r in results:
        writer.writerow({
            "business_id": r.get("business_id", ""),
            "company_name": r.get("company_name", ""),
            "address": r.get("address", ""),
            "error": r.get("error", ""),
            "timestamp": r.get("timestamp", "")
        })

    csv_bytes = buffer.getvalue().encode("utf-8")

    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name="results.csv"
    )


@app.route("/logs", methods=["GET"])
def logs():
    """Display logs from logs.json."""
    log_file = "logs.json"
    logs = []
    
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                logs = json.load(f)
                if not isinstance(logs, list):
                    logs = []
        except (json.JSONDecodeError, IOError):
            logs = []
    
    # Reverse to show newest first
    logs.reverse()
    
    return render_template("logs.html", logs=logs)


@app.route("/lookup-single", methods=["POST"])
def lookup_single():
    """Single business lookup endpoint."""
    try:
        data = request.get_json(silent=True) or {}
        business_id = data.get("business_id", "").strip()
        
        # Validate ID format
        validation_error = validate_id_format(business_id)
        if validation_error:
            log_lookup("lookup_single", business_id, validation_error, "error")
            return jsonify(validation_error), 400
        
        # Perform lookup
        result = lookup_business(business_id)
        
        # Log the lookup
        status = "ok" if "error" not in result else "error"
        log_lookup("lookup_single", business_id, result, status)
        
        if "error" in result:
            return jsonify(result), 404
        
        return jsonify(result), 200
        
    except Exception as e:
        log_error(e, "lookup_single")
        return jsonify({"error": "internal_server_error"}), 500


@app.route("/lookup-bulk", methods=["POST"])
def lookup_bulk():
    """Bulk business lookup endpoint."""
    try:
        data = request.get_json(silent=True) or {}
        business_ids = data.get("business_ids", [])
        
        if not isinstance(business_ids, list):
            return jsonify({"error": "business_ids must be a list"}), 400
        
        results = []
        
        for business_id in business_ids:
            business_id = str(business_id).strip() if business_id else ""
            
            # Validate ID format
            validation_error = validate_id_format(business_id)
            if validation_error:
                results.append(validation_error)
                log_lookup("lookup_bulk", business_id, validation_error, "error")
                continue
            
            # Perform lookup
            result = lookup_business(business_id)
            
            # Log the lookup
            status = "ok" if "error" not in result else "error"
            log_lookup("lookup_bulk", business_id, result, status)
            
            results.append(result)
        
        return jsonify({"results": results}), 200
        
    except Exception as e:
        log_error(e, "lookup_bulk")
        return jsonify({"error": "internal_server_error"}), 500


@app.route("/lookup-csv", methods=["POST"])
def lookup_csv():
    """CSV upload and lookup endpoint."""
    try:
        file = request.files.get("file")
        
        if not file:
            return jsonify({"error": "file is required"}), 400
        
        file_bytes = file.read()
        
        if not file_bytes:
            return jsonify({"error": "file is empty"}), 400
        
        # Parse CSV
        buffer = io.BytesIO(file_bytes)
        try:
            df = pd.read_csv(buffer, dtype=str).fillna("")
        except Exception as e:
            log_error(e, "lookup_csv_parse")
            return jsonify({"error": "invalid_csv_format"}), 400
        
        # Find ID column
        id_column = None
        for candidate in ("business_id", "corporate_number"):
            if candidate in df.columns:
                id_column = candidate
                break
        
        if not id_column:
            return jsonify({"error": "csv_missing_id_column"}), 400
        
        results = []
        
        # Process each row
        for _, row in df.iterrows():
            business_id = (row.get(id_column) or "").strip()
            
            # Skip blank rows
            if not business_id:
                continue
            
            # Validate ID format
            validation_error = validate_id_format(business_id)
            if validation_error:
                results.append(validation_error)
                log_lookup("lookup_csv", business_id, validation_error, "error")
                continue
            
            # Perform lookup
            result = lookup_business(business_id)
            
            # Log the lookup
            status = "ok" if "error" not in result else "error"
            log_lookup("lookup_csv", business_id, result, status)
            
            results.append(result)
        
        return jsonify({"results": results}), 200
        
    except Exception as e:
        log_error(e, "lookup_csv")
        return jsonify({"error": "internal_server_error"}), 500


# Unified error handler
@app.errorhandler(Exception)
def handle_exception(e):
    """Catch all unhandled exceptions."""
    log_error(e, "unhandled_exception")
    return jsonify({"error": "internal_server_error"}), 500


if __name__ == "__main__":
    app.run(debug=True)

