"""Authentication helpers: password hashing, JWT access tokens, current user."""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import get_db
from app.models import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a plaintext password with bcrypt.

    Args:
        password: Raw password string.

    Returns:
        Bcrypt hash suitable for storage.
    """
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Args:
        plain: Candidate plaintext password.
        hashed: Stored bcrypt hash.

    Returns:
        ``True`` if the password matches.
    """
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, organization_id: str) -> str:
    """Create a signed JWT access token for a user within an organization.

    Args:
        subject: User id placed in the ``sub`` claim.
        organization_id: Tenant id placed in the ``org`` claim.

    Returns:
        Encoded JWT string.
    """
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "org": organization_id, "exp": expire}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    """Resolve the authenticated user from a Bearer JWT.

    Args:
        token: OAuth2 bearer access token.
        db: Database session.

    Returns:
        Loaded ``User`` row.

    Raises:
        HTTPException: If the token is invalid or the user no longer exists.
    """
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc
    user = db.get(User, user_id)
    if user is None:
        raise credentials_exception
    return user
