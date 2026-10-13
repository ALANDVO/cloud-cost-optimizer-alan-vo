# User model for authentication
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    sub = Column(String(256), unique=True, nullable=False, index=True)  # OIDC subject
    email = Column(String(256), unique=True, nullable=False, index=True)
    name = Column(String(256), nullable=True)
    roles = Column(String(512), default="viewer")  # comma-separated: viewer,operator,admin
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    def get_roles(self) -> list[str]:
        return [r.strip() for r in self.roles.split(",") if r.strip()]

    def has_role(self, role: str) -> bool:
        return role in self.get_roles()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "sub": self.sub,
            "email": self.email,
            "name": self.name,
            "roles": self.get_roles(),
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login": self.last_login.isoformat() if self.last_login else None,
        }