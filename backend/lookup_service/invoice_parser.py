"""
Invoice parser for uploaded files.
Requires structured JSON metadata - no filename guessing or placeholder data.
"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, List


class InvoiceParseError(Exception):
    """Raised when invoice parsing fails due to missing or invalid data."""
    pass


def parse_invoice_from_json_metadata(
    file_path: str,
    file_content: bytes,
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Parse invoice from structured JSON metadata.
    
    Requires all required fields to be present in metadata. Rejects if missing.
    
    Args:
        file_path: Path to the uploaded file
        file_content: Raw file content (bytes)
        metadata: JSON dict with invoice data (issuer_name, buyer, invoice_number, date, items)
    
    Returns:
        Dictionary with invoice data structure expected by run_batch
    
    Raises:
        InvoiceParseError: If required fields are missing or invalid
    """
    errors = []
    
    # Required fields
    invoice_number = metadata.get("invoice_number")
    if not invoice_number or not str(invoice_number).strip():
        errors.append("invoice_number is required")
    
    issuer_name = metadata.get("issuer_name")
    if not issuer_name or not str(issuer_name).strip():
        errors.append("issuer_name is required")
    
    buyer = metadata.get("buyer")
    if not buyer or not str(buyer).strip():
        errors.append("buyer is required")
    
    date = metadata.get("date")
    if not date or not str(date).strip():
        errors.append("date is required")
    else:
        # Validate date format (ISO YYYY-MM-DD)
        try:
            datetime.fromisoformat(str(date))
        except (ValueError, TypeError):
            errors.append(f"date must be in YYYY-MM-DD format, got: {date}")
    
    # Required: items array with at least one item
    items = metadata.get("items")
    if not items or not isinstance(items, list) or len(items) == 0:
        errors.append("items must be a non-empty array")
    else:
        # Validate each item has required fields
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"items[{idx}] must be an object")
                continue
            
            description = item.get("description", "").strip()
            amount_excl_tax = item.get("amount_excl_tax")
            tax_rate = item.get("tax_rate", "").strip()
            
            if not description:
                errors.append(f"items[{idx}].description is required")
            
            if amount_excl_tax is None:
                errors.append(f"items[{idx}].amount_excl_tax is required")
            else:
                try:
                    amount_excl_tax = float(amount_excl_tax)
                    if amount_excl_tax < 0:
                        errors.append(f"items[{idx}].amount_excl_tax must be non-negative")
                except (ValueError, TypeError):
                    errors.append(f"items[{idx}].amount_excl_tax must be a number")
            
            if not tax_rate:
                errors.append(f"items[{idx}].tax_rate is required")
            elif tax_rate not in ["0%", "8%", "10%"]:
                errors.append(f"items[{idx}].tax_rate must be one of: 0%, 8%, 10%")
    
    # If any errors, reject
    if errors:
        raise InvoiceParseError(f"Invalid invoice metadata: {', '.join(errors)}")
    
    # Build invoice dict with validated data
    invoice = {
        "invoice_number": str(invoice_number).strip()[:64],
        "issuer_name": str(issuer_name).strip()[:128],
        "buyer": str(buyer).strip()[:128],
        "date": str(date).strip(),
        "items": [],
    }
    
    # Normalize items
    for item in items:
        normalized_item = {
            "description": str(item.get("description", "")).strip(),
            "amount_excl_tax": float(item.get("amount_excl_tax", 0)),
            "tax_rate": str(item.get("tax_rate", "")).strip(),
        }
        invoice["items"].append(normalized_item)
    
    # Optional fields
    if "issuer_id" in metadata and metadata["issuer_id"]:
        invoice["issuer_id"] = str(metadata["issuer_id"]).strip()
    
    if "address" in metadata and metadata["address"]:
        invoice["address"] = str(metadata["address"]).strip()
    
    if "phone" in metadata and metadata["phone"]:
        invoice["phone"] = str(metadata["phone"]).strip()
    
    if "email" in metadata and metadata["email"]:
        invoice["email"] = str(metadata["email"]).strip()
    
    if "totals" in metadata and metadata["totals"]:
        totals = metadata["totals"]
        if isinstance(totals, dict):
            invoice["totals"] = {}
            if "subtotal" in totals:
                invoice["totals"]["subtotal"] = float(totals["subtotal"])
            if "taxTotal" in totals:
                invoice["totals"]["taxTotal"] = float(totals["taxTotal"])
            if "grandTotal" in totals:
                invoice["totals"]["grandTotal"] = float(totals["grandTotal"])
    
    if "remarks" in metadata:
        invoice["remarks"] = str(metadata.get("remarks", "")).strip()
    
    # Set source filename for batch processing
    invoice["source_filename"] = file_path
    
    return invoice


def parse_invoice_from_multipart(
    file_path: str,
    file_content: bytes,
    json_metadata: Optional[str] = None
) -> Dict[str, Any]:
    """
    Parse invoice from multipart form data.
    
    If JSON metadata is provided, uses it. If not provided, creates minimal
    metadata from filename and defaults.
    
    Args:
        file_path: Path to the uploaded file
        file_content: Raw file content (bytes)
        json_metadata: JSON string with invoice metadata (optional)
    
    Returns:
        Dictionary with invoice data structure expected by run_batch
    
    Raises:
        InvoiceParseError: If JSON metadata is invalid (when provided)
    """
    if json_metadata:
        try:
            metadata = json.loads(json_metadata)
        except json.JSONDecodeError as e:
            raise InvoiceParseError(f"Invalid JSON metadata: {str(e)}")
        
        if not isinstance(metadata, dict):
            raise InvoiceParseError("Metadata must be a JSON object")
        
        return parse_invoice_from_json_metadata(file_path, file_content, metadata)
    else:
        # Create minimal metadata from filename and defaults
        filename = os.path.basename(file_path)
        # Extract invoice number from filename (remove extension, use base name)
        invoice_number = os.path.splitext(filename)[0] or "INV-UNKNOWN"
        
        minimal_metadata = {
            "invoice_number": invoice_number,
            "issuer_name": "",
            "buyer": "",
            "date": datetime.utcnow().date().isoformat(),
            "items": [
                {
                    "description": "Auto-generated item",
                    "amount_excl_tax": 0.0,
                    "tax_rate": "10%"
                }
            ]
        }
        
        return parse_invoice_from_json_metadata(file_path, file_content, minimal_metadata)
