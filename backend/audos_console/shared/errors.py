# errors.py
class ValidationError(Exception):
    """Raised when invoice field validation fails."""
    def __init__(self, invoice_number, details=None):
        super().__init__(f"Validation failed for {invoice_number}")
        self.invoice_number = invoice_number
        self.details = details or {}

class PDFGenerationError(Exception):
    """Raised when PDF creation fails."""
    pass

class StorageError(Exception):
    """Raised when saving or archiving outputs fails."""
    pass

class BatchProcessingError(Exception):
    """Raised when the batch runner itself encounters a fatal issue."""
    pass
