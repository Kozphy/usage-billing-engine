"""Pydantic request/response schemas for the billing API."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.money import normalize_currency


class MoneyStr(BaseModel):
    """Base model enabling ORM attribute reading for money-related responses."""

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    organization_name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    organization_id: str
    user_id: str


def _validate_currency(value: Any) -> str:
    """Reject unknown ISO 4217 codes before they reach the ledger.

    Args:
        value: Raw currency field.

    Returns:
        Canonical uppercase code.

    Raises:
        ValueError: If ``value`` is not a string.
        UnknownCurrencyError: If the code is not in the minor-unit table.
    """
    if not isinstance(value, str):
        raise ValueError("currency must be an ISO 4217 alphabetic code")
    return normalize_currency(value)


class CustomerCreate(BaseModel):
    name: str
    external_ref: str
    currency: str = "USD"

    @field_validator("currency", mode="before")
    @classmethod
    def known_currency(cls, value: Any) -> str:
        return _validate_currency(value)


class CustomerOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    external_ref: str
    currency: str


class MetricCreate(BaseModel):
    code: str
    name: str
    unit: str = "unit"


class MetricOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    unit: str


class Tier(BaseModel):
    up_to: Decimal | None = None
    unit_price: Decimal

    @field_validator("unit_price", mode="before")
    @classmethod
    def no_float_price(cls, v: Any) -> Any:
        if isinstance(v, float):
            raise TypeError("float unit_price rejected")
        return v


class ComponentIn(BaseModel):
    metric_code: str
    model: str = "flat_per_unit"
    unit_price: Decimal = Decimal("0")
    tiers: list[Tier] | None = None

    @field_validator("unit_price", mode="before")
    @classmethod
    def no_float_unit(cls, v: Any) -> Any:
        if isinstance(v, float):
            raise TypeError("float unit_price rejected")
        return v


class PlanCreate(BaseModel):
    code: str
    name: str
    currency: str = "USD"
    base_fee: Decimal = Decimal("0")
    components: list[ComponentIn]
    effective_from: datetime | None = None

    @field_validator("currency", mode="before")
    @classmethod
    def known_currency(cls, value: Any) -> str:
        return _validate_currency(value)

    @field_validator("base_fee", mode="before")
    @classmethod
    def no_float_base(cls, v: Any) -> Any:
        if isinstance(v, float):
            raise TypeError("float base_fee rejected")
        return v


class PlanVersionCreate(BaseModel):
    base_fee: Decimal = Decimal("0")
    components: list[ComponentIn]
    effective_from: datetime | None = None

    @field_validator("base_fee", mode="before")
    @classmethod
    def no_float_base(cls, v: Any) -> Any:
        if isinstance(v, float):
            raise TypeError("float base_fee rejected")
        return v


class SubscriptionCreate(BaseModel):
    customer_id: str
    plan_code: str
    pricing_version: int | None = None


class UsageEventIn(BaseModel):
    event_id: str = Field(min_length=1, max_length=128)
    customer_external_ref: str = Field(min_length=1, max_length=200)
    metric_code: str = Field(min_length=1, max_length=64)
    quantity: Decimal
    occurred_at: datetime
    schema_version: int = Field(default=1, ge=1, le=100)
    properties: dict[str, Any] | None = None

    @field_validator("quantity", mode="before")
    @classmethod
    def no_float_qty(cls, v: Any) -> Any:
        if isinstance(v, float):
            raise TypeError("float quantity rejected; pass string or Decimal")
        return v

    @field_validator("occurred_at")
    @classmethod
    def require_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None:
            raise ValueError("occurred_at must be timezone-aware (prefer UTC)")
        return v


class UsageBatchIn(BaseModel):
    events: list[UsageEventIn]


class UsageEventOut(BaseModel):
    id: str
    event_id: str
    status: str
    duplicate: bool = False
    conflict: bool = False
    received_at: datetime | None = None
    correlation_id: str | None = None
    schema_version: int | None = None


class InvoiceGenerateIn(BaseModel):
    customer_id: str
    period_start: date
    period_end: date
    subscription_id: str | None = None
    finalize: bool = True


class InvoiceLineOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal
    pricing_version_id: str | None = None
    source_event_ids: list[str] | None = None


class InvoiceAdjustmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    usage_event_id: str
    amount: Decimal
    reason: str
    correlation_id: str


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    number: str
    status: str
    currency: str
    period_start: date
    period_end: date
    subtotal: Decimal
    tax_total: Decimal = Decimal("0")
    total: Decimal
    correlation_id: str | None = None
    finalized_at: datetime | None = None
    lines: list[InvoiceLineOut]
    adjustments: list[InvoiceAdjustmentOut] = []


class ChargeIn(BaseModel):
    idempotency_key: str


class RefundIn(BaseModel):
    amount: Decimal
    reason: str = ""

    @field_validator("amount", mode="before")
    @classmethod
    def no_float_amt(cls, v: Any) -> Any:
        if isinstance(v, float):
            raise TypeError("float amount rejected")
        return v


class ShadowCompareIn(BaseModel):
    invoice_id: str
    alternate_pricing_version_id: str
    # Optional absolute expected delta for this invoice (marks expected_delta).
    expected_delta: Decimal | None = None

    @field_validator("expected_delta", mode="before")
    @classmethod
    def no_float_delta(cls, v: Any) -> Any:
        if isinstance(v, float):
            raise TypeError("float expected_delta rejected")
        return v


class CutoverIn(BaseModel):
    plan_code: str
    to_pricing_version_id: str
    # Require all shadows for listed invoices to allow cutover.
    invoice_ids: list[str]


class ReportSummaryOut(BaseModel):
    customers: int
    usage_events: int
    invoices_open: int
    invoices_paid: int
    revenue_paid: Decimal
    revenue_open: Decimal
