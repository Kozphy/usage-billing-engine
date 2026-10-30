"""Authentication routes: register organization/user and login."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Organization, User
from app.schemas import RegisterRequest, TokenResponse
from app.security import create_access_token, hash_password, verify_password
from app.services import audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse)
def register(body: RegisterRequest, db: Annotated[Session, Depends(get_db)]) -> TokenResponse:
    """Register a new organization and primary user, returning a JWT.

    Args:
        body: Registration payload with org name, email, and password.
        db: Database session.

    Returns:
        Access token plus organization/user ids.

    Raises:
        HTTPException: If the email is already registered.
    """
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing:
        raise HTTPException(status_code=400, detail="email already registered")
    org = Organization(name=body.organization_name)
    db.add(org)
    db.flush()
    user = User(
        organization_id=org.id,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    audit.write_audit(
        db,
        organization_id=org.id,
        action="auth.register",
        entity_type="organization",
        entity_id=org.id,
        details={"email": body.email},
    )
    db.commit()
    token = create_access_token(user.id, org.id)
    return TokenResponse(
        access_token=token,
        organization_id=org.id,
        user_id=user.id,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    """Authenticate with email/password and return a JWT.

    Args:
        form: OAuth2 password form (username = email).
        db: Database session.

    Returns:
        Access token plus organization/user ids.

    Raises:
        HTTPException: If credentials are invalid.
    """
    user = db.scalar(select(User).where(User.email == form.username))
    if user is None or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid credentials")
    token = create_access_token(user.id, user.organization_id)
    return TokenResponse(
        access_token=token,
        organization_id=user.organization_id,
        user_id=user.id,
    )
