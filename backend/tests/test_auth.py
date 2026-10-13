# Tests for authentication
import pytest
from backend.app.core.auth import (
    create_access_token,
    verify_token,
    create_csrf_token,
)
from backend.app.models.user import User
from datetime import timedelta


def test_create_access_token():
    """Test JWT token creation."""
    token = create_access_token({"sub": "test-user", "email": "test@example.com"})
    assert token is not None
    assert isinstance(token, str)
    assert len(token) > 0


def test_verify_token():
    """Test JWT token verification."""
    token = create_access_token({"sub": "test-user", "email": "test@example.com"})
    payload = verify_token(token)

    assert payload is not None
    assert payload["sub"] == "test-user"
    assert payload["email"] == "test@example.com"
    assert payload["type"] == "access"


def test_verify_invalid_token():
    """Test verification of invalid token."""
    payload = verify_token("invalid.token.string")
    assert payload is None


def test_verify_expired_token():
    """Test verification of expired token."""
    token = create_access_token({"sub": "test-user"}, expires_delta=timedelta(seconds=-1))
    payload = verify_token(token)
    assert payload is None


def test_create_csrf_token():
    """Test CSRF token generation."""
    token1 = create_csrf_token()
    token2 = create_csrf_token()

    assert token1 != token2
    assert len(token1) >= 32
    assert len(token2) >= 32


def test_user_roles(db_session):
    """Test User role handling."""
    user = User(
        sub="test-user-roles",
        email="test-roles@example.com",
        roles="viewer,operator,admin",
    )
    db_session.add(user)
    db_session.commit()

    assert user.has_role("viewer")
    assert user.has_role("operator")
    assert user.has_role("admin")
    assert not user.has_role("nonexistent")

    roles = user.get_roles()
    assert set(roles) == {"viewer", "operator", "admin"}


def test_user_to_dict(db_session):
    """Test User serialization."""
    user = User(
        sub="test-user-dict",
        email="test-dict@example.com",
        name="Test User",
        roles="viewer,operator",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    data = user.to_dict()
    assert data["sub"] == "test-user-dict"
    assert data["email"] == "test-dict@example.com"
    assert data["name"] == "Test User"
    assert "viewer" in data["roles"]
    assert "operator" in data["roles"]