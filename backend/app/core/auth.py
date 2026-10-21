# Authentication and authorization
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import jwt, JWTError
from fastapi import Request, HTTPException, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.app.core.config import get_settings, is_demo_mode, require_production_auth
from backend.app.core.database import get_db_session
from backend.app.models.user import User
from sqlalchemy.orm import Session

settings = get_settings()
security = HTTPBearer(auto_error=False)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_csrf_token() -> str:
    """Generate CSRF token."""
    return secrets.token_urlsafe(32)


def verify_token(token: str) -> Optional[dict]:
    """Verify JWT token and return payload."""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db_session),
) -> User:
    """Get current authenticated user from session cookie or bearer token."""
    # Demo mode: return a default demo user
    if is_demo_mode():
        demo_user = db.query(User).filter(User.sub == "demo-user").first()
        if not demo_user:
            demo_user = User(
                sub="demo-user",
                email="demo@localhost",
                name="Demo User",
                roles="viewer,operator,admin",
                is_active=True,
            )
            db.add(demo_user)
            db.commit()
            db.refresh(demo_user)
        return demo_user

    # Production mode: require authentication
    token = None
    # Try session cookie first
    if settings.SESSION_COOKIE_NAME in request.cookies:
        token = request.cookies[settings.SESSION_COOKIE_NAME]
    # Fallback to Authorization header
    elif credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    payload = verify_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token payload")

    user = db.query(User).filter(User.sub == sub).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


def require_roles(*required_roles: str):
    """Dependency factory for role-based access control."""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        for role in required_roles:
            if user.has_role(role):
                return user
        raise HTTPException(status_code=403, detail=f"Requires one of roles: {required_roles}")
    return role_checker


def set_auth_cookies(response: Response, user: User, csrf_token: str) -> None:
    """Set authentication cookies (HttpOnly, Secure, SameSite)."""
    access_token = create_access_token({"sub": user.sub, "email": user.email, "roles": user.roles})
    is_secure = not is_demo_mode()  # Secure in production
    response.set_cookie(
        key=settings.SESSION_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=is_secure,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,  # JavaScript needs to read this for CSRF header
        secure=is_secure,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )


def clear_auth_cookies(response: Response) -> None:
    """Clear authentication cookies."""
    is_secure = not is_demo_mode()
    response.delete_cookie(settings.SESSION_COOKIE_NAME, path="/", secure=is_secure, samesite="lax")
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/", secure=is_secure, samesite="lax")


def verify_csrf(request: Request) -> None:
    """Verify CSRF token for state-changing operations."""
    if is_demo_mode():
        return  # Skip CSRF in demo mode

    csrf_cookie = request.cookies.get(settings.CSRF_COOKIE_NAME)
    csrf_header = request.headers.get("X-CSRF-Token")

    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status_code=403, detail="CSRF validation failed")