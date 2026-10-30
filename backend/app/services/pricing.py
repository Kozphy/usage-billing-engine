"""Versioned pricing plans and quantity pricing calculators."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.money import money, usage_qty
from app.models import Metric, PricingComponent, PricingPlan, PricingVersion
from app.schemas import ComponentIn, PlanCreate, PlanVersionCreate
from app.services import audit


def _tiers_to_json(tiers: list | None) -> str | None:
    """Serialize tier definitions to JSON text for storage.

    Args:
        tiers: Optional list of ``Tier`` models.

    Returns:
        JSON string or ``None`` when no tiers are provided.
    """
    if not tiers:
        return None
    payload = [
        {"up_to": None if t.up_to is None else str(t.up_to), "unit_price": str(money(t.unit_price))}
        for t in tiers
    ]
    return json.dumps(payload)


def create_plan(
    db: Session,
    *,
    organization_id: str,
    body: PlanCreate,
    actor_user_id: str | None = None,
) -> PricingPlan:
    """Create a pricing plan with an initial version and components.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.
        body: Plan create payload.
        actor_user_id: Optional authenticated user id for audit.

    Returns:
        Newly created ``PricingPlan`` including version 1.
    """
    plan = PricingPlan(
        organization_id=organization_id,
        code=body.code,
        name=body.name,
        currency=body.currency,
        active=True,
    )
    db.add(plan)
    db.flush()
    effective = body.effective_from or datetime.now(timezone.utc)
    version = PricingVersion(
        plan_id=plan.id,
        version=1,
        effective_from=effective,
        base_fee=money(body.base_fee),
    )
    db.add(version)
    db.flush()
    _attach_components(db, organization_id, version, body.components)
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="pricing.plan_create",
        entity_type="pricing_plan",
        entity_id=plan.id,
        details={"code": plan.code, "version": 1},
    )
    return plan


def add_version(
    db: Session,
    *,
    organization_id: str,
    plan_code: str,
    body: PlanVersionCreate,
    actor_user_id: str | None = None,
) -> PricingVersion:
    """Append a new pricing version and close the prior effective interval.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id.
        plan_code: Existing plan code.
        body: New version payload.
        actor_user_id: Optional authenticated user id for audit.

    Returns:
        Newly created ``PricingVersion``.

    Raises:
        ValueError: If the plan is not found.
    """
    plan = db.scalar(
        select(PricingPlan).where(
            PricingPlan.organization_id == organization_id,
            PricingPlan.code == plan_code,
        )
    )
    if plan is None:
        raise ValueError("plan not found")
    versions = sorted(plan.versions, key=lambda v: v.version)
    next_version = (versions[-1].version + 1) if versions else 1
    effective = body.effective_from or datetime.now(timezone.utc)
    if versions:
        versions[-1].effective_to = effective
    version = PricingVersion(
        plan_id=plan.id,
        version=next_version,
        effective_from=effective,
        base_fee=money(body.base_fee),
    )
    db.add(version)
    db.flush()
    _attach_components(db, organization_id, version, body.components)
    audit.write_audit(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
        action="pricing.version_create",
        entity_type="pricing_version",
        entity_id=version.id,
        details={"plan_code": plan_code, "version": next_version},
    )
    return version


def _attach_components(
    db: Session,
    organization_id: str,
    version: PricingVersion,
    components: list[ComponentIn],
) -> None:
    """Attach pricing components to a version.

    Args:
        db: Active SQLAlchemy session.
        organization_id: Tenant id used to resolve metrics.
        version: Target pricing version.
        components: Component definitions to attach.

    Raises:
        ValueError: If a referenced metric code is unknown.
    """
    for component in components:
        metric = db.scalar(
            select(Metric).where(
                Metric.organization_id == organization_id,
                Metric.code == component.metric_code,
            )
        )
        if metric is None:
            raise ValueError(f"unknown metric {component.metric_code}")
        db.add(
            PricingComponent(
                pricing_version_id=version.id,
                metric_id=metric.id,
                model=component.model,
                unit_price=money(component.unit_price),
                tiers_json=_tiers_to_json(component.tiers),
            )
        )


def get_version(db: Session, version_id: str) -> PricingVersion:
    """Load a pricing version with components eagerly loaded.

    Args:
        db: Active SQLAlchemy session.
        version_id: Pricing version primary key.

    Returns:
        ``PricingVersion`` including ``components``.

    Raises:
        ValueError: If the version does not exist.
    """
    version = db.scalar(
        select(PricingVersion)
        .where(PricingVersion.id == version_id)
        .options(selectinload(PricingVersion.components))
    )
    if version is None:
        raise ValueError("pricing version not found")
    return version


def price_quantity(component: PricingComponent, quantity: Decimal) -> tuple[Decimal, Decimal]:
    """Price a usage quantity under a flat or tiered component.

    Args:
        component: Pricing component definition.
        quantity: Usage quantity to price.

    Returns:
        Tuple of ``(effective_unit_price, line_amount)``.

    Raises:
        ValueError: Unknown model, missing tiers, or quantity beyond tiers.
    """
    qty = usage_qty(quantity)
    if component.model == "flat_per_unit":
        unit = money(component.unit_price)
        return unit, money(unit * qty)
    if component.model == "tiered":
        if not component.tiers_json:
            raise ValueError("tiered component missing tiers")
        tiers = json.loads(component.tiers_json)
        remaining = qty
        previous_up_to = Decimal("0")
        total = Decimal("0")
        for tier in tiers:
            up_to = None if tier["up_to"] is None else Decimal(tier["up_to"])
            unit = money(tier["unit_price"])
            if up_to is None:
                band = remaining
            else:
                band_cap = usage_qty(up_to - previous_up_to)
                band = min(remaining, band_cap)
                previous_up_to = up_to
            if band > 0:
                total = money(total + money(unit * band))
                remaining = usage_qty(remaining - band)
            if remaining == 0:
                break
        if remaining > 0:
            raise ValueError("quantity exceeds defined tiers")
        # effective average for display
        avg = money(total / qty) if qty else money(0)
        return avg, total
    raise ValueError(f"unknown pricing model {component.model}")
