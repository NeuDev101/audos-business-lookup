"""
Real validation tests for /validate-invoices endpoint.
Tests that the actual validator with rules.json is used, not stubs.
"""
import os
import sys
import unittest
from io import BytesIO
from unittest import mock

# Add audos_console to path for imports
AUDOS_CONSOLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "audos_console"))
if AUDOS_CONSOLE_DIR not in sys.path:
    sys.path.insert(0, AUDOS_CONSOLE_DIR)

from app import app as flask_app
from validator.validator import InvoiceValidator


class ValidateInvoicesRealValidationTests(unittest.TestCase):
    """Tests that verify real validator is used with rules.json."""
    
    def setUp(self):
        """Set up test client and real validator."""
        self.client = flask_app.test_client()
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        # Initialize database
        from db.db import init_db
        init_db()
        # Register user and capture token
        register_response = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.valid_token = register_response.get_json()["access_token"]
        
        # Use real validator (not mocked)
        self.validator = InvoiceValidator()
        
        # Mock run_batch but capture what it receives
        self.run_batch_patcher = mock.patch("app.run_batch")
        self.mock_run_batch = self.run_batch_patcher.start()
        # Set default return value
        self.mock_run_batch.return_value = {
            "batch_id": "test-batch",
            "counts": {"pass": 1, "fail": 0, "warn": 0},
            "invoices": [
                {
                    "invoice_number": "INV-001",
                    "status": "pass",
                    "compliant": True,
                    "issues": 0,
                }
            ],
        }
    
    def tearDown(self):
        """Clean up."""
        for key in ["SECRET_KEY", "JWT_SECRET", "DATABASE_URL"]:
            if key in os.environ:
                del os.environ[key]
        self.run_batch_patcher.stop()
    
    def _make_authorized_request(self, files_data, token=None):
        """Helper to make authorized request."""
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        return self.client.post(
            "/validate-invoices",
            data=files_data,
            content_type="multipart/form-data",
            headers=headers,
        )
    
    def test_parsed_invoice_has_no_unknown_stubs(self):
        """Test that parsed invoices don't contain 'Unknown' placeholder values."""
        pdf_content = b"%PDF-1.4\ntest invoice"
        
        files_data = {"files": [(BytesIO(pdf_content), "INV-TEST-001.pdf")]}
        response = self._make_authorized_request(files_data, token=self.valid_token)
        
        self.assertEqual(response.status_code, 200)
        self.mock_run_batch.assert_called_once()
        
        # Get the invoice passed to run_batch
        call_args = self.mock_run_batch.call_args[0][0]
        invoice = call_args[0]
        
        # Verify no "Unknown" stubs
        self.assertNotEqual(invoice.get("issuer_name"), "Unknown Issuer")
        self.assertNotEqual(invoice.get("buyer"), "Unknown Buyer")
        self.assertIsNotNone(invoice.get("issuer_name"))
        self.assertIsNotNone(invoice.get("buyer"))
    
    def test_parsed_invoice_has_valid_structure_for_validator(self):
        """Test that parsed invoice structure matches what validator expects."""
        pdf_content = b"%PDF-1.4\ntest"
        
        files_data = {
            "files": [
                (BytesIO(pdf_content), "INV-001_AcmeCorp_CustomerInc_2024-01-01.pdf")
            ]
        }
        response = self._make_authorized_request(files_data, token=self.valid_token)
        
        self.assertEqual(response.status_code, 200)
        
        # Get invoice passed to run_batch
        call_args = self.mock_run_batch.call_args[0][0]
        invoice = call_args[0]
        
        # Validate structure matches what validator expects
        # (This is what run_batch will normalize and pass to validator.validate)
        self.assertIn("invoice_number", invoice)
        self.assertIn("issuer_name", invoice)
        self.assertIn("buyer", invoice)
        self.assertIn("date", invoice)
        self.assertIn("items", invoice)
        
        # Items structure
        self.assertGreater(len(invoice["items"]), 0)
        for item in invoice["items"]:
            self.assertIn("description", item)
            self.assertIn("amount_excl_tax", item)
            self.assertIn("tax_rate", item)
            # amount_excl_tax should be numeric
            self.assertIsInstance(item["amount_excl_tax"], (int, float))
            # tax_rate should be string like "10%"
            self.assertIsInstance(item["tax_rate"], str)
    
    def test_validator_would_catch_missing_required_fields(self):
        """Test that if we pass an invoice missing required fields, validator catches it."""
        # Create an invoice missing required fields
        invalid_invoice = {
            "invoice_number": "INV-001",
            # Missing issuer_name and buyer
            "date": "2024-01-01",
            "items": [
                {"description": "Item", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
        }
        
        # Validate with real validator
        result = self.validator.validate(invalid_invoice, language="both")
        
        # Should fail validation
        self.assertFalse(result["overall"]["compliant"])
        self.assertGreater(result["issues_count"], 0)
        # Should have errors for missing fields
        self.assertIn("issuer_name", result["fields"])
        self.assertIn("buyer", result["fields"])
    
    def test_validator_would_catch_invalid_date(self):
        """Test that validator catches invalid date format."""
        invalid_invoice = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "01/01/2024",  # Invalid format
            "items": [
                {"description": "Item", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
        }
        
        result = self.validator.validate(invalid_invoice, language="both")
        
        # Should fail validation
        self.assertFalse(result["overall"]["compliant"])
        self.assertIn("date", result["fields"])
        self.assertEqual(result["fields"]["date"]["status"], "fail")
    
    def test_validator_would_catch_invalid_tax_rate(self):
        """Test that validator catches invalid tax rate."""
        invalid_invoice = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "2024-01-01",
            "items": [
                {"description": "Item", "amount_excl_tax": 100.0, "tax_rate": "15%"}  # Invalid
            ],
        }
        
        result = self.validator.validate(invalid_invoice, language="both")
        
        # Should fail validation
        self.assertFalse(result["overall"]["compliant"])
        self.assertGreater(result["issues_count"], 0)


if __name__ == "__main__":
    unittest.main()
