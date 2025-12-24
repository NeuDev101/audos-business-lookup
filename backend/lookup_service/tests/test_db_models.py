"""
Unit and integration tests for database models and persistence.

Tests invoice insertion, retrieval, and error handling.
"""

import unittest
import os
import tempfile
import sys
from unittest.mock import patch

# Add audos_console to path
AUDOS_CONSOLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "audos_console"))
if AUDOS_CONSOLE_DIR not in sys.path:
    sys.path.insert(0, AUDOS_CONSOLE_DIR)

from db.models import InvoiceResult, insert_invoice
from db.db import get_session, init_db, reset_db, get_database_url


class DatabaseModelTests(unittest.TestCase):
    """Tests for database models and persistence."""

    def setUp(self):
        """Set up test database (SQLite in memory)."""
        # Use in-memory SQLite for tests
        self.test_db_url = "sqlite:///:memory:"
        with patch.dict(os.environ, {"DATABASE_URL": self.test_db_url}):
            # Reset module-level engine
            import db.db
            db.db._engine = None
            db.db._session_factory = None
            
            # Initialize database
            init_db()

    def tearDown(self):
        """Clean up test database."""
        # Close any open sessions
        import db.db
        if db.db._session_factory:
            db.db._session_factory.remove()
        db.db._engine = None
        db.db._session_factory = None

    def test_insert_and_retrieve_invoice(self):
        """Test inserting and retrieving an invoice result."""
        invoice = insert_invoice(
            invoice_number="INV-001",
            status="pass",
            issues_count=0,
            pdf_path="/path/to/invoice.pdf",
            pdf_hash="abc123def456",
            ruleset_version="2025-10",
            batch_id="batch-uuid-123",
        )

        self.assertIsNotNone(invoice.id)
        self.assertEqual(invoice.invoice_number, "INV-001")
        self.assertEqual(invoice.status, "pass")
        self.assertEqual(invoice.issues_count, 0)
        self.assertEqual(invoice.pdf_path, "/path/to/invoice.pdf")
        self.assertEqual(invoice.pdf_hash, "abc123def456")
        self.assertEqual(invoice.ruleset_version, "2025-10")
        self.assertEqual(invoice.batch_id, "batch-uuid-123")
        self.assertIsNotNone(invoice.created_at)

        # Retrieve from database
        session = get_session()
        try:
            retrieved = session.query(InvoiceResult).filter_by(invoice_number="INV-001").first()
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.status, "pass")
            self.assertEqual(retrieved.batch_id, "batch-uuid-123")
        finally:
            session.close()

    def test_insert_failed_invoice(self):
        """Test inserting a failed invoice (no PDF path)."""
        invoice = insert_invoice(
            invoice_number="INV-FAIL-001",
            status="fail",
            issues_count=3,
            pdf_path=None,
            pdf_hash="hash-for-failed",
            ruleset_version="2025-10",
            batch_id="batch-uuid-456",
        )

        self.assertEqual(invoice.status, "fail")
        self.assertEqual(invoice.issues_count, 3)
        self.assertIsNone(invoice.pdf_path)
        self.assertEqual(invoice.pdf_hash, "hash-for-failed")

    def test_insert_without_batch_id(self):
        """Test inserting invoice without batch_id."""
        invoice = insert_invoice(
            invoice_number="INV-NO-BATCH",
            status="pass",
            issues_count=0,
            pdf_path="/path/to/invoice.pdf",
            pdf_hash="hash123",
            ruleset_version="2025-10",
            batch_id=None,
        )

        self.assertIsNone(invoice.batch_id)

    def test_to_dict(self):
        """Test converting model to dictionary."""
        invoice = insert_invoice(
            invoice_number="INV-DICT",
            status="pass",
            issues_count=0,
            pdf_path="/path/to/invoice.pdf",
            pdf_hash="hash456",
            ruleset_version="2025-10",
            batch_id="batch-789",
        )

        invoice_dict = invoice.to_dict()
        self.assertEqual(invoice_dict["invoice_number"], "INV-DICT")
        self.assertEqual(invoice_dict["status"], "pass")
        self.assertEqual(invoice_dict["batch_id"], "batch-789")
        self.assertIn("created_at", invoice_dict)

    def test_multiple_invoices_same_batch(self):
        """Test inserting multiple invoices with the same batch_id."""
        batch_id = "shared-batch-123"
        
        inv1 = insert_invoice(
            invoice_number="INV-BATCH-1",
            status="pass",
            issues_count=0,
            pdf_path="/path/1.pdf",
            pdf_hash="hash1",
            batch_id=batch_id,
        )
        
        inv2 = insert_invoice(
            invoice_number="INV-BATCH-2",
            status="fail",
            issues_count=2,
            pdf_path=None,
            pdf_hash="hash2",
            batch_id=batch_id,
        )

        self.assertEqual(inv1.batch_id, batch_id)
        self.assertEqual(inv2.batch_id, batch_id)
        
        # Query by batch_id
        session = get_session()
        try:
            batch_invoices = session.query(InvoiceResult).filter_by(batch_id=batch_id).all()
            self.assertEqual(len(batch_invoices), 2)
        finally:
            session.close()


class DatabaseConfigurationTests(unittest.TestCase):
    """Tests for database configuration and error handling."""

    def test_missing_database_url_uses_default(self):
        """Test that missing DATABASE_URL uses SQLite default."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove DATABASE_URL if present
            if "DATABASE_URL" in os.environ:
                del os.environ["DATABASE_URL"]
            
            import db.db
            db.db._engine = None  # Reset engine
            
            url = db.db.get_database_url()
            # Should default to SQLite
            self.assertIn("sqlite", url.lower())

    def test_empty_database_url_raises_error(self):
        """Test that empty DATABASE_URL raises ValueError."""
        with patch.dict(os.environ, {"DATABASE_URL": ""}):
            import db.db
            db.db._engine = None  # Reset engine
            
            with self.assertRaises(ValueError) as cm:
                db.db.get_database_url()
            self.assertIn("DATABASE_URL", str(cm.exception))

    def test_database_url_from_environment(self):
        """Test that DATABASE_URL is read from environment."""
        test_url = "postgresql://user:pass@localhost:5432/testdb"
        with patch.dict(os.environ, {"DATABASE_URL": test_url}):
            import db.db
            db.db._engine = None  # Reset engine
            
            url = db.db.get_database_url()
            self.assertEqual(url, test_url)

    def test_insert_fails_without_database_url(self):
        """Test that insert fails gracefully if DATABASE_URL is misconfigured."""
        # This test verifies that the error handling works
        # In practice, we'd want to ensure DATABASE_URL is set before running batch_runner
        with patch.dict(os.environ, {"DATABASE_URL": "invalid://url"}):
            import db.db
            db.db._engine = None
            db.db._session_factory = None
            
            # Attempting to insert should raise an error
            with self.assertRaises(Exception):
                insert_invoice(
                    invoice_number="INV-ERROR",
                    status="pass",
                    issues_count=0,
                    pdf_path="/path/to/invoice.pdf",
                    pdf_hash="hash",
                )


if __name__ == "__main__":
    unittest.main()

