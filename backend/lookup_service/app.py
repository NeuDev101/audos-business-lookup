import io
import csv
import json
import logging
import os
import sys
import tempfile
import shutil
import traceback
import uuid
import zipfile
from datetime import datetime
import time
from functools import wraps
from flask import Flask, render_template, request, send_file, jsonify
import pandas as pd

# Ensure local packages (e.g., pdf.proof) are importable when run from repo root
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from audit_store import (
    get_run_metadata,
    get_run_results,
    init_db,
    record_result,
    start_run,
)
from lookup.csv_handler import process_csv
from lookup.japan import lookup_japan
from pdf.proof import generate_pdf, generate_pdf_zip
from invoice_parser import parse_invoice_from_multipart, InvoiceParseError

# Get the directory where app.py is located
# Default to auth disabled for the MVP/guest experience unless explicitly overridden
os.environ.setdefault("DISABLE_AUTH", "1")
os.environ.setdefault("SECRET_KEY", "dev-secret-key")
AUTH_DISABLED = os.getenv("DISABLE_AUTH", "").lower() in ("1", "true", "yes")
# Ruleset version recorded on each run for audit defensibility
RULESET_VERSION = "v1.0"

# Production configuration
class Config:
    """Production-ready configuration from environment variables."""
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-key"
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is required")
    
    FLASK_ENV = os.getenv("FLASK_ENV", "production")
    DEBUG = os.getenv("DEBUG", "False").lower() in ("true", "1", "yes")
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "5000"))
    
    # CORS configuration
    ALLOWED_ORIGINS = [
        origin.strip()
        for origin in os.getenv("ALLOWED_ORIGINS", "").split(",")
        if origin.strip()
    ]
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    
    # Feature flags
    LOGS_ROUTE_ENABLED = os.getenv("LOGS_ROUTE_ENABLED", "false").lower() == "true"

# Configure logging
log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = Config.SECRET_KEY
# Ensure audit store is ready for run logging
init_db()

# React build directory (for production serving)
# From backend/lookup_service/app.py, go up two levels to repo root, then into react-business-lookup/dist
REACT_BUILD_DIR = os.path.abspath(os.path.join(APP_DIR, "..", "..", "react-business-lookup", "dist"))
AUDOS_CONSOLE_DIR = os.path.abspath(os.path.join(APP_DIR, "..", "audos_console"))

run_batch = None
BATCH_RUNNER_IMPORT_ERROR = None
MANUAL_VALIDATOR = None
VALIDATOR_IMPORT_ERROR = None
INVOICE_PDF_GENERATOR = None
PDF_GENERATOR_IMPORT_ERROR = None

if os.path.isdir(AUDOS_CONSOLE_DIR):
    if AUDOS_CONSOLE_DIR not in sys.path:
        sys.path.append(AUDOS_CONSOLE_DIR)
    try:
        from shared import batch_runner as shared_batch_runner  # type: ignore

        run_batch = shared_batch_runner.run_batch  # type: ignore[attr-defined]
    except Exception as import_exc:  # pragma: no cover - logging only
        BATCH_RUNNER_IMPORT_ERROR = str(import_exc)
    
    # Import validator for manual invoice validation
    try:
        from validator.validator import InvoiceValidator  # type: ignore
        
        MANUAL_VALIDATOR = InvoiceValidator()  # type: ignore[call-arg]
    except Exception as import_exc:  # pragma: no cover - logging only
        VALIDATOR_IMPORT_ERROR = str(import_exc)
    
    # Import invoice PDF generator
    try:
        from pdf_generator.pdf.pdf_generator import generate_invoice_pdf  # type: ignore
        
        INVOICE_PDF_GENERATOR = generate_invoice_pdf  # type: ignore[assignment]
    except Exception as import_exc:  # pragma: no cover - logging only
        PDF_GENERATOR_IMPORT_ERROR = str(import_exc)
    
    # Import auth modules
    try:
        from shared.auth_middleware import require_auth, optional_auth  # type: ignore
        from db.auth_models import (  # type: ignore
            create_user, get_user_by_email, get_user_by_id, verify_password,
            create_access_token, create_refresh_token, verify_token
        )
        from db.models import InvoiceResult  # type: ignore
        from db.db import get_session  # type: ignore
        AUTH_AVAILABLE = True
    except Exception as import_exc:  # pragma: no cover - logging only
        AUTH_AVAILABLE = False
        AUTH_IMPORT_ERROR = str(import_exc)
else:  # pragma: no cover - logging only
    BATCH_RUNNER_IMPORT_ERROR = f"Missing audos_console directory at {AUDOS_CONSOLE_DIR}"
    VALIDATOR_IMPORT_ERROR = f"Missing audos_console directory at {AUDOS_CONSOLE_DIR}"
    PDF_GENERATOR_IMPORT_ERROR = f"Missing audos_console directory at {AUDOS_CONSOLE_DIR}"
    AUTH_AVAILABLE = False
    AUTH_IMPORT_ERROR = f"Missing audos_console directory at {AUDOS_CONSOLE_DIR}"


def _guest_auth_decorator(f):
    """No-op auth decorator used when auth is disabled/unavailable."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        # Keep downstream code happy with a placeholder user
        request.current_user_id = 0
        request.current_user_email = "guest@audos.local"
        return f(*args, **kwargs)
    return wrapper


# When auth is disabled or unavailable, fall back to guest/no-op decorators
if AUTH_DISABLED or not AUTH_AVAILABLE:
    require_auth = _guest_auth_decorator  # type: ignore
    optional_auth = _guest_auth_decorator  # type: ignore

ALLOWED_INVOICE_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg"}
MAX_FILES_PER_REQUEST = 50
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_CSV_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_CSV_ROWS = 5000

# CORS configuration - allow origins from ALLOWED_ORIGINS, or use sensible defaults for dev
@app.after_request
def after_request(response):
    origin = request.headers.get('Origin', '')
    
    # Default allowed origins for development (when ALLOWED_ORIGINS is empty)
    default_origins = ['http://localhost:5173']
    
    # Use configured origins if available, otherwise use defaults
    allowed_origins = Config.ALLOWED_ORIGINS if Config.ALLOWED_ORIGINS else default_origins
    
    # Set CORS headers if origin is in allowed list
    if origin and origin in allowed_origins:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    # If no Origin header, it's a same-origin request (allowed by default)
    
    return response

@app.route("/lookup-single", methods=["OPTIONS"])
@app.route("/lookup-bulk", methods=["OPTIONS"])
@app.route("/lookup-csv", methods=["OPTIONS"])
@app.route("/validate_field", methods=["OPTIONS"])
@app.route("/manual-invoice/validate", methods=["OPTIONS"])
@app.route("/manual-invoice/generate", methods=["OPTIONS"])
@app.route("/api/auth/login", methods=["OPTIONS"])
@app.route("/api/auth/register", methods=["OPTIONS"])
@app.route("/api/auth/refresh", methods=["OPTIONS"])
def handle_options():
    """Handle CORS preflight requests."""
    origin = request.headers.get('Origin', '')
    default_origins = ['http://localhost:5173']
    allowed_origins = Config.ALLOWED_ORIGINS if Config.ALLOWED_ORIGINS else default_origins
    
    response = jsonify({})
    if origin in allowed_origins or (not Config.ALLOWED_ORIGINS and origin in default_origins):
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        response.headers['Access-Control-Allow-Credentials'] = 'true'
    return response, 200

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


def lookup_business(business_id: str, max_retries: int = 2, retry_delay: float = 0.5) -> dict:
    """Lookup business and return normalized result dict with basic retries for reliability."""
    last_exc = None
    for attempt in range(max_retries + 1):
        timestamp = datetime.utcnow().isoformat() + "Z"
        try:
            result = lookup_japan(business_id)
            # Keep API-provided errors as-is (don't retry on logical errors)
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
        except Exception as exc:
            last_exc = exc
            if attempt < max_retries:
                time.sleep(retry_delay)
                continue
            return {
                "business_id": business_id,
                "error": f"Lookup failed: {str(exc)}",
                "timestamp": timestamp
            }


def log_lookup(event: str, input_data: str, output: dict, status: str):
    """Log lookup event to file-based log."""
    try:
        log_dir = os.path.join(APP_DIR, "logs", "lookups")
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
        log_dir = os.path.join(APP_DIR, "logs", "errors")
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
    log_file = os.path.join(APP_DIR, "logs.json")
    
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


@app.route("/single", methods=["GET"])
def single():
    if Config.DEBUG:
        print("=" * 80)
        print("!!! DEBUG: GET /single ROUTE EXECUTED - RENDERING index.html (SINGLE LOOKUP v2) !!!")
        print("=" * 80)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("=" * 80)
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
    if Config.DEBUG:
        print("=" * 80)
        print("!!! DEBUG: GET /bulk ROUTE EXECUTED - RENDERING bulk.html (BULK LOOKUP v2) !!!")
        print("=" * 80)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("=" * 80)
    # In production, if React build exists, serve React instead
    react_index = os.path.join(REACT_BUILD_DIR, "index.html")
    if os.path.exists(react_index):
        return send_file(react_index)
    return render_template("bulk.html")


@app.route("/upload-csv", methods=["POST"])
def upload_csv():
    file = request.files.get("file")

    if not file:
        return render_template("bulk.html", error="CSV file is required.")

    # Validate filename extension
    filename = file.filename or ""
    if not filename.lower().endswith(".csv"):
        return render_template("bulk.html", error="Only CSV files are allowed.")

    # Validate mimetype
    mimetype = file.content_type or ""
    if mimetype and not any(mt in mimetype.lower() for mt in ["text/csv", "application/csv", "text/plain"]):
        return render_template("bulk.html", error="Invalid file type. Only CSV files are allowed.")

    # Read and validate file size
    file_bytes = file.read()
    if len(file_bytes) > MAX_CSV_SIZE_BYTES:
        return render_template("bulk.html", error=f"File size exceeds {MAX_CSV_SIZE_BYTES / (1024 * 1024)}MB limit.")

    if not file_bytes:
        return render_template("bulk.html", error="CSV file is empty.")

    # Parse CSV
    buffer = io.BytesIO(file_bytes)
    try:
        df = pd.read_csv(buffer, dtype=str).fillna("")
    except Exception as e:
        log_error(e, "upload_csv_parse")
        return render_template("bulk.html", error="Invalid CSV format.")

    # Check row count
    if len(df) > MAX_CSV_ROWS:
        return render_template("bulk.html", error=f"CSV contains {len(df)} rows. Maximum {MAX_CSV_ROWS} rows allowed.")

    # Find ID column
    id_column = None
    for candidate in ("business_id", "corporate_number"):
        if candidate in df.columns:
            id_column = candidate
            break

    if not id_column:
        return render_template("bulk.html", error="CSV must include a 'business_id' or 'corporate_number' column.")

    # Process and validate IDs
    valid_ids = []
    validation_errors = []

    for idx, row in df.iterrows():
        business_id = (row.get(id_column) or "").strip()
        
        # Skip completely blank rows
        if not business_id:
            continue

        # Validate ID format
        validation_error = validate_id_format(business_id)
        if validation_error:
            validation_errors.append({
                "row": idx + 2,  # +2 because of header and 0-indexing
                "business_id": business_id,
                "error": validation_error.get("error", "Invalid format")
            })
        else:
            valid_ids.append(business_id)

    if not valid_ids:
        error_msg = "No valid IDs found in CSV."
        if validation_errors:
            error_msg += f" Found {len(validation_errors)} invalid ID(s)."
        return render_template("bulk.html", error=error_msg, errors=validation_errors)

    # Lookup each valid ID
    full_results = []
    for business_id in valid_ids:
        result = lookup_japan(business_id)
        result["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        # Log each lookup attempt
        if "error" in result:
            write_log(business_id, "error")
        else:
            write_log(business_id, "ok")
        
        full_results.append(result)

    # Cache results for ZIP download
    CACHE["bulk_results"] = full_results

    zip_url = "/download/zip"
    csv_url = "/download/results.csv"

    return render_template("bulk.html", results=full_results, zip_url=zip_url, csv_url=csv_url, errors=validation_errors if validation_errors else None)


@app.route("/download/zip", methods=["GET"])
def download_zip():
    results = CACHE.get("bulk_results", [])

    if not results:
        return "No results available.", 404

    zip_bytes = generate_pdf_zip(results)

    return send_file(
        io.BytesIO(zip_bytes),
        mimetype="application/zip",
        as_attachment=True,
        download_name="audos_lookup_results.zip"
    )


@app.route("/download/results.csv", methods=["GET"])
def download_results_csv():
    run_id = request.args.get("run_id") or CACHE.get("last_run_id")
    meta = {}
    if run_id:
        results = get_run_results(run_id)
        meta = get_run_metadata(run_id) or {}
    else:
        results = CACHE.get("bulk_results", [])

    if not results:
        return "No results available.", 404

    # Build CSV in memory
    buffer = io.StringIO()
    fieldnames = ["business_id", "company_name", "address", "error", "timestamp"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()

    for r in results:
        writer.writerow({
            "business_id": r.get("business_id", ""),
            "company_name": r.get("company_name", r.get("name", "")),
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


@app.route("/export-run/<run_id>", methods=["GET"])
def export_run(run_id):
    """Export a specific run's results as CSV using persisted audit records."""
    rows = get_run_results(run_id)
    if not rows:
        return jsonify({"error": "run_not_found"}), 404
    
    meta = get_run_metadata(run_id) or {}
    buffer = io.StringIO()
    fieldnames = ["business_id", "name", "address", "registration_status", "error", "timestamp", "ruleset_version"]
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    
    for r in rows:
        writer.writerow({
            "business_id": r.get("business_id", ""),
            "name": r.get("name", r.get("company_name", "")),
            "address": r.get("address", ""),
            "registration_status": r.get("registration_status", ""),
            "error": r.get("error", ""),
            "timestamp": r.get("timestamp", ""),
            "ruleset_version": meta.get("ruleset_version", RULESET_VERSION),
        })
    
    csv_bytes = buffer.getvalue().encode("utf-8")
    filename = f"run_{run_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.csv"
    
    return send_file(
        io.BytesIO(csv_bytes),
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/logs", methods=["GET"])
def logs():
    """Display logs from logs.json. Disabled in production unless LOGS_ROUTE_ENABLED=true."""
    if not Config.LOGS_ROUTE_ENABLED:
        return "Not found", 404
    
    log_file = os.path.join(APP_DIR, "logs.json")
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
    if Config.DEBUG:
        print("=" * 80)
        print("DEBUG: /lookup-single HIT")
        print("DEBUG: request.method =", request.method)
        print("DEBUG: request.headers =", dict(request.headers))
        print("DEBUG: request.args =", dict(request.args))
        print("DEBUG: request.form =", dict(request.form))
    try:
        json_data = request.get_json(silent=True)
        if Config.DEBUG:
            print("DEBUG: request.get_json() =", json_data)
    except Exception as e:
        if Config.DEBUG:
            print("DEBUG: request.get_json() raised:", e)
        json_data = None
    if Config.DEBUG:
        print("=" * 80)
    
    try:
        data = json_data or {}
        business_id = data.get("business_id", "").strip()
        if Config.DEBUG:
            print(f"DEBUG: Extracted business_id = '{business_id}'")
        
        # Validate ID format
        validation_error = validate_id_format(business_id)
        if validation_error:
            log_lookup("lookup_single", business_id, validation_error, "error")
            return jsonify(validation_error), 400
        
        run_id = str(uuid.uuid4())
        user = getattr(request, "current_user_email", "guest@audos.local") or "guest@audos.local"
        start_run(run_id, user=user, count=1, ruleset_version=RULESET_VERSION, source="lookup_single")
        
        # Perform lookup with retry
        result = lookup_business(business_id)
        record_result(run_id, result)
        
        # Log the lookup
        status = "ok" if "error" not in result else "error"
        log_lookup("lookup_single", business_id, result, status)
        
        response_body = {"run_id": run_id, "ruleset_version": RULESET_VERSION, **result}
        if "error" in result:
            return jsonify(response_body), 404
        
        return jsonify(response_body), 200
        
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
        
        run_id = str(uuid.uuid4())
        user = getattr(request, "current_user_email", "guest@audos.local") or "guest@audos.local"
        start_run(run_id, user=user, count=len(business_ids), ruleset_version=RULESET_VERSION, source="lookup_bulk")
        CACHE["last_run_id"] = run_id

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
            record_result(run_id, result)
            
            # Log the lookup
            status = "ok" if "error" not in result else "error"
            log_lookup("lookup_bulk", business_id, result, status)
            
            results.append(result)
        
        return jsonify({"run_id": run_id, "ruleset_version": RULESET_VERSION, "results": results}), 200
        
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
        
        # Validate filename extension
        filename = file.filename or ""
        if not filename.lower().endswith(".csv"):
            return jsonify({"error": "Only CSV files are allowed"}), 400
        
        # Validate mimetype
        mimetype = file.content_type or ""
        if mimetype and not any(mt in mimetype.lower() for mt in ["text/csv", "application/csv", "text/plain"]):
            return jsonify({"error": "Invalid file type. Only CSV files are allowed"}), 400
        
        file_bytes = file.read()
        
        # Validate file size
        if len(file_bytes) > MAX_CSV_SIZE_BYTES:
            return jsonify({"error": f"File size exceeds {MAX_CSV_SIZE_BYTES / (1024 * 1024)}MB limit"}), 400
        
        if not file_bytes:
            return jsonify({"error": "file is empty"}), 400
        
        # Parse CSV
        buffer = io.BytesIO(file_bytes)
        try:
            df = pd.read_csv(buffer, dtype=str).fillna("")
        except Exception as e:
            log_error(e, "lookup_csv_parse")
            return jsonify({"error": "invalid_csv_format"}), 400
        
        # Check row count
        if len(df) > MAX_CSV_ROWS:
            return jsonify({"error": f"CSV contains {len(df)} rows. Maximum {MAX_CSV_ROWS} rows allowed"}), 400
        
        # Find ID column
        id_column = None
        for candidate in ("business_id", "corporate_number"):
            if candidate in df.columns:
                id_column = candidate
                break
        
        if not id_column:
            return jsonify({"error": "csv_missing_id_column"}), 400
        
        # Process and validate IDs
        validation_errors = []
        valid_ids = []
        invalid_results = []
        
        for idx, row in df.iterrows():
            business_id = (row.get(id_column) or "").strip()
            
            # Skip completely blank rows
            if not business_id:
                continue
            
            # Validate ID format
            validation_error = validate_id_format(business_id)
            if validation_error:
                error_entry = {
                    "business_id": business_id,
                    "error": validation_error.get("error", "Invalid format"),
                    "row": idx + 2,  # +2 because of header and 0-indexing
                }
                validation_errors.append(error_entry)
                invalid_results.append(validation_error)
                continue
            
            valid_ids.append(business_id)
        
        # Check if any valid IDs were processed
        if not valid_ids:
            return jsonify({
                "error": "No valid IDs found",
                "errors": validation_errors
            }), 400
        
        run_id = str(uuid.uuid4())
        user = getattr(request, "current_user_email", "guest@audos.local") or "guest@audos.local"
        start_run(run_id, user=user, count=len(valid_ids) + len(invalid_results), ruleset_version=RULESET_VERSION, source="lookup_csv")
        CACHE["last_run_id"] = run_id
        
        results = []
        
        # Record invalid rows in audit with timestamps
        for invalid in invalid_results:
            if "timestamp" not in invalid:
                invalid["timestamp"] = datetime.utcnow().isoformat() + "Z"
            record_result(run_id, invalid)
            log_lookup("lookup_csv", invalid.get("business_id", ""), invalid, "error")
            results.append(invalid)
        
        for business_id in valid_ids:
            result = lookup_business(business_id)
            record_result(run_id, result)
            
            # Log the lookup
            status = "ok" if "error" not in result else "error"
            log_lookup("lookup_csv", business_id, result, status)
            
            results.append(result)
        
        # Cache results for ZIP/CSV download
        CACHE["bulk_results"] = results
        
        response_body = {"run_id": run_id, "ruleset_version": RULESET_VERSION, "results": results}
        if validation_errors:
            response_body["errors"] = validation_errors
        
        return jsonify(response_body), 200
        
    except Exception as e:
        log_error(e, "lookup_csv")
        return jsonify({"error": "internal_server_error"}), 500


# Unified error handler
@app.errorhandler(Exception)
def handle_exception(e):
    """Catch all unhandled exceptions."""
    log_error(e, "unhandled_exception")
    return jsonify({"error": "internal_server_error"}), 500


# Production: Serve React build (only if build exists and route is not an API route)
@app.route("/", defaults={"path": ""}, methods=["GET"])
@app.route("/<path:path>", methods=["GET"])
def serve_react_app(path):
    """Serve the React build when available, otherwise fall back to Flask templates."""
    # Let API routes continue to the Flask handlers above
    if path.startswith(("lookup-", "download/", "logs")):
        return "Not found", 404
    
    index_path = os.path.join(REACT_BUILD_DIR, "index.html")
    build_exists = os.path.exists(REACT_BUILD_DIR)
    
    # Serve built static assets when the React build exists
    if build_exists and path and not path.endswith("/"):
        file_path = os.path.join(REACT_BUILD_DIR, path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return send_file(file_path)
    
    if build_exists and os.path.exists(index_path):
        return send_file(index_path)
    
    # Fallback to server-rendered templates when the React build is missing
    if path in ("", "single"):
        return render_template("index.html")
    if path == "bulk":
        return render_template("bulk.html")
    
    return "React build not found. Run 'cd react-business-lookup && npm run build'", 404


# ===============================
# Authentication Endpoints
# ===============================

@app.route("/api/auth/register", methods=["POST"])
def register():
    """Register a new user."""
    if AUTH_DISABLED:
        demo_user = {
            "id": 0,
            "email": "demo@audos.local",
            "username": "demo",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        return jsonify({
            "user": demo_user,
            "access_token": "demo-access-token",
            "refresh_token": "demo-refresh-token",
        }), 200
    if not AUTH_AVAILABLE:
        return jsonify({"error": "Authentication service unavailable"}), 503
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body is required"}), 400
        
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        username = data.get("username", "").strip() or None
        
        if not email:
            return jsonify({"error": "email is required"}), 400
        if not password or len(password) < 8:
            return jsonify({"error": "password must be at least 8 characters"}), 400
        
        # Check if user already exists
        existing = get_user_by_email(email)
        if existing:
            return jsonify({"error": "Email already registered"}), 409
        
        # Create user
        user = create_user(email=email, password=password, username=username)
        
        # Generate tokens
        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id, user.email)
        
        return jsonify({
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }), 201
    
    except Exception as e:
        log_error(e, "register")
        return jsonify({"error": "Registration failed"}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    """Login and get access/refresh tokens."""
    if AUTH_DISABLED:
        demo_user = {
            "id": 0,
            "email": "demo@audos.local",
            "username": "demo",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        return jsonify({
            "user": demo_user,
            "access_token": "demo-access-token",
            "refresh_token": "demo-refresh-token",
        }), 200
    if not AUTH_AVAILABLE:
        return jsonify({"error": "Authentication service unavailable"}), 503
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body is required"}), 400
        
        email = data.get("email", "").strip()
        password = data.get("password", "").strip()
        
        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400
        
        # Get user
        user = get_user_by_email(email)
        if not user:
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Verify password
        if not verify_password(password, user.password_hash):
            return jsonify({"error": "Invalid email or password"}), 401
        
        # Generate tokens
        access_token = create_access_token(user.id, user.email)
        refresh_token = create_refresh_token(user.id, user.email)
        
        return jsonify({
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
        }), 200
    
    except Exception as e:
        log_error(e, "login")
        return jsonify({"error": "Login failed"}), 500


@app.route("/api/auth/refresh", methods=["POST"])
def refresh_token():
    """Refresh access token using refresh token."""
    if AUTH_DISABLED:
        return jsonify({"access_token": "demo-access-token"}), 200
    if not AUTH_AVAILABLE:
        return jsonify({"error": "Authentication service unavailable"}), 503
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body is required"}), 400
        
        refresh_token_str = data.get("refresh_token", "").strip()
        if not refresh_token_str:
            return jsonify({"error": "refresh_token is required"}), 400
        
        # Verify refresh token
        payload = verify_token(refresh_token_str, token_type="refresh")
        if not payload:
            return jsonify({"error": "Invalid or expired refresh token"}), 401
        
        user_id = payload.get("user_id")
        email = payload.get("email")
        
        # Verify user still exists
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({"error": "User not found"}), 401
        
        # Generate new access token
        access_token = create_access_token(user.id, user.email)
        
        return jsonify({
            "access_token": access_token,
        }), 200
    
    except Exception as e:
        log_error(e, "refresh_token")
        return jsonify({"error": "Token refresh failed"}), 500


# ===============================
# History API Endpoints
# ===============================

@app.route("/api/history", methods=["GET"])
@require_auth
def get_history():
    """Get invoice history for the authenticated user."""
    if not AUTH_AVAILABLE:
        return jsonify({"error": "History service unavailable"}), 503
    
    try:
        user_id = request.current_user_id
        
        # Parse query parameters
        status = request.args.get("status")  # "pass" or "fail"
        batch_id = request.args.get("batch_id")
        invoice_number = request.args.get("invoice_number")
        start_date = request.args.get("start_date")
        end_date = request.args.get("end_date")
        page = int(request.args.get("page", 1))
        per_page = min(int(request.args.get("per_page", 50)), 100)  # Max 100 per page
        
        session = get_session()
        try:
            # Build query
            query = session.query(InvoiceResult).filter_by(user_id=user_id)
            
            if status:
                query = query.filter_by(status=status)
            if batch_id:
                query = query.filter_by(batch_id=batch_id)
            if invoice_number:
                query = query.filter(InvoiceResult.invoice_number.like(f"%{invoice_number}%"))
            if start_date:
                try:
                    start_dt = datetime.fromisoformat(start_date)
                    query = query.filter(InvoiceResult.created_at >= start_dt)
                except ValueError:
                    pass
            if end_date:
                try:
                    end_dt = datetime.fromisoformat(end_date)
                    query = query.filter(InvoiceResult.created_at <= end_dt)
                except ValueError:
                    pass
            
            # Get total count
            total = query.count()
            
            # Apply pagination
            offset = (page - 1) * per_page
            invoices = query.order_by(InvoiceResult.created_at.desc()).offset(offset).limit(per_page).all()
            
            return jsonify({
                "invoices": [inv.to_dict() for inv in invoices],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page,
                },
            }), 200
        finally:
            session.close()
    
    except Exception as e:
        log_error(e, "get_history")
        return jsonify({"error": "Failed to fetch history"}), 500


@app.route("/api/history/<int:invoice_id>", methods=["GET"])
@require_auth
def get_history_detail(invoice_id):
    """Get a specific invoice detail."""
    if not AUTH_AVAILABLE:
        return jsonify({"error": "History service unavailable"}), 503
    
    try:
        user_id = request.current_user_id
        
        session = get_session()
        try:
            invoice = session.query(InvoiceResult).filter_by(id=invoice_id, user_id=user_id).first()
            
            if not invoice:
                return jsonify({"error": "Invoice not found"}), 404
            
            return jsonify(invoice.to_dict()), 200
        finally:
            session.close()
    
    except Exception as e:
        log_error(e, "get_history_detail")
        return jsonify({"error": "Failed to fetch invoice detail"}), 500


# ===============================
# Invoice Validation Endpoints
# ===============================

@app.route("/validate-invoices", methods=["POST"])
@require_auth
def validate_invoices():
    """Handle invoice validation batches uploaded from the console UI."""
    # User is authenticated via @require_auth decorator
    user_id = request.current_user_id
    
    # Service availability check
    if run_batch is None:
        message = "Invoice validation service is unavailable"
        if BATCH_RUNNER_IMPORT_ERROR:
            message += f": {BATCH_RUNNER_IMPORT_ERROR}"
        return jsonify({"error": message}), 503

    uploaded_files = request.files.getlist("files")
    if not uploaded_files:
        return jsonify({"error": "At least one file is required"}), 400

    # Enforce max files limit
    if len(uploaded_files) > MAX_FILES_PER_REQUEST:
        return jsonify({
            "error": f"Too many files. Maximum {MAX_FILES_PER_REQUEST} files per request."
        }), 400

    # Read language from form data (default 'en')
    language = request.form.get("language", "en")
    if language not in ("en", "ja"):
        language = "en"

    # Get metadata from form data (can be single object, array, or empty)
    metadata_list = request.form.getlist("metadata")
    # If no metadata provided, create minimal defaults per file
    if len(metadata_list) == 0:
        metadata_list = [None] * len(uploaded_files)
    # If single metadata provided, reuse for all files
    elif len(metadata_list) == 1 and len(uploaded_files) > 1:
        metadata_list = metadata_list * len(uploaded_files)
    # If metadata count doesn't match file count and it's not a single metadata, error
    elif len(metadata_list) != len(uploaded_files):
        return jsonify({
            "error": f"Metadata count ({len(metadata_list)}) must match file count ({len(uploaded_files)}). Provide one metadata for all files, one per file, or none (defaults will be used)."
        }), 400

    # Create temporary directory for uploaded files
    temp_dir = None
    temp_file_paths = []
    invoices = []
    rejected_files = []
    
    try:
        temp_dir = tempfile.mkdtemp(prefix="validate_invoices_")
        
        for idx, storage in enumerate(uploaded_files):
            # Check for missing filename
            if not storage or not storage.filename:
                rejected_files.append(f"File {idx + 1} (missing filename)")
                continue
            
            # Check file extension
            extension = os.path.splitext(storage.filename)[1].lower()
            if extension not in ALLOWED_INVOICE_EXTENSIONS:
                rejected_files.append(f"{storage.filename} (unsupported extension: {extension})")
                continue
            
            # Read file content and close stream
            try:
                storage.seek(0)
                file_content = storage.read()
            finally:
                # Close the uploaded file stream to avoid ResourceWarning
                if hasattr(storage, 'close'):
                    try:
                        storage.close()
                    except Exception:
                        pass
            
            # Check file size
            file_size = len(file_content)
            if file_size == 0:
                rejected_files.append(f"{storage.filename} (empty file)")
                continue
            
            if file_size > MAX_FILE_SIZE_BYTES:
                rejected_files.append(f"{storage.filename} (file too large: {file_size} bytes, max {MAX_FILE_SIZE_BYTES} bytes)")
                continue
            
            # Save file to temp directory
            safe_filename = os.path.basename(storage.filename)
            temp_file_path = os.path.join(temp_dir, safe_filename)
            with open(temp_file_path, "wb") as f:
                f.write(file_content)
            temp_file_paths.append(temp_file_path)
            
            # Get metadata for this file (may be None)
            json_metadata = metadata_list[idx] if idx < len(metadata_list) else None
            
            # If metadata is missing, create minimal defaults
            if not json_metadata:
                json_metadata = json.dumps({
                    "invoice_number": os.path.splitext(safe_filename)[0],
                    "issuer_name": "N/A",
                    "issuer_id": "",
                    "buyer": "N/A",
                    "date": datetime.utcnow().date().isoformat(),
                    "items": [
                        {
                            "description": "Item",
                            "amount_excl_tax": 0,
                            "tax_rate": "10%",
                        }
                    ]
                })
            
            # Parse invoice from JSON metadata
            try:
                invoice = parse_invoice_from_multipart(temp_file_path, file_content, json_metadata)
                # Ensure source_filename and extension are set for batch processing
                invoice["source_filename"] = temp_file_path
                invoice["source_extension"] = extension
                # Attach language for downstream processing
                invoice["language"] = language
                invoices.append(invoice)
            except InvoiceParseError as parse_exc:
                # If parsing fails due to missing/invalid data, reject with 400
                log_error(parse_exc, f"parse_invoice_{safe_filename}")
                rejected_files.append(f"{safe_filename}: {str(parse_exc)}")
                continue
            except Exception as parse_exc:
                # Other parsing errors
                log_error(parse_exc, f"parse_invoice_{safe_filename}")
                rejected_files.append(f"{safe_filename} (parsing failed: {str(parse_exc)[:50]})")
                continue

        if not invoices:
            message = "No valid files were provided."
            if rejected_files:
                message += f" Rejected: {', '.join(rejected_files[:5])}"
                if len(rejected_files) > 5:
                    message += f" (and {len(rejected_files) - 5} more)"
            return jsonify({"error": message}), 400

        # Run batch validation
        try:
            summary = run_batch(invoices, user_id=user_id, language=language)
        except Exception as exc:
            log_error(exc, "validate_invoices")
            return jsonify({"error": "invoice_validation_failed"}), 500

        # Collect generated PDFs from run_batch results
        # run_batch already generates PDFs and saves them to disk
        generated_pdfs = {}
        invoice_metadata = {}
        
        for inv_result in summary.get("invoices", []):
            invoice_number = inv_result.get("invoice_number", "")
            if not invoice_number:
                continue
            
            # Store metadata for response
            invoice_metadata[invoice_number] = {
                "invoice_number": invoice_number,
                "status": inv_result.get("status", "unknown"),
                "compliant": inv_result.get("compliant", False),
                "issues": inv_result.get("issues", 0),
            }
            
            # Read PDF if path is available - guard against missing/nonexistent files
            pdf_path = inv_result.get("pdf_path")
            if pdf_path:
                try:
                    if os.path.exists(pdf_path):
                        with open(pdf_path, "rb") as f:
                            generated_pdfs[invoice_number] = f.read()
                except Exception as read_exc:
                    # Log but don't fail - skip missing PDFs gracefully
                    log_error(read_exc, f"validate_invoices_read_pdf_{invoice_number}")
        
        # If INVOICE_PDF_GENERATOR is available and we want to regenerate PDFs,
        # we could do that here, but run_batch already generates them using the same generator

        # Handle response based on number of files
        if len(invoices) == 1:
            # Single file: return JSON with validation summary and PDF file download
            invoice_number = list(invoice_metadata.keys())[0] if invoice_metadata else "unknown"
            
            # Build JSON response with validation summary
            response_body = {
                "batch_id": summary.get("batch_id"),
                "counts": summary.get("counts", {}),
                "invoices": summary.get("invoices", []),
            }
            if summary.get("ruleset_version"):
                response_body["ruleset_version"] = summary["ruleset_version"]
            
            # If PDF was generated and available, return it as file download
            # Otherwise, always return JSON 200 (robust handling for missing PDFs)
            if generated_pdfs and invoice_number in generated_pdfs:
                try:
                    pdf_bytes = generated_pdfs[invoice_number]
                    if pdf_bytes:
                        # Return PDF file - Flask send_file handles the download
                        return send_file(
                            io.BytesIO(pdf_bytes),
                            mimetype="application/pdf",
                            as_attachment=True,
                            download_name=f"invoice_{invoice_number}.pdf"
                        )
                except Exception as pdf_exc:
                    # If PDF response building fails, fall back to JSON
                    log_error(pdf_exc, f"validate_invoices_pdf_response_{invoice_number}")
            
            # No PDF available or PDF response failed - return JSON 200
            return jsonify(response_body), 200
        else:
            # Multiple files: return zip with PDFs and JSON summary
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                # Add generated PDFs to zip
                for invoice_number, pdf_bytes in generated_pdfs.items():
                    zip_file.writestr(f"invoice_{invoice_number}.pdf", pdf_bytes)
                
                # Add JSON summary with validation results
                summary_json = json.dumps({
                    "batch_id": summary.get("batch_id"),
                    "counts": summary.get("counts", {}),
                    "invoices": summary.get("invoices", []),
                    "ruleset_version": summary.get("ruleset_version"),
                }, indent=2, ensure_ascii=False)
                zip_file.writestr("validation_summary.json", summary_json.encode("utf-8"))
            
            zip_buffer.seek(0)
            
            # Return zip file
            return send_file(
                zip_buffer,
                mimetype="application/zip",
                as_attachment=True,
                download_name=f"invoices_batch_{summary.get('batch_id', 'unknown')}.zip"
            ), 200

    except Exception as exc:
        log_error(exc, "validate_invoices")
        return jsonify({"error": "invoice_validation_failed"}), 500
    
    finally:
        # Clean up temporary files and directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as cleanup_exc:
                log_error(cleanup_exc, "validate_invoices_cleanup")


@app.route("/validate_field", methods=["POST"])
def validate_field():
    """Validate a single field using the existing validator rules."""
    if MANUAL_VALIDATOR is None:
        return jsonify({"error": "Validation service unavailable"}), 503
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body required"}), 400
        
        field_name = data.get("field")
        field_value = data.get("value")
        
        if field_name is None:
            return jsonify({"error": "field is required"}), 400
        
        # Use the existing validator's validate_field_only method
        result = MANUAL_VALIDATOR.validate_field_only(field_name, field_value)
        return jsonify(result), 200
        
    except Exception as e:
        log_error(e, "validate_field")
        return jsonify({"error": "Validation failed"}), 500


@app.route("/manual-invoice/validate", methods=["POST"])
@require_auth
def manual_invoice_validate():
    """Validate a manually entered invoice."""
    # User is authenticated via @require_auth decorator
    user_id = request.current_user_id
    
    # Service availability check
    if MANUAL_VALIDATOR is None:
        message = "Invoice validation service is unavailable"
        if VALIDATOR_IMPORT_ERROR:
            message += f": {VALIDATOR_IMPORT_ERROR}"
        return jsonify({"error": message}), 503
    
    # Parse and validate input
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body is required"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400
    
    # Read language from request (default to 'en')
    language = data.get("language", "en")
    if language not in ("en", "ja"):
        language = "en"
    
    # Validate required fields
    errors = []
    
    seller_name = data.get("sellerName", "").strip()
    seller_reg_no = data.get("sellerRegNo", "").strip()
    seller_address = data.get("sellerAddress", "").strip()
    buyer_name = data.get("buyerName", "").strip()
    buyer_address = data.get("buyerAddress", "").strip()
    invoice_no = data.get("invoiceNo", "").strip()
    invoice_date = data.get("invoiceDate", "").strip()
    due_date = data.get("dueDate", "").strip()
    items = data.get("items", [])
    totals = data.get("totals", {})  # Optional totals for verification
    
    if not seller_name:
        errors.append("sellerName is required")
    if not seller_reg_no:
        errors.append("sellerRegNo is required")
    elif not seller_reg_no.isdigit() or len(seller_reg_no) != 13:
        errors.append("sellerRegNo must be a 13-digit numeric value")
    if not seller_address:
        errors.append("sellerAddress is required")
    if not buyer_name:
        errors.append("buyerName is required")
    if not buyer_address:
        errors.append("buyerAddress is required")
    if not invoice_no:
        errors.append("invoiceNo is required")
    if not invoice_date:
        errors.append("invoiceDate is required")
    elif len(invoice_date) > 0:
        try:
            datetime.fromisoformat(invoice_date)
        except (ValueError, TypeError):
            errors.append("invoiceDate must be in YYYY-MM-DD format")
    if not isinstance(items, list) or len(items) == 0:
        errors.append("items must be a non-empty array")
    
    # Validate items
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{idx}] must be an object")
            continue
        
        description = item.get("description", "").strip()
        qty = item.get("qty")
        unit_price = item.get("unitPrice")
        item_tax_rate = item.get("taxRate", "").strip()
        
        if not description:
            errors.append(f"items[{idx}].description is required")
        if not isinstance(qty, (int, float)) or qty <= 0:
            errors.append(f"items[{idx}].qty must be a positive number")
        if not isinstance(unit_price, (int, float)) or unit_price < 0:
            errors.append(f"items[{idx}].unitPrice must be a non-negative number")
        if not item_tax_rate:
            errors.append(f"items[{idx}].taxRate is required")
    
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400
    
    # Normalize invoice data for validator
    normalized_items = []
    computed_subtotal = 0.0
    computed_tax_total = 0.0
    
    for item in items:
        qty = float(item.get("qty", 0))
        unit_price = float(item.get("unitPrice", 0))
        amount_excl_tax = qty * unit_price
        computed_subtotal += amount_excl_tax
        
        tax_rate_str = item.get("taxRate", "0%").strip()
        tax_rate_num = float(tax_rate_str.replace("%", ""))
        computed_tax_total += (amount_excl_tax * tax_rate_num) / 100.0
        
        normalized_items.append({
            "description": item.get("description", "").strip(),
            "amount_excl_tax": amount_excl_tax,
            "tax_rate": tax_rate_str,
        })
    
    computed_grand_total = computed_subtotal + computed_tax_total
    
    # Verify totals if provided
    totals_errors = []
    if totals:
        expected_subtotal = totals.get("subtotal")
        expected_tax_total = totals.get("taxTotal")
        expected_grand_total = totals.get("grandTotal")
        
        tolerance = 0.01  # Allow small floating point differences
        
        if expected_subtotal is not None and abs(float(expected_subtotal) - computed_subtotal) > tolerance:
            totals_errors.append(f"Subtotal mismatch: expected {expected_subtotal}, computed {computed_subtotal:.2f}")
        if expected_tax_total is not None and abs(float(expected_tax_total) - computed_tax_total) > tolerance:
            totals_errors.append(f"Tax total mismatch: expected {expected_tax_total}, computed {computed_tax_total:.2f}")
        if expected_grand_total is not None and abs(float(expected_grand_total) - computed_grand_total) > tolerance:
            totals_errors.append(f"Grand total mismatch: expected {expected_grand_total}, computed {computed_grand_total:.2f}")
    
    # Check for errors after totals verification
    if totals_errors:
        errors.extend(totals_errors)
    
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400
    
    # Use provided invoice_date or default to today
    invoice_date_to_use = invoice_date if invoice_date else datetime.utcnow().date().isoformat()
    
    # Normalize seller_reg_no to include T prefix for validator (pattern: ^T[0-9]{13}$)
    normalized_issuer_id = seller_reg_no
    if normalized_issuer_id and not normalized_issuer_id.startswith('T'):
        normalized_issuer_id = f"T{seller_reg_no}"
    
    normalized_invoice = {
        "invoice_number": invoice_no,
        "issuer_name": seller_name,
        "issuer_id": normalized_issuer_id,
        "buyer": buyer_name,
        "address": seller_address,
        "date": invoice_date_to_use,
        "items": normalized_items,
    }
    
    # Add due_date if provided (validator may not use it, but preserve it)
    if due_date:
        normalized_invoice["due_date"] = due_date
    
    # Validate with InvoiceValidator
    try:
        # Use selected language for validation messages (fallback to "both" if language not supported)
        validation_language = language if language in ("en", "ja") else "both"
        validation_result = MANUAL_VALIDATOR.validate(normalized_invoice, language=validation_language)
    except Exception as exc:
        log_error(exc, "manual_invoice_validate")
        return jsonify({"error": "Validation processing failed"}), 500
    
    # Extract issues from validation result
    issues = []
    fields = validation_result.get("fields", {})
    for field_name, field_data in fields.items():
        if field_data.get("status") == "fail":
            messages = field_data.get("messages", {})
            # Use selected language for messages, fallback to English
            lang_key = language if language in ("en", "ja") else "en"
            lang_messages = messages.get(lang_key, messages.get("en", []))
            for msg in lang_messages:
                issues.append(f"{field_name}: {msg}")
    
    # Also include auto-fix summary issues
    auto_fix_summary = validation_result.get("auto_fix_summary", {})
    needs_user_action = auto_fix_summary.get("needs_user_action", [])
    issues.extend(needs_user_action)
    
    # Include totals errors in issues if any
    if totals_errors:
        issues.extend(totals_errors)
    
    overall = validation_result.get("overall", {})
    compliant = overall.get("compliant", False)
    issues_count = validation_result.get("issues_count", len(issues))
    status = "pass" if compliant else "fail"
    
    response_body = {
        "compliant": compliant,
        "issues_count": issues_count,
        "issues": issues,
        "normalized": normalized_invoice,
        "status": status,
        "language": language,  # Include language in response
    }
    
    return jsonify(response_body), 200


@app.route("/manual-invoice/generate", methods=["POST"])
@require_auth
def manual_invoice_generate():
    """Generate PDF for a manually entered invoice after validation."""
    # User is authenticated via @require_auth
    user_id = request.current_user_id
    
    # Service availability checks
    if MANUAL_VALIDATOR is None:
        message = "Invoice validation service is unavailable"
        if VALIDATOR_IMPORT_ERROR:
            message += f": {VALIDATOR_IMPORT_ERROR}"
        return jsonify({"error": message}), 503
    
    if INVOICE_PDF_GENERATOR is None:
        message = "PDF generation service is unavailable"
        if PDF_GENERATOR_IMPORT_ERROR:
            message += f": {PDF_GENERATOR_IMPORT_ERROR}"
        return jsonify({"error": message}), 503
    
    # Parse input
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "JSON body is required"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid JSON: {str(e)}"}), 400
    
    # Read language from request (default to 'en')
    language = data.get("language", "en")
    if language not in ("en", "ja"):
        language = "en"
    
    # Validate and normalize using shared helper
    try:
        errors, normalized_invoice, validation_result = _validate_and_normalize_invoice_data(data, language=language)
    except Exception as exc:
        log_error(exc, "manual_invoice_generate_validate")
        return jsonify({"error": "Validation processing failed"}), 500
    
    if errors:
        return jsonify({"error": "Validation failed", "details": errors}), 400
    
    if not normalized_invoice or not validation_result:
        return jsonify({"error": "Validation failed"}), 400
    
    # Extract data for PDF generation
    seller_name = normalized_invoice.get("issuer_name", "")
    buyer_name = normalized_invoice.get("buyer", "")
    invoice_number = normalized_invoice.get("invoice_number", "")
    issue_date = normalized_invoice.get("date", "")
    registration_number = normalized_invoice.get("issuer_id", "").lstrip("T")  # Remove T prefix for PDF
    address = normalized_invoice.get("address", "")
    items_data = normalized_invoice.get("items", [])
    
    # Extract items arrays for PDF generator from original data
    original_items = data.get("items", [])
    items = []
    quantities = []
    prices = []
    
    # Extract tax rate from first item (PDF generator expects single tax rate)
    tax_rate = 10.0  # Default
    if original_items and len(original_items) > 0:
        first_tax_rate_str = original_items[0].get("taxRate", "10%").strip().replace("%", "")
        try:
            tax_rate = float(first_tax_rate_str)
        except (ValueError, TypeError):
            tax_rate = 10.0
    
    # Extract from original items array (preserves qty and unitPrice)
    for item in original_items:
        items.append(item.get("description", "").strip())
        quantities.append(float(item.get("qty", 1)))
        prices.append(float(item.get("unitPrice", 0)))
    
    # Optional fields (can be blank)
    phone = data.get("phone", "").strip() or ""
    email = data.get("email", "").strip() or ""
    transaction_date = issue_date  # Use invoice date as transaction date
    reduced_rate = ""  # Empty unless needed
    remarks = data.get("remarks", "").strip() or ""
    
    # Generate PDF
    try:
        pdf_buffer = io.BytesIO()
        INVOICE_PDF_GENERATOR(
            pdf_buffer,
            seller_name,
            buyer_name,
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
            language=language,
        )
        
        pdf_buffer.seek(0)
        
        # Return PDF as file download
        return send_file(
            pdf_buffer,
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"invoice_{invoice_number}.pdf",
        )
        
    except Exception as exc:
        log_error(exc, "manual_invoice_generate_pdf")
        return jsonify({"error": "PDF generation failed"}), 500


def _validate_and_normalize_invoice_data(data, language="en"):
    """
    Helper function to validate and normalize invoice data.
    Returns (errors, normalized_invoice, validation_result) or raises exceptions.
    
    Args:
        data: Invoice data dictionary
        language: Language for validation messages ('en' or 'ja', default 'en')
    """
    errors = []
    
    # Extract and validate fields
    seller_name = data.get("sellerName", "").strip()
    seller_reg_no = data.get("sellerRegNo", "").strip()
    seller_address = data.get("sellerAddress", "").strip()
    buyer_name = data.get("buyerName", "").strip()
    buyer_address = data.get("buyerAddress", "").strip()
    invoice_no = data.get("invoiceNo", "").strip()
    invoice_date = data.get("invoiceDate", "").strip()
    due_date = data.get("dueDate", "").strip()
    items = data.get("items", [])
    totals = data.get("totals", {})
    
    # Validate required fields
    if not seller_name:
        errors.append("sellerName is required")
    if not seller_reg_no:
        errors.append("sellerRegNo is required")
    elif not seller_reg_no.isdigit() or len(seller_reg_no) != 13:
        errors.append("sellerRegNo must be a 13-digit numeric value")
    if not seller_address:
        errors.append("sellerAddress is required")
    if not buyer_name:
        errors.append("buyerName is required")
    if not buyer_address:
        errors.append("buyerAddress is required")
    if not invoice_no:
        errors.append("invoiceNo is required")
    if not invoice_date:
        errors.append("invoiceDate is required")
    elif len(invoice_date) > 0:
        try:
            datetime.fromisoformat(invoice_date)
        except (ValueError, TypeError):
            errors.append("invoiceDate must be in YYYY-MM-DD format")
    if not isinstance(items, list) or len(items) == 0:
        errors.append("items must be a non-empty array")
    
    # Validate items
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f"items[{idx}] must be an object")
            continue
        
        description = item.get("description", "").strip()
        qty = item.get("qty")
        unit_price = item.get("unitPrice")
        item_tax_rate = item.get("taxRate", "").strip()
        
        if not description:
            errors.append(f"items[{idx}].description is required")
        if not isinstance(qty, (int, float)) or qty <= 0:
            errors.append(f"items[{idx}].qty must be a positive number")
        if not isinstance(unit_price, (int, float)) or unit_price < 0:
            errors.append(f"items[{idx}].unitPrice must be a non-negative number")
        if not item_tax_rate:
            errors.append(f"items[{idx}].taxRate is required")
    
    if errors:
        return errors, None, None
    
    # Normalize invoice data
    normalized_items = []
    computed_subtotal = 0.0
    computed_tax_total = 0.0
    
    for item in items:
        qty = float(item.get("qty", 0))
        unit_price = float(item.get("unitPrice", 0))
        amount_excl_tax = qty * unit_price
        computed_subtotal += amount_excl_tax
        
        tax_rate_str = item.get("taxRate", "0%").strip()
        tax_rate_num = float(tax_rate_str.replace("%", ""))
        computed_tax_total += (amount_excl_tax * tax_rate_num) / 100.0
        
        normalized_items.append({
            "description": item.get("description", "").strip(),
            "amount_excl_tax": amount_excl_tax,
            "tax_rate": tax_rate_str,
        })
    
    computed_grand_total = computed_subtotal + computed_tax_total
    
    # Verify totals if provided
    totals_errors = []
    if totals:
        expected_subtotal = totals.get("subtotal")
        expected_tax_total = totals.get("taxTotal")
        expected_grand_total = totals.get("grandTotal")
        
        tolerance = 0.01
        if expected_subtotal is not None and abs(float(expected_subtotal) - computed_subtotal) > tolerance:
            totals_errors.append(f"Subtotal mismatch: expected {expected_subtotal}, computed {computed_subtotal:.2f}")
        if expected_tax_total is not None and abs(float(expected_tax_total) - computed_tax_total) > tolerance:
            totals_errors.append(f"Tax total mismatch: expected {expected_tax_total}, computed {computed_tax_total:.2f}")
        if expected_grand_total is not None and abs(float(expected_grand_total) - computed_grand_total) > tolerance:
            totals_errors.append(f"Grand total mismatch: expected {expected_grand_total}, computed {computed_grand_total:.2f}")
    
    if totals_errors:
        errors.extend(totals_errors)
    
    if errors:
        return errors, None, None
    
    # Normalize invoice structure
    invoice_date_to_use = invoice_date if invoice_date else datetime.utcnow().date().isoformat()
    
    normalized_issuer_id = seller_reg_no
    if normalized_issuer_id and not normalized_issuer_id.startswith('T'):
        normalized_issuer_id = f"T{seller_reg_no}"
    
    normalized_invoice = {
        "invoice_number": invoice_no,
        "issuer_name": seller_name,
        "issuer_id": normalized_issuer_id,
        "buyer": buyer_name,
        "address": seller_address,
        "date": invoice_date_to_use,
        "items": normalized_items,
    }
    
    if due_date:
        normalized_invoice["due_date"] = due_date
    
    # Validate with InvoiceValidator
    if MANUAL_VALIDATOR is None:
        raise Exception("Validation service unavailable")
    
    # Use selected language for validation messages (fallback to "both" if language not supported)
    validation_language = language if language in ("en", "ja") else "both"
    validation_result = MANUAL_VALIDATOR.validate(normalized_invoice, language=validation_language)
    
    # Collect issues
    issues = []
    fields = validation_result.get("fields", {})
    for field_name, field_data in fields.items():
        if field_data.get("status") == "fail":
            messages = field_data.get("messages", {})
            # Use selected language for messages, fallback to English
            lang_key = language if language in ("en", "ja") else "en"
            lang_messages = messages.get(lang_key, messages.get("en", []))
            for msg in lang_messages:
                issues.append(f"{field_name}: {msg}")
    
    auto_fix_summary = validation_result.get("auto_fix_summary", {})
    needs_user_action = auto_fix_summary.get("needs_user_action", [])
    issues.extend(needs_user_action)
    
    if totals_errors:
        issues.extend(totals_errors)
    
    return errors if errors else None, normalized_invoice, validation_result


if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
