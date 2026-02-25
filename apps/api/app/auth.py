"""
VOLO — Authentication & Authorization
JWT auth, password hashing, OAuth scaffolding, user management.
"""

import uuid
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

from app.config import settings

# Bearer token extractor
security = HTTPBearer(auto_error=False)


# ── Password Utilities ───────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


# ── JWT Utilities ────────────────────────────

def create_access_token(
    user_id: str,
    tenant_id: str = "volo-default",
    role: str = "member",
    expires_delta: Optional[timedelta] = None,
) -> str:
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=settings.jwt_expiry_hours))
    payload = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "iat": datetime.utcnow(),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=30)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


# ── API Key Utilities ────────────────────────

def generate_api_key() -> tuple[str, str, str]:
    """Generate a new API key. Returns (raw_key, key_hash, prefix)."""
    raw = f"volo_{secrets.token_urlsafe(32)}"
    prefix = raw[:10]
    key_hash = hashlib.sha256(raw.encode()).hexdigest()
    return raw, key_hash, prefix


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    return hashlib.sha256(raw_key.encode()).hexdigest() == stored_hash


# ── Dependency Injection ─────────────────────

class CurrentUser:
    """Represents the authenticated user from JWT or API key."""
    def __init__(self, user_id: str, tenant_id: str, role: str):
        self.user_id = user_id
        self.tenant_id = tenant_id
        self.role = role


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> CurrentUser:
    """
    Extract and validate the current user from JWT bearer token or API key.
    Falls back to a default user in development mode for convenience.
    """
    # Try Bearer token
    if credentials:
        payload = decode_token(credentials.credentials)
        return CurrentUser(
            user_id=payload["sub"],
            tenant_id=payload.get("tenant_id", "volo-default"),
            role=payload.get("role", "member"),
        )

    # Try API key from header
    api_key = request.headers.get("X-API-Key")
    if api_key and api_key.startswith("volo_"):
        # In production, look up the key hash in the database
        # For now, accept any volo_ prefixed key in development
        if settings.app_env == "development":
            return CurrentUser(
                user_id="dev-user",
                tenant_id="volo-default",
                role="owner",
            )

    # Development fallback — allow unauthenticated requests
    if settings.app_env == "development":
        return CurrentUser(
            user_id="dev-user",
            tenant_id="volo-default",
            role="owner",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_optional_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[CurrentUser]:
    """Same as get_current_user but returns None instead of raising."""
    try:
        return await get_current_user(request, credentials)
    except HTTPException:
        return None


def require_role(*roles: str):
    """Dependency factory that requires a specific role."""
    async def checker(user: CurrentUser = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' does not have permission. Required: {', '.join(roles)}",
            )
        return user
    return checker
