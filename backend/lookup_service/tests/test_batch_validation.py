"""
Tests for invoice validation in batch processing (file upload path).
Tests cover required fields, date validity, and totals/tax calculations.
"""
import os
import sys
import unittest
from datetime import datetime

# Add audos_console to path for imports
AUDOS_CONSOLE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "audos_console"))
if AUDOS_CONSOLE_DIR not in sys.path:
    sys.path.insert(0, AUDOS_CONSOLE_DIR)

from validator.validator import InvoiceValidator
from shared.validation_helpers import validate_totals_and_tax, compute_totals_from_items


class BatchValidationTests(unittest.TestCase):
    """Test validation logic used in batch processing (file upload path)."""
    
    def setUp(self):
        """Set up validator for tests."""
        self.validator = InvoiceValidator()
    
    def test_missing_required_fields(self):
        """Test that missing required fields are caught by validator."""
        # Missing issuer_name (required)
        invoice = {
            "invoice_number": "INV-001",
            "buyer": "Test Buyer",
            "date": "2024-01-01",
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
        }
        
        result = self.validator.validate(invoice, language="both")
        
        self.assertFalse(result["overall"]["compliant"])
        self.assertGreater(result["issues_count"], 0)
        self.assertIn("issuer_name", result["fields"])
        self.assertEqual(result["fields"]["issuer_name"]["status"], "fail")
    
    def test_missing_buyer_field(self):
        """Test that missing buyer field is caught."""
        invoice = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "date": "2024-01-01",
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
        }
        
        result = self.validator.validate(invoice, language="both")
        
        self.assertFalse(result["overall"]["compliant"])
        self.assertIn("buyer", result["fields"])
        self.assertEqual(result["fields"]["buyer"]["status"], "fail")
    
    def test_invalid_date_format(self):
        """Test that invalid date format is caught."""
        invoice = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "01/01/2024",  # Invalid format (should be YYYY-MM-DD)
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
        }
        
        result = self.validator.validate(invoice, language="both")
        
        self.assertFalse(result["overall"]["compliant"])
        self.assertIn("date", result["fields"])
        self.assertEqual(result["fields"]["date"]["status"], "fail")
    
    def test_valid_date_format(self):
        """Test that valid ISO date format passes validation."""
        invoice = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "2024-01-01",  # Valid ISO format
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}
            ],
        }
        
        result = self.validator.validate(invoice, language="both")
        
        # Date should not be in failed fields
        if "date" in result["fields"]:
            self.assertNotEqual(result["fields"]["date"]["status"], "fail")
    
    def test_incorrect_totals_validation(self):
        """Test that incorrect totals are caught by validation helper."""
        items = [
            {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"},
            {"description": "Item 2", "amount_excl_tax": 200.0, "tax_rate": "8%"},
        ]
        
        # Correct totals: subtotal=300, tax=26 (10+16), grand=326
        # But provide incorrect totals
        totals = {
            "subtotal": 300.0,
            "taxTotal": 30.0,  # Wrong! Should be 26.0
            "grandTotal": 330.0,  # Wrong! Should be 326.0
        }
        
        errors = validate_totals_and_tax(items, totals)
        
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("Tax total mismatch" in err for err in errors))
        self.assertTrue(any("Grand total mismatch" in err for err in errors))
    
    def test_correct_totals_validation(self):
        """Test that correct totals pass validation."""
        items = [
            {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"},
            {"description": "Item 2", "amount_excl_tax": 200.0, "tax_rate": "8%"},
        ]
        
        # Correct totals: subtotal=300, tax=26 (10+16), grand=326
        totals = {
            "subtotal": 300.0,
            "taxTotal": 26.0,
            "grandTotal": 326.0,
        }
        
        errors = validate_totals_and_tax(items, totals)
        
        self.assertEqual(len(errors), 0)
    
    def test_totals_with_tolerance(self):
        """Test that small floating point differences are tolerated."""
        items = [
            {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"},
        ]
        
        # Correct total is 110.0, but provide 110.005 (within tolerance)
        totals = {
            "subtotal": 100.0,
            "taxTotal": 10.005,  # Small difference
            "grandTotal": 110.005,
        }
        
        errors = validate_totals_and_tax(items, totals, tolerance=0.01)
        
        # Should pass with tolerance
        self.assertEqual(len(errors), 0)
    
    def test_totals_outside_tolerance(self):
        """Test that differences outside tolerance are caught."""
        items = [
            {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"},
        ]
        
        # Correct total is 110.0, but provide 110.02 (outside tolerance of 0.01)
        totals = {
            "subtotal": 100.0,
            "taxTotal": 10.02,  # Outside tolerance
            "grandTotal": 110.02,
        }
        
        errors = validate_totals_and_tax(items, totals, tolerance=0.01)
        
        # Should fail
        self.assertGreater(len(errors), 0)
    
    def test_invalid_tax_rate_enum(self):
        """Test that invalid tax rate values are caught."""
        invoice = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "2024-01-01",
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "15%"}  # Invalid (not 0%, 8%, or 10%)
            ],
        }
        
        result = self.validator.validate(invoice, language="both")
        
        self.assertFalse(result["overall"]["compliant"])
        # Should have an issue with tax_rate
        self.assertGreater(result["issues_count"], 0)
    
    def test_valid_tax_rate_enum(self):
        """Test that valid tax rate values pass validation."""
        invoice = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer",
            "buyer": "Test Buyer",
            "date": "2024-01-01",
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"}  # Valid
            ],
        }
        
        result = self.validator.validate(invoice, language="both")
        
        # Tax rate should not cause issues
        tax_rate_issues = [
            field for field in result.get("fields", {})
            if "tax_rate" in field.lower()
        ]
        self.assertEqual(len(tax_rate_issues), 0)
    
    def test_fully_valid_invoice(self):
        """Test that a fully valid invoice passes all checks."""
        invoice = {
            "invoice_number": "INV-001",
            "issuer_name": "Test Issuer Co.",
            "issuer_id": "T1234567890123",
            "buyer": "Test Buyer Inc.",
            "date": "2024-01-01",
            # Note: address field uses regex with Unicode properties that require 'regex' module
            # Since we're using stdlib 're', we omit address to avoid that validation
            "items": [
                {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"},
                {"description": "Item 2", "amount_excl_tax": 200.0, "tax_rate": "8%"},
            ],
        }
        
        result = self.validator.validate(invoice, language="both")
        
        self.assertTrue(result["overall"]["compliant"])
        self.assertEqual(result["issues_count"], 0)
    
    def test_compute_totals_from_items(self):
        """Test the compute_totals_from_items helper function."""
        items = [
            {"description": "Item 1", "amount_excl_tax": 100.0, "tax_rate": "10%"},
            {"description": "Item 2", "amount_excl_tax": 200.0, "tax_rate": "8%"},
        ]
        
        totals = compute_totals_from_items(items)
        
        self.assertEqual(totals["subtotal"], 300.0)
        self.assertEqual(totals["taxTotal"], 26.0)  # 10 + 16
        self.assertEqual(totals["grandTotal"], 326.0)
    
    def test_empty_items_list(self):
        """Test that empty items list is handled correctly."""
        items = []
        
        totals = compute_totals_from_items(items)
        
        self.assertEqual(totals["subtotal"], 0.0)
        self.assertEqual(totals["taxTotal"], 0.0)
        self.assertEqual(totals["grandTotal"], 0.0)


if __name__ == "__main__":
    unittest.main()

