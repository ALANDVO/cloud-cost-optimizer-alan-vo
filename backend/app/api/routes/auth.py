# Authentication routes
from fastapi import APIRouter, Request, Response, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from backend.app.core.database import get_db_session
from backend.app.core.auth import (
    get_current_user,
    require_roles,
    set_auth_cookies,
    clear_auth_cookies,
    create_csrf_token,
    verify_csrf,
    is_demo_mode,
)
from backend.app.models.user import User
from backend.app.core.config import get_settings
import httpx
import secrets
import urllib.parse

router = APIRouter(tags=["auth"])
settings = get_settings()

# In-memory state storage for PKCE (use Redis in production)
_oauth_states = {}


@router.get("/api/auth/me")
def get_current_user_info(user: User = Depends(get_current_user)):
    """Get current user info."""
    return user.to_dict()


@router.get("/api/auth/csrf")
def get_csrf_token(response: Response, user: User = Depends(get_current_user)):
    """Get CSRF token for authenticated user."""
    csrf_token = create_csrf_token()
    # Update cookie with new CSRF token
    is_secure = not is_demo_mode()
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=is_secure,
        samesite="lax",
        max_age=settings.JWT_EXPIRE_MINUTES * 60,
        path="/",
    )
    return {"csrf_token": csrf_token}


@router.post("/api/auth/logout")
def logout(response: Response, user: User = Depends(get_current_user)):
    """Logout and clear session."""
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


# OIDC/OAuth2 routes (production mode)
@router.get("/api/auth/login")
def login(request: Request):
    """Initiate OIDC login flow."""
    if is_demo_mode():
        # Demo mode: create local session
        db = next(get_db_session())
        try:
            user = db.query(User).filter(User.sub == "demo-user").first()
            if not user:
                user = User(sub="demo-user", email="demo@localhost", name="Demo User", roles="viewer,operator,admin")
                db.add(user)
                db.commit()
                db.refresh(user)
            csrf_token = create_csrf_token()
            response = RedirectResponse(url="/")
            set_auth_cookies(response, user, csrf_token)
            return response
        finally:
            db.close()

    # Production OIDC flow
    if not settings.OIDC_ISSUER_URL or not settings.OIDC_CLIENT_ID:
        raise HTTPException(status_code=503, detail="OIDC not configured")

    # Generate PKCE parameters
    code_verifier = secrets.token_urlsafe(32)
    code_challenge = secrets.token_urlsafe(32)  # Simplified; use S256 in production
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)

    _oauth_states[state] = {
        "code_verifier": code_verifier,
        "code_challenge": code_challenge,
        "nonce": nonce,
    }

    # Build authorization URL
    auth_url = f"{settings.OIDC_ISSUER_URL}/protocol/openid-connect/auth"
    params = {
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "state": state,
        "nonce": nonce,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return RedirectResponse(url=f"{auth_url}?{urllib.parse.urlencode(params)}")


@router.get("/api/auth/callback")
def oidc_callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle OIDC callback."""
    if is_demo_mode():
        return RedirectResponse(url="/")

    if error:
        raise HTTPException(status_code=400, detail=f"OIDC error: {error}")

    if not code or not state:
        raise HTTPException(status_code=400, detail="Missing code or state")

    stored = _oauth_states.pop(state, None)
    if not stored:
        raise HTTPException(status_code=400, detail="Invalid or expired state")

    # Exchange code for tokens
    token_url = f"{settings.OIDC_ISSUER_URL}/protocol/openid-connect/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "client_id": settings.OIDC_CLIENT_ID,
        "client_secret": settings.OIDC_CLIENT_SECRET,
        "code_verifier": stored["code_verifier"],
    }

    with httpx.Client(timeout=30) as client:
        resp = client.post(token_url, data=data)
        resp.raise_for_status()
        tokens = resp.json()

    # Validate ID token
    id_token = tokens.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="No ID token in response")

    from jose import jwt
    try:
        # In production, fetch JWKS from issuer and validate properly
        payload = jwt.decode(
            id_token,
            settings.JWT_SECRET,  # Placeholder; use JWKS in production
            algorithms=["RS256", "HS256"],
            audience=settings.OIDC_CLIENT_ID,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid ID token: {e}")

    # Verify nonce
    if payload.get("nonce") != stored["nonce"]:
        raise HTTPException(status_code=401, detail="Nonce mismatch")

    # Get or create user
    sub = payload.get("sub")
    email = payload.get("email", "")
    name = payload.get("name", payload.get("preferred_username", ""))

    db = next(get_db_session())
    try:
        user = db.query(User).filter(User.sub == sub).first()
        if not user:
            user = User(sub=sub, email=email, name=name, roles="viewer")
            db.add(user)
        else:
            user.email = email
            user.name = name
            user.last_login = datetime.utcnow()
        db.commit()
        db.refresh(user)

        csrf_token = create_csrf_token()
        response = RedirectResponse(url="/")
        set_auth_cookies(response, user, csrf_token)
        return response
    finally:
        db.close()


@router.get("/api/auth/saml/login")
def saml_login():
    """Initiate SAML login (via Keycloak broker)."""
    if is_demo_mode():
        return RedirectResponse(url="/api/auth/login")

    if not settings.OIDC_ISSUER_URL:
        raise HTTPException(status_code=503, detail="SAML broker not configured")

    # Redirect to Keycloak with SAML IdP hint
    auth_url = f"{settings.OIDC_ISSUER_URL}/protocol/openid-connect/auth"
    params = {
        "client_id": settings.OIDC_CLIENT_ID,
        "redirect_uri": settings.OIDC_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid profile email",
        "kc_idp_hint": "saml",  # Keycloak identity broker hint
    }
    return RedirectResponse(url=f"{auth_url}?{urllib.parse.urlencode(params)}")


from datetime import datetime