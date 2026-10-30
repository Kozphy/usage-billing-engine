from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())



class InvoiceStatus(str, enum.Enum):
    draft = "draft"
    open = "open"
    paid = "paid"
    void = "void"
    uncollectible = "uncollectible"
    finalized = "finalized"  # immutable accounting snapshot; payment may follow


class OutboxStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    done = "done"
    failed = "failed"  # terminal after max attempts; replay is explicit


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    users: Mapped[list[User]] = relationship(back_populates="organization")
    customers: Mapped[list[Customer]] = relationship(back_populates="organization")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("organization_id", "email", name="uq_user_org_email"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped[Organization] = relationship(back_populates="users")


class Customer(Base):
    __tablename__ = "customers"
    __table_args__ = (UniqueConstraint("organization_id", "external_ref", name="uq_customer_ext"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    organization: Mapped[Organization] = relationship(back_populates="customers")
    subscriptions: Mapped[list[Subscription]] = relationship(back_populates="customer")


class Metric(Base):
    __tablename__ = "metrics"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_metric_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), default="unit")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PricingPlan(Base):
    __tablename__ = "pricing_plans"
    __table_args__ = (UniqueConstraint("organization_id", "code", name="uq_plan_code"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    versions: Mapped[list[PricingVersion]] = relationship(back_populates="plan")


class PricingVersion(Base):
    __tablename__ = "pricing_versions"
    __table_args__ = (UniqueConstraint("plan_id", "version", name="uq_plan_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    plan_id: Mapped[str] = mapped_column(ForeignKey("pricing_plans.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    base_fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    plan: Mapped[PricingPlan] = relationship(back_populates="versions")
    components: Mapped[list[PricingComponent]] = relationship(back_populates="version")


class PricingComponent(Base):
    __tablename__ = "pricing_components"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    pricing_version_id: Mapped[str] = mapped_column(ForeignKey("pricing_versions.id"), nullable=False)
    metric_id: Mapped[str] = mapped_column(ForeignKey("metrics.id"), nullable=False)
    # flat_per_unit | tiered
    model: Mapped[str] = mapped_column(String(32), default="flat_per_unit")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    # JSON-ish text: [{"up_to":"1000","unit_price":"0.0100"},{"up_to":null,"unit_price":"0.0080"}]
    tiers_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    version: Mapped[PricingVersion] = relationship(back_populates="components")
    metric: Mapped[Metric] = relationship()


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(ForeignKey("pricing_plans.id"), nullable=False)
    pricing_version_id: Mapped[str] = mapped_column(ForeignKey("pricing_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    customer: Mapped[Customer] = relationship(back_populates="subscriptions")


class UsageEvent(Base):
    __tablename__ = "usage_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "event_id", name="uq_usage_event_id"),
        Index("ix_usage_customer_metric_ts", "customer_id", "metric_id", "occurred_at"),
        Index("ix_usage_correlation", "correlation_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    metric_id: Mapped[str] = mapped_column(ForeignKey("metrics.id"), nullable=False)
    event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Server-assigned receive time (distinct from client occurred_at).
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default=new_id)
    properties_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    # pending | applied | late | discarded
    status: Mapped[str] = mapped_column(String(32), default="pending")


class UsageAggregate(Base):
    __tablename__ = "usage_aggregates"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "customer_id",
            "metric_id",
            "period_start",
            "period_end",
            name="uq_usage_agg",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    metric_id: Mapped[str] = mapped_column(ForeignKey("metrics.id"), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 6), nullable=False, default=Decimal("0"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (
        UniqueConstraint("organization_id", "number", name="uq_invoice_number"),
        UniqueConstraint(
            "organization_id",
            "customer_id",
            "period_start",
            "period_end",
            name="uq_invoice_period",
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    subscription_id: Mapped[str | None] = mapped_column(ForeignKey("subscriptions.id"), nullable=True)
    pricing_version_id: Mapped[str] = mapped_column(ForeignKey("pricing_versions.id"), nullable=False)
    number: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[InvoiceStatus] = mapped_column(Enum(InvoiceStatus), default=InvoiceStatus.draft)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    # Tax extension point: always zero in this build; never silently invent tax.
    tax_total: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    provider_invoice_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    lines: Mapped[list[InvoiceLine]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    adjustments: Mapped[list["InvoiceAdjustment"]] = relationship(back_populates="invoice")


class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    metric_id: Mapped[str | None] = mapped_column(ForeignKey("metrics.id"), nullable=True)
    pricing_version_id: Mapped[str | None] = mapped_column(
        ForeignKey("pricing_versions.id"), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(24, 6), default=Decimal("0"))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), default=Decimal("0"))
    # Traceability: event ids contributing to this line (JSON array of strings).
    source_event_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice: Mapped[Invoice] = relationship(back_populates="lines")


class InvoiceAdjustment(Base):
    """Late usage after finalization — never mutates the finalized invoice totals."""

    __tablename__ = "invoice_adjustments"
    __table_args__ = (
        UniqueConstraint("organization_id", "usage_event_id", name="uq_adjustment_event"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    usage_event_id: Mapped[str] = mapped_column(ForeignKey("usage_events.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), default="late_usage")
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default=new_id)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    invoice: Mapped[Invoice] = relationship(back_populates="adjustments")


class PaymentAttempt(Base):
    """Payment status is intentionally separate from invoice calculation totals."""

    __tablename__ = "payment_attempts"
    __table_args__ = (UniqueConstraint("organization_id", "idempotency_key", name="uq_pay_idem"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_payment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    # pending | succeeded | failed | timed_out
    status: Mapped[str] = mapped_column(String(32), default="pending")
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(64), nullable=False, default=new_id)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    reason: Mapped[str] = mapped_column(String(500), default="")
    provider_refund_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "provider", "provider_event_id", name="uq_webhook_event"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OutboxMessage(Base):
    __tablename__ = "outbox_messages"
    __table_args__ = (Index("ix_outbox_status_created", "status", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    topic: Mapped[str] = mapped_column(String(64), nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(Enum(OutboxStatus), default=OutboxStatus.pending)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, default=5)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    locked_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_org_created", "organization_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    details_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ShadowInvoice(Base):
    """Parallel invoice computed under an alternate pricing version (migration rehearsal)."""

    __tablename__ = "shadow_invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    source_invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False)
    pricing_version_id: Mapped[str] = mapped_column(ForeignKey("pricing_versions.id"), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    delta: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    # match | expected_delta | unexpected_delta
    classification: Mapped[str] = mapped_column(String(32), default="match")
    cutover_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PricingCutover(Base):
    """Record of controlled cutover / rollback decisions (does not rewrite finalized invoices)."""

    __tablename__ = "pricing_cutovers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    plan_id: Mapped[str] = mapped_column(ForeignKey("pricing_plans.id"), nullable=False)
    from_version_id: Mapped[str] = mapped_column(ForeignKey("pricing_versions.id"), nullable=False)
    to_version_id: Mapped[str] = mapped_column(ForeignKey("pricing_versions.id"), nullable=False)
    # cutover | rollback | blocked
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    shadow_report_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
