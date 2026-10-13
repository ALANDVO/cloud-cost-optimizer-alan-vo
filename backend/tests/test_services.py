# Tests for AnalysisService
import pytest
from unittest.mock import Mock, patch, MagicMock
from backend.app.services.analysis import AnalysisService
from backend.app.models.analysis import Analysis, CloudProvider, AnalysisStatus, RecommendationType


@pytest.fixture
def mock_aws_service():
    """Create a mock AWS service."""
    with patch("backend.app.services.analysis.create_aws_service") as mock:
        service = Mock()
        service.detect_idle_instances.return_value = [
            {
                "type": RecommendationType.IDLE_INSTANCE.value,
                "resource_id": "i-123",
                "resource_type": "EC2:t3.medium",
                "region": "us-east-1",
                "current_cost_monthly": 50.0,
                "recommended_action": "Stop idle instance i-123",
                "estimated_savings_monthly": 50.0,
                "confidence": 0.9,
                "details": {"instance_type": "t3.medium", "avg_cpu_percent": 2.0},
            }
        ]
        service.find_unattached_volumes.return_value = [
            {
                "type": RecommendationType.UNATTACHED_VOLUME.value,
                "resource_id": "vol-456",
                "resource_type": "EBS:gp3",
                "region": "us-east-1",
                "current_cost_monthly": 20.0,
                "recommended_action": "Delete unattached volume vol-456",
                "estimated_savings_monthly": 20.0,
                "confidence": 0.95,
                "details": {"size_gb": 200, "volume_type": "gp3"},
            }
        ]
        service.find_orphaned_elastic_ips.return_value = []
        service.get_cost_summary.return_value = {
            "total_monthly_cost": 500.0,
            "by_service": {"EC2": 300.0, "EBS": 200.0},
            "period_days": 30,
        }
        mock.return_value = service
        yield service


@pytest.fixture
def mock_gcp_service():
    """Create a mock GCP service."""
    with patch("backend.app.services.analysis.create_gcp_service") as mock:
        service = Mock()
        service.detect_idle_instances.return_value = []
        service.find_unattached_disks.return_value = []
        service.find_orphaned_ips.return_value = []
        service.get_cost_summary.return_value = {
            "total_monthly_cost": 0.0,
            "by_service": {},
            "period_days": 30,
        }
        mock.return_value = service
        yield service


@pytest.fixture
def mock_llm_service():
    """Create a mock LLM service."""
    with patch("backend.app.services.analysis.create_llm_service") as mock:
        llm = Mock()
        llm.api_key = "test-key"
        llm.analyze_costs.return_value = "LLM analysis: Found significant waste in EC2 instances."
        llm.generate_optimization_plan.return_value = "Plan: 1. Stop idle instances (save $50)"
        llm.answer_question.return_value = "Your biggest waste is idle EC2 instances costing $50/month."
        mock.return_value = llm
        yield llm


def test_create_analysis(db_session):
    """Test creating an analysis record."""
    service = AnalysisService(db_session)
    analysis = service.create_analysis(CloudProvider.AWS, "us-east-1", 30)

    assert analysis.id is not None
    assert analysis.cloud_provider == CloudProvider.AWS
    assert analysis.region == "us-east-1"
    assert analysis.days_analyzed == 30
    assert analysis.status == AnalysisStatus.PENDING


def test_run_analysis_aws(db_session, mock_aws_service, mock_llm_service):
    """Test running AWS analysis."""
    service = AnalysisService(db_session)
    analysis = service.create_analysis(CloudProvider.AWS, "us-east-1", 30)

    completed = service.run_analysis(analysis.id)

    assert completed.status == AnalysisStatus.COMPLETED
    assert completed.total_monthly_cost == 500.0
    assert completed.potential_monthly_savings == 70.0  # 50 + 20
    assert completed.llm_insights is not None
    assert len(completed.recommendations) == 2

    # Verify recommendations persisted
    recs = completed.recommendations
    assert any(r.type == RecommendationType.IDLE_INSTANCE for r in recs)
    assert any(r.type == RecommendationType.UNATTACHED_VOLUME for r in recs)


def test_run_analysis_failure(db_session):
    """Test analysis failure handling."""
    service = AnalysisService(db_session)
    analysis = service.create_analysis(CloudProvider.AWS, "invalid-region", 30)

    # Mock service to raise exception
    with patch("backend.app.services.analysis.create_aws_service") as mock:
        mock.side_effect = Exception("AWS credentials not found")

        with pytest.raises(Exception):
            service.run_analysis(analysis.id)

    # Check analysis marked as failed
    db_session.refresh(analysis)
    assert analysis.status == AnalysisStatus.FAILED


def test_get_analysis(db_session, mock_aws_service, mock_llm_service):
    """Test retrieving analysis by ID."""
    service = AnalysisService(db_session)
    analysis = service.create_analysis(CloudProvider.AWS, "us-east-1", 30)
    service.run_analysis(analysis.id)

    retrieved = service.get_analysis(analysis.id)
    assert retrieved is not None
    assert retrieved.id == analysis.id
    assert len(retrieved.recommendations) == 2


def test_list_analyses(db_session, mock_aws_service, mock_llm_service):
    """Test listing analyses with filtering."""
    service = AnalysisService(db_session)

    a1 = service.create_analysis(CloudProvider.AWS, "us-east-1", 30)
    service.run_analysis(a1.id)

    a2 = service.create_analysis(CloudProvider.GCP, "us-central1", 30)
    # Don't run GCP analysis to test filtering

    all_analyses = service.list_analyses()
    # Only count the ones we created in this test (there may be leftovers from other tests)
    aws_analyses = service.list_analyses(provider=CloudProvider.AWS)
    assert len(aws_analyses) >= 1
    assert all(a.cloud_provider == CloudProvider.AWS for a in aws_analyses)


def test_generate_optimization_plan(db_session, mock_aws_service, mock_llm_service):
    """Test generating optimization plan."""
    service = AnalysisService(db_session)
    analysis = service.create_analysis(CloudProvider.AWS, "us-east-1", 30)
    service.run_analysis(analysis.id)

    plan = service.generate_optimization_plan(analysis.id, target_savings=100.0)

    assert plan.analysis_id == analysis.id
    assert plan.target_savings_monthly == 100.0
    assert plan.projected_savings_monthly > 0
    assert len(plan.actions) > 0
    assert plan.timeline_weeks == 4


def test_generate_optimization_plan_not_completed(db_session):
    """Test plan generation fails for non-completed analysis."""
    service = AnalysisService(db_session)
    analysis = service.create_analysis(CloudProvider.AWS, "us-east-1", 30)
    # Don't run analysis

    with pytest.raises(ValueError, match="completed"):
        service.generate_optimization_plan(analysis.id, 100.0)


def test_answer_question(db_session, mock_aws_service, mock_llm_service):
    """Test answering natural language question."""
    service = AnalysisService(db_session)
    analysis = service.create_analysis(CloudProvider.AWS, "us-east-1", 30)
    service.run_analysis(analysis.id)

    answer = service.answer_question(analysis.id, "What is my biggest waste?")
    assert "idle" in answer.lower() or "ec2" in answer.lower()


def test_answer_question_no_llm(db_session, mock_aws_service):
    """Test answering question without LLM configured."""
    with patch("backend.app.services.analysis.create_llm_service") as mock:
        llm = Mock()
        llm.api_key = None
        mock.return_value = llm

        service = AnalysisService(db_session)
        analysis = service.create_analysis(CloudProvider.AWS, "us-east-1", 30)
        service.run_analysis(analysis.id)

        answer = service.answer_question(analysis.id, "What is my cost?")
        assert "LLM not configured" in answer


def test_get_rightsize_recommendations(db_session, mock_aws_service, mock_llm_service):
    """Test getting rightsize recommendations."""
    service = AnalysisService(db_session)
    analysis = service.create_analysis(CloudProvider.AWS, "us-east-1", 30)
    service.run_analysis(analysis.id)

    # Mock the AWS service's get_rightsize_recommendations method
    mock_aws_service.get_rightsize_recommendations.return_value = [
        {
            "type": RecommendationType.RIGHTSIZE.value,
            "resource_id": "i-123",
            "current_type": "t3.large",
            "recommended_type": "t3.medium",
            "estimated_savings": 30.0,
        }
    ]

    recommendations = service.get_rightsize_recommendations(analysis.id, "i-123")
    assert len(recommendations) == 1
    assert recommendations[0]["type"] == "rightsize"


def test_get_rightsize_non_aws(db_session, mock_gcp_service, mock_llm_service):
    """Test rightsize for non-AWS provider returns error."""
    service = AnalysisService(db_session)
    analysis = service.create_analysis(CloudProvider.GCP, "us-central1", 30)
    service.run_analysis(analysis.id)

    recommendations = service.get_rightsize_recommendations(analysis.id, "instance-1")
    assert len(recommendations) == 1
    assert "error" in recommendations[0]
    assert "AWS" in recommendations[0]["error"]