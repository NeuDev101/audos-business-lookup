"""
Shared validation helpers for invoice validation.
Used by both manual entry and file upload paths.
"""
from typing import Dict, List, Any, Optional


def validate_totals_and_tax(
    items: List[Dict[str, Any]],
    totals: Optional[Dict[str, float]] = None,
    tolerance: float = 0.01
) -> List[str]:
    """
    Validate that computed totals and tax match expected values.
    
    Args:
        items: List of invoice items with amount_excl_tax and tax_rate
        totals: Optional dict with 'subtotal', 'taxTotal', 'grandTotal'
        tolerance: Allowed difference for floating point comparisons
    
    Returns:
        List of error messages (empty if validation passes)
    """
    errors = []
    
    # Compute totals from items
    computed_subtotal = 0.0
    computed_tax_total = 0.0
    
    for item in items:
        amount_excl_tax = float(item.get("amount_excl_tax", 0))
        computed_subtotal += amount_excl_tax
        
        tax_rate_str = str(item.get("tax_rate", "0%")).strip()
        # Handle tax_rate as "10%" or numeric
        if tax_rate_str.endswith("%"):
            tax_rate_num = float(tax_rate_str.replace("%", ""))
        else:
            try:
                tax_rate_num = float(tax_rate_str)
            except (ValueError, TypeError):
                tax_rate_num = 0.0
        
        computed_tax_total += (amount_excl_tax * tax_rate_num) / 100.0
    
    computed_grand_total = computed_subtotal + computed_tax_total
    
    # Verify totals if provided
    if totals:
        expected_subtotal = totals.get("subtotal")
        expected_tax_total = totals.get("taxTotal")
        expected_grand_total = totals.get("grandTotal")
        
        if expected_subtotal is not None:
            diff = abs(float(expected_subtotal) - computed_subtotal)
            if diff > tolerance:
                errors.append(
                    f"Subtotal mismatch: expected {expected_subtotal}, computed {computed_subtotal:.2f}"
                )
        
        if expected_tax_total is not None:
            diff = abs(float(expected_tax_total) - computed_tax_total)
            if diff > tolerance:
                errors.append(
                    f"Tax total mismatch: expected {expected_tax_total}, computed {computed_tax_total:.2f}"
                )
        
        if expected_grand_total is not None:
            diff = abs(float(expected_grand_total) - computed_grand_total)
            if diff > tolerance:
                errors.append(
                    f"Grand total mismatch: expected {expected_grand_total}, computed {computed_grand_total:.2f}"
                )
    
    return errors


def compute_totals_from_items(items: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Compute subtotal, tax total, and grand total from items.
    
    Args:
        items: List of invoice items with amount_excl_tax and tax_rate
    
    Returns:
        Dict with 'subtotal', 'taxTotal', 'grandTotal'
    """
    subtotal = 0.0
    tax_total = 0.0
    
    for item in items:
        amount_excl_tax = float(item.get("amount_excl_tax", 0))
        subtotal += amount_excl_tax
        
        tax_rate_str = str(item.get("tax_rate", "0%")).strip()
        if tax_rate_str.endswith("%"):
            tax_rate_num = float(tax_rate_str.replace("%", ""))
        else:
            try:
                tax_rate_num = float(tax_rate_str)
            except (ValueError, TypeError):
                tax_rate_num = 0.0
        
        tax_total += (amount_excl_tax * tax_rate_num) / 100.0
    
    return {
        "subtotal": subtotal,
        "taxTotal": tax_total,
        "grandTotal": subtotal + tax_total,
    }

