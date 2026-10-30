from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Customer, Metric, PricingPlan, Subscription, User
from app.schemas import (
    CustomerCreate,
    CustomerOut,
    MetricCreate,
    MetricOut,
    PlanCreate,
    PlanVersionCreate,
    SubscriptionCreate,
)
from app.security import get_current_user
from app.services import pricing

router = APIRouter(tags=["catalog"])


@router.post("/customers", response_model=CustomerOut)
def create_customer(
    body: CustomerCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Customer:
    row = Customer(
        organization_id=user.organization_id,
        name=body.name,
        external_ref=body.external_ref,
        currency=body.currency,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/customers", response_model=list[CustomerOut])
def list_customers(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[Customer]:
    return list(
        db.scalars(select(Customer).where(Customer.organization_id == user.organization_id)).all()
    )


@router.post("/metrics", response_model=MetricOut)
def create_metric(
    body: MetricCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> Metric:
    row = Metric(
        organization_id=user.organization_id,
        code=body.code,
        name=body.name,
        unit=body.unit,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/metrics", response_model=list[MetricOut])
def list_metrics(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[Metric]:
    return list(
        db.scalars(select(Metric).where(Metric.organization_id == user.organization_id)).all()
    )


@router.post("/plans")
def create_plan(
    body: PlanCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        plan = pricing.create_plan(
            db,
            organization_id=user.organization_id,
            body=body,
            actor_user_id=user.id,
        )
        db.commit()
        db.refresh(plan)
        return {
            "id": plan.id,
            "code": plan.code,
            "versions": [{"id": v.id, "version": v.version} for v in plan.versions],
        }
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/plans/{plan_code}/versions")
def create_plan_version(
    plan_code: str,
    body: PlanVersionCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    try:
        version = pricing.add_version(
            db,
            organization_id=user.organization_id,
            plan_code=plan_code,
            body=body,
            actor_user_id=user.id,
        )
        db.commit()
        return {"id": version.id, "version": version.version, "plan_id": version.plan_id}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/plans")
def list_plans(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    plans = db.scalars(
        select(PricingPlan).where(PricingPlan.organization_id == user.organization_id)
    ).all()
    return [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "versions": [
                {"id": v.id, "version": v.version, "base_fee": str(v.base_fee)}
                for v in sorted(p.versions, key=lambda x: x.version)
            ],
        }
        for p in plans
    ]


@router.post("/subscriptions")
def create_subscription(
    body: SubscriptionCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    plan = db.scalar(
        select(PricingPlan).where(
            PricingPlan.organization_id == user.organization_id,
            PricingPlan.code == body.plan_code,
        )
    )
    if plan is None:
        raise HTTPException(status_code=404, detail="plan not found")
    versions = sorted(plan.versions, key=lambda v: v.version)
    if not versions:
        raise HTTPException(status_code=400, detail="plan has no versions")
    if body.pricing_version is not None:
        version = next((v for v in versions if v.version == body.pricing_version), None)
        if version is None:
            raise HTTPException(status_code=400, detail="pricing version not found")
    else:
        version = versions[-1]
    customer = db.get(Customer, body.customer_id)
    if customer is None or customer.organization_id != user.organization_id:
        raise HTTPException(status_code=404, detail="customer not found")
    sub = Subscription(
        organization_id=user.organization_id,
        customer_id=customer.id,
        plan_id=plan.id,
        pricing_version_id=version.id,
        status="active",
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return {
        "id": sub.id,
        "customer_id": sub.customer_id,
        "plan_id": sub.plan_id,
        "pricing_version_id": sub.pricing_version_id,
        "status": sub.status,
    }
