# Tests for analysis models
import pytest
from datetime import datetime, timezone
from backend.app.models.analysis import (
    Analysis, Recommendation, OptimizationPlan,
    CloudProvider, AnalysisStatus, RecommendationType
)
from backend.app.models.user import User


def test_analysis_model_creation(db_session):
    """Test creating an Analysis record."""
    analysis = Analysis(
        cloud_provider=CloudProvider.AWS,
        region="us-east-1",
        days_analyzed=30,
        status=AnalysisStatus.PENDING,
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    assert analysis.id is not None
    assert analysis.cloud_provider == CloudProvider.AWS
    assert analysis.region == "us-east-1"
    assert analysis.status == AnalysisStatus.PENDING
    assert analysis.created_at is not None


def test_analysis_to_dict(db_session):
    """Test Analysis.to_dict() serialization."""
    analysis = Analysis(
        cloud_provider=CloudProvider.GCP,
        region="us-central1",
        days_analyzed=14,
        status=AnalysisStatus.COMPLETED,
        total_monthly_cost=1000.0,
        potential_monthly_savings=300.0,
        llm_insights="LLM insights",
        completed_at=datetime.now(timezone.utc),
    )
    db_session.add(analysis)
    db_session.commit()
    db_session.refresh(analysis)

    data = analysis.to_dict()
    assert data["id"] == analysis.id
    assert data["cloud_provider"] == "gcp"
    assert data["region"] == "us-central1"
    assert data["status"] == "completed"
    assert data["total_monthly_cost"] == 1000.0
    assert data["potential_monthly_savings"] == 300.0


def test_recommendation_model(db_session):
    """Test creating a Recommendation record."""
    analysis = Analysis(cloud_provider=CloudProvider.AWS, region="us-east-1", status=AnalysisStatus.COMPLETED)
    db_session.add(analysis)
    db_session.commit()

    rec = Recommendation(
        analysis_id=analysis.id,
        type=RecommendationType.IDLE_INSTANCE,
        resource_id="i-123456",
        resource_type="EC2:t3.medium",
        region="us-east-1",
        current_cost_monthly=50.0,
        recommended_action="Stop instance",
        estimated_savings_monthly=50.0,
        confidence=0.9,
        details={"instance_type": "t3.medium"},
    )
    db_session.add(rec)
    db_session.commit()
    db_session.refresh(rec)

    assert rec.id is not None
    assert rec.analysis_id == analysis.id
    assert rec.type == RecommendationType.IDLE_INSTANCE

    data = rec.to_dict()
    assert data["type"] == "idle_instance"
    assert data["resource_id"] == "i-123456"


def test_optimization_plan_model(db_session):
    """Test creating an OptimizationPlan record."""
    analysis = Analysis(cloud_provider=CloudProvider.AWS, region="us-east-1", status=AnalysisStatus.COMPLETED)
    db_session.add(analysis)
    db_session.commit()

    plan = OptimizationPlan(
        analysis_id=analysis.id,
        target_savings_monthly=500.0,
        projected_savings_monthly=450.0,
        actions=[{"action": "Stop idle instances", "savings": 300}],
        risk_assessment="Low risk",
        timeline_weeks=2,
    )
    db_session.add(plan)
    db_session.commit()
    db_session.refresh(plan)

    assert plan.id is not None
    data = plan.to_dict()
    assert data["target_savings_monthly"] == 500.0
    assert data["actions"][0]["action"] == "Stop idle instances"


def test_user_model(db_session):
    """Test User model and role handling."""
    user = User(
        sub="test-sub-model",
        email="test-model@example.com",
        name="Test User",
        roles="viewer,operator,admin",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    assert user.has_role("viewer")
    assert user.has_role("operator")
    assert user.has_role("admin")
    assert not user.has_role("nonexistent")

    data = user.to_dict()
    assert "viewer" in data["roles"]
    assert "operator" in data["roles"]
    assert "admin" in data["roles"]