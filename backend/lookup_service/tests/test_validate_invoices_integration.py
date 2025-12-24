"""
Integration tests for /validate-invoices endpoint.
Tests that uploaded invoices are validated using real JSON metadata, not filename guesses.
"""
import json
import os
import tempfile
import unittest
from io import BytesIO
from unittest import mock

from app import app as flask_app


class ValidateInvoicesIntegrationTests(unittest.TestCase):
    """Integration tests for invoice validation via file upload with JSON metadata."""
    
    def setUp(self):
        """Set up test client and environment."""
        self.client = flask_app.test_client()
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"
        os.environ["DATABASE_URL"] = "sqlite:///:memory:"
        # Initialize database
        from db.db import init_db
        init_db()
        # Register a user to obtain JWT
        register_response = self.client.post(
            "/api/auth/register",
            json={"email": "test@example.com", "password": "password123"},
        )
        self.valid_token = register_response.get_json()["access_token"]
        
        # Mock run_batch to capture what invoices are passed to it
        self.run_batch_patcher = mock.patch("app.run_batch")
        self.mock_run_batch = self.run_batch_patcher.start()
        self.mock_run_batch.return_value = {
            "batch_id": "test-batch",
            "counts": {"pass": 0, "fail": 1, "warn": 0},
            "invoices": [
                {
                    "invoice_number": "INV-001",
                    "status": "fail",
                    "compliant": False,
                    "issues": 1,
                }
            ],
        }
    
    def tearDown(self):
        """Clean up."""
        for key in ["SECRET_KEY", "JWT_SECRET", "DATABASE_URL"]:
            if key in os.environ:
                del os.environ[key]
        self.run_batch_patcher.stop()
    
    def _make_authorized_request(self, files_data, metadata_json=None, token=None):
        """Helper to make authorized request with token and metadata."""
        headers = {}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        
        # Add metadata to form data
        if metadata_json:
            if isinstance(metadata_json, str):
                files_data["metadata"] = metadata_json
            elif isinstance(metadata_json, list):
                for idx, meta in enumerate(metadata_json):
                    files_data[f"metadata"] = meta  # Flask will handle as list
        
        return self.client.post(
            "/validate-invoices",
            data=files_data,
            content_type="multipart/form-data",
            headers=headers,
        )
    
    def test_missing_required_fields_rejects_with_400(self):
        """Test that invoices missing required fields are rejected with 400."""
        pdf_content = b"%PDF-1.4\nminimal pdf"
        
        # Missing issuer_name and buyer
        invalid_metadata = {
            "invoice_number": "INV-001",
            "date": "2024-01-01",
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
        }
        
        files_data = {"files": [(BytesIO(pdf_content), "test.pdf")]}
        response = self._make_authorized_request(
            files_data,
            metadata_json=json.dumps(invalid_metadata),
            token=self.valid_token
        )
        
        # Should reject with 400, not process
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        # Should mention missing fields
        self.assertIn("issuer_name", payload["error"].lower() or payload.get("details", "").lower())
        # Should not call run_batch
        self.mock_run_batch.assert_not_called()
    
    def test_missing_buyer_rejects_with_400(self):
        """Test that missing buyer field is rejected."""
        pdf_content = b"%PDF-1.4\ntest"
        
        invalid_metadata = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "date": "2024-01-01",
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
        }
        
        files_data = {"files": [(BytesIO(pdf_content), "test.pdf")]}
        response = self._make_authorized_request(
            files_data,
            metadata_json=json.dumps(invalid_metadata),
            token=self.valid_token
        )
        
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("buyer", payload["error"].lower())
        self.mock_run_batch.assert_not_called()
    
    def test_invalid_date_format_rejects_with_400(self):
        """Test that invalid date format is rejected with 400."""
        pdf_content = b"%PDF-1.4\ntest"
        
        invalid_metadata = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "01/01/2024",  # Invalid format (should be YYYY-MM-DD)
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
        }
        
        files_data = {"files": [(BytesIO(pdf_content), "test.pdf")]}
        response = self._make_authorized_request(
            files_data,
            metadata_json=json.dumps(invalid_metadata),
            token=self.valid_token
        )
        
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("date", payload["error"].lower())
        self.assertIn("YYYY-MM-DD", payload["error"])
        self.mock_run_batch.assert_not_called()
    
    def test_missing_items_rejects_with_400(self):
        """Test that missing items array is rejected."""
        pdf_content = b"%PDF-1.4\ntest"
        
        invalid_metadata = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "2024-01-01",
            # Missing items
        }
        
        files_data = {"files": [(BytesIO(pdf_content), "test.pdf")]}
        response = self._make_authorized_request(
            files_data,
            metadata_json=json.dumps(invalid_metadata),
            token=self.valid_token
        )
        
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("items", payload["error"].lower())
        self.mock_run_batch.assert_not_called()
    
    def test_invalid_tax_rate_rejects_with_400(self):
        """Test that invalid tax rate is rejected."""
        pdf_content = b"%PDF-1.4\ntest"
        
        invalid_metadata = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "2024-01-01",
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "15%"}  # Invalid
            ],
        }
        
        files_data = {"files": [(BytesIO(pdf_content), "test.pdf")]}
        response = self._make_authorized_request(
            files_data,
            metadata_json=json.dumps(invalid_metadata),
            token=self.valid_token
        )
        
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("tax_rate", payload["error"].lower())
        self.mock_run_batch.assert_not_called()
    
    def test_incorrect_totals_passes_to_validator(self):
        """Test that invoices with incorrect totals are passed to validator (not rejected at parse time)."""
        pdf_content = b"%PDF-1.4\ntest"
        
        # Valid structure but incorrect totals
        metadata = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "2024-01-01",
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
            "totals": {
                "subtotal": 100.0,
                "taxTotal": 15.0,  # Wrong! Should be 10.0
                "grandTotal": 115.0,  # Wrong! Should be 110.0
            },
        }
        
        # Mock run_batch to return failure for totals mismatch
        self.mock_run_batch.return_value = {
            "batch_id": "test-batch",
            "counts": {"pass": 0, "fail": 1, "warn": 0},
            "invoices": [
                {
                    "invoice_number": "INV-001",
                    "status": "fail",
                    "compliant": False,
                    "issues": 1,  # Totals mismatch
                }
            ],
        }
        
        files_data = {"files": [(BytesIO(pdf_content), "test.pdf")]}
        response = self._make_authorized_request(
            files_data,
            metadata_json=json.dumps(metadata),
            token=self.valid_token
        )
        
        # Should pass parsing and reach validator
        self.assertEqual(response.status_code, 200)
        self.mock_run_batch.assert_called_once()
        
        # Verify invoice passed to run_batch has totals
        call_args = self.mock_run_batch.call_args[0][0]
        invoice = call_args[0]
        self.assertIn("totals", invoice)
        self.assertEqual(invoice["totals"]["taxTotal"], 15.0)
        self.assertEqual(invoice["totals"]["grandTotal"], 115.0)
    
    def test_valid_invoice_passes_validation(self):
        """Test that a valid invoice passes parsing and validation."""
        pdf_content = b"%PDF-1.4\nvalid invoice pdf"
        
        valid_metadata = {
            "invoice_number": "INV-001",
            "issuer_name": "Acme Corporation",
            "buyer": "Customer Inc.",
            "date": "2024-01-01",
            "items": [
                {"description": "Product A", "amount_excl_tax": 1000.0, "tax_rate": "10%"},
                {"description": "Product B", "amount_excl_tax": 500.0, "tax_rate": "8%"},
            ],
            "totals": {
                "subtotal": 1500.0,
                "taxTotal": 130.0,  # 100 + 40
                "grandTotal": 1630.0,
            },
        }
        
        # Mock run_batch to return success
        self.mock_run_batch.return_value = {
            "batch_id": "test-batch",
            "counts": {"pass": 1, "fail": 0, "warn": 0},
            "invoices": [
                {
                    "invoice_number": "INV-001",
                    "status": "pass",
                    "compliant": True,
                    "issues": 0,
                    "pdf_path": "/tmp/test.pdf",
                }
            ],
        }
        
        files_data = {"files": [(BytesIO(pdf_content), "invoice.pdf")]}
        response = self._make_authorized_request(
            files_data,
            metadata_json=json.dumps(valid_metadata),
            token=self.valid_token
        )
        
        self.assertEqual(response.status_code, 200)
        self.mock_run_batch.assert_called_once()
        
        # Verify the parsed invoice has all required fields with real values
        call_args = self.mock_run_batch.call_args[0][0]
        invoice = call_args[0]
        
        # Required fields with real values (not stubs)
        self.assertEqual(invoice["invoice_number"], "INV-001")
        self.assertEqual(invoice["issuer_name"], "Acme Corporation")
        self.assertEqual(invoice["buyer"], "Customer Inc.")
        self.assertEqual(invoice["date"], "2024-01-01")
        
        # Items with real data
        self.assertEqual(len(invoice["items"]), 2)
        self.assertEqual(invoice["items"][0]["description"], "Product A")
        self.assertEqual(invoice["items"][0]["amount_excl_tax"], 1000.0)
        self.assertEqual(invoice["items"][0]["tax_rate"], "10%")
        
        # Totals
        self.assertIn("totals", invoice)
        self.assertEqual(invoice["totals"]["subtotal"], 1500.0)
        self.assertEqual(invoice["totals"]["taxTotal"], 130.0)
        self.assertEqual(invoice["totals"]["grandTotal"], 1630.0)
    
    def test_multiple_files_with_metadata(self):
        """Test that multiple files with corresponding metadata are processed."""
        pdf_content1 = b"%PDF-1.4\ninvoice1"
        pdf_content2 = b"%PDF-1.4\ninvoice2"
        
        metadata1 = {
            "invoice_number": "INV-001",
            "issuer_name": "Company A",
            "buyer": "Customer 1",
            "date": "2024-01-01",
            "items": [{"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}],
        }
        
        metadata2 = {
            "invoice_number": "INV-002",
            "issuer_name": "Company B",
            "buyer": "Customer 2",
            "date": "2024-01-02",
            "items": [{"description": "Item 2", "amount_excl_tax": 200.0, "tax_rate": "8%"}],
        }
        
        self.mock_run_batch.return_value = {
            "batch_id": "test-batch",
            "counts": {"pass": 2, "fail": 0, "warn": 0},
            "invoices": [
                {"invoice_number": "INV-001", "status": "pass", "compliant": True, "issues": 0},
                {"invoice_number": "INV-002", "status": "pass", "compliant": True, "issues": 0},
            ],
        }
        
        files_data = {
            "files": [
                (BytesIO(pdf_content1), "invoice1.pdf"),
                (BytesIO(pdf_content2), "invoice2.pdf"),
            ],
            "metadata": [json.dumps(metadata1), json.dumps(metadata2)],
        }
        
        response = self._make_authorized_request(files_data, token=self.valid_token)
        
        self.assertEqual(response.status_code, 200)
        self.mock_run_batch.assert_called_once()
        
        # Verify both invoices were parsed
        call_args = self.mock_run_batch.call_args[0][0]
        self.assertEqual(len(call_args), 2)
        self.assertEqual(call_args[0]["invoice_number"], "INV-001")
        self.assertEqual(call_args[1]["invoice_number"], "INV-002")
    
    def test_missing_metadata_rejects_with_400(self):
        """Test that missing metadata rejects with 400."""
        pdf_content = b"%PDF-1.4\ntest"
        
        files_data = {"files": [(BytesIO(pdf_content), "test.pdf")]}
        # No metadata provided
        response = self._make_authorized_request(files_data, token=self.valid_token)
        
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("metadata", payload["error"].lower())
        self.mock_run_batch.assert_not_called()
    
    def test_invalid_json_metadata_rejects_with_400(self):
        """Test that invalid JSON metadata rejects with 400."""
        pdf_content = b"%PDF-1.4\ntest"
        
        files_data = {
            "files": [(BytesIO(pdf_content), "test.pdf")],
            "metadata": "not valid json {",
        }
        
        response = self._make_authorized_request(files_data, token=self.valid_token)
        
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIn("error", payload)
        self.assertIn("json", payload["error"].lower())
        self.mock_run_batch.assert_not_called()


if __name__ == "__main__":
    unittest.main()
