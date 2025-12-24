"""
SQLAlchemy models for invoice persistence.
"""

from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from .db import Base


class InvoiceResult(Base):
    """
    Model for storing invoice validation results.
    
    Fields align with batch_runner.py output and support history tracking.
    """
    __tablename__ = "invoice_results"

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    # User association
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    # Invoice identification
    invoice_number = Column(String(128), nullable=False, index=True)
    batch_id = Column(String(36), nullable=True, index=True)  # UUID as string

    # Validation status
    status = Column(String(16), nullable=False, index=True)  # "pass" or "fail"
    issues_count = Column(Integer, nullable=False, default=0)

    # PDF storage
    pdf_path = Column(Text, nullable=True)  # Full path to PDF file
    pdf_hash = Column(String(64), nullable=False)  # SHA256 hash

    # Ruleset version used for validation
    ruleset_version = Column(String(32), nullable=False, default="2025-10")

    # Timestamps
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), index=True)

    def __repr__(self):
        return (
            f"<InvoiceResult(id={self.id}, invoice_number='{self.invoice_number}', "
            f"status='{self.status}', batch_id='{self.batch_id}')>"
        )

    def to_dict(self):
        """Convert model instance to dictionary."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "invoice_number": self.invoice_number,
            "batch_id": self.batch_id,
            "status": self.status,
            "issues_count": self.issues_count,
            "pdf_path": self.pdf_path,
            "pdf_hash": self.pdf_hash,
            "ruleset_version": self.ruleset_version,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def insert_invoice(
    invoice_number: str,
    status: str,
    issues_count: int,
    pdf_path: str | None,
    pdf_hash: str,
    user_id: int,
    ruleset_version: str = "2025-10",
    batch_id: str | None = None,
) -> InvoiceResult:
    """
    Insert a new invoice result into the database.
    
    Args:
        invoice_number: Invoice identifier.
        status: Validation status ("pass" or "fail").
        issues_count: Number of validation issues found.
        pdf_path: Path to generated PDF (None if failed).
        pdf_hash: SHA256 hash of PDF file.
        user_id: ID of the user who created this invoice.
        ruleset_version: Version of rules used for validation.
        batch_id: Optional batch identifier (UUID).
        
    Returns:
        InvoiceResult: The created database record.
        
    Raises:
        ValueError: If DATABASE_URL is not configured.
        Exception: Database errors (connection, constraint violations, etc.).
    """
    from .db import get_session

    session = get_session()
    try:
        invoice = InvoiceResult(
            invoice_number=invoice_number,
            user_id=user_id,
            batch_id=batch_id,
            status=status,
            issues_count=issues_count,
            pdf_path=pdf_path,
            pdf_hash=pdf_hash,
            ruleset_version=ruleset_version,
        )
        session.add(invoice)
        session.commit()
        session.refresh(invoice)
        return invoice
    except Exception as e:
        session.rollback()
        raise
    finally:
        session.close()

