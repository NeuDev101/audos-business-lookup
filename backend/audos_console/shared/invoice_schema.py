from typing import Annotated
from pydantic import BaseModel, Field, validator, constr
from datetime import date, datetime
from typing import Optional

IssuerID = Annotated[str, Field(pattern=r"^T\d{13}$", description="Registration number (starts with 'T')")]

class InvoiceSchema(BaseModel):
    invoice_number: str = Field(..., description="Unique invoice ID")
    issue_date: date = Field(default_factory=date.today)
    transaction_date: Optional[date] = None

    issuer_name: str = Field(..., description="Registered issuer name")
    issuer_id: IssuerID                      # ✅ regex pattern enforced here
    address: Optional[str] = ""
    phone: Optional[str] = ""
    email: Optional[str] = ""
    buyer_name: Optional[str] = ""

    subtotal: float = 0
    tax_rate: int = 10
    tax_amount: float = 0
    total: float = 0
    reduced_rate_flag: Optional[str] = ""
    remarks: Optional[str] = ""
    validation_status: Optional[str] = ""
    validation_message: Optional[str] = ""

    @validator("tax_amount", always=True)
    def calc_tax(cls, v, values):
        if not v and "subtotal" in values and "tax_rate" in values:
            try:
                return round(values["subtotal"] * values["tax_rate"] / 100)
            except Exception:
                return 0
        return v

    @validator("total", always=True)
    def calc_total(cls, v, values):
        if not v and "subtotal" in values and "tax_amount" in values:
            try:
                return values["subtotal"] + values["tax_amount"]
            except Exception:
                return 0
        return v

    @validator("issue_date", "transaction_date", pre=True)
    def parse_dates(cls, v):
        if not v:
            return None
        if isinstance(v, (datetime, date)):
            return v
        try:
            return datetime.strptime(v, "%Y-%m-%d").date()
        except Exception:
            return None
