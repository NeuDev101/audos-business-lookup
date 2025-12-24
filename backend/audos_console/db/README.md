# Database Package

This package provides SQLAlchemy models and session management for persisting invoice validation results.

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- SQLAlchemy 2.0.23
- psycopg2-binary 2.9.9 (for PostgreSQL support)

### 2. Configure Database URL

Set the `DATABASE_URL` environment variable:

```bash
export DATABASE_URL="postgresql://user:password@localhost:5432/audos_db"
```

For development/testing, you can use SQLite (default if `DATABASE_URL` is not set):
```bash
# Uses sqlite:///./audos_invoices.db by default
```

**Note**: If `DATABASE_URL` is explicitly set to an empty string, the application will raise a `ValueError` to prevent misconfiguration.

### 3. Initialize Database Schema

Run the migration script to create tables:

```bash
cd backend/audos_console
python -m db.migrations
```

Or programmatically:

```python
from db import init_db
init_db()
```

## Models

### InvoiceResult

Stores invoice validation results with the following fields:

- `id` (Integer, Primary Key): Auto-incrementing ID
- `invoice_number` (String, Indexed): Invoice identifier
- `batch_id` (String, Indexed, Optional): Batch UUID for grouping invoices
- `status` (String, Indexed): Validation status ("pass" or "fail")
- `issues_count` (Integer): Number of validation issues found
- `pdf_path` (Text, Optional): Path to generated PDF (None if validation failed)
- `pdf_hash` (String): SHA256 hash of PDF file
- `ruleset_version` (String): Version of validation rules used (default: "2025-10")
- `created_at` (DateTime, Indexed): Timestamp of record creation (UTC)

## Usage

### Inserting Invoice Results

```python
from db.models import insert_invoice

invoice = insert_invoice(
    invoice_number="INV-001",
    status="pass",
    issues_count=0,
    pdf_path="/path/to/invoice.pdf",
    pdf_hash="abc123...",
    ruleset_version="2025-10",
    batch_id="batch-uuid-123",  # Optional
)
```

### Querying Results

```python
from db.db import get_session
from db.models import InvoiceResult

session = get_session()
try:
    # Find all invoices in a batch
    invoices = session.query(InvoiceResult).filter_by(batch_id="batch-uuid-123").all()
    
    # Find failed invoices
    failed = session.query(InvoiceResult).filter_by(status="fail").all()
finally:
    session.close()
```

## Integration with batch_runner

The `batch_runner.py` module automatically inserts invoice results into the database after validation. Ensure `DATABASE_URL` is set before running batch validation.

## Testing

Tests use an in-memory SQLite database by default. See `backend/lookup_service/tests/test_db_models.py` for examples.

Run tests:
```bash
PYTHONPATH=backend/audos_console python -m unittest backend.lookup_service.tests.test_db_models
```

