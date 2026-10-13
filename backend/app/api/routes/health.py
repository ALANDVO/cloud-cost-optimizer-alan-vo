# Health check endpoint
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from backend.app.core.database import get_db_session
from backend.app.core.config import get_settings

router = APIRouter(tags=["health"])
settings = get_settings()


@router.get("/api/health")
def health_check(db: Session = Depends(get_db_session)):
    """Health check endpoint."""
    # Check database connectivity
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "database": db_status,
        "demo_mode": settings.DEMO_MODE,
    }


@router.get("/api/ready")
def readiness_check():
    """Readiness check for Kubernetes."""
    return {"ready": True}