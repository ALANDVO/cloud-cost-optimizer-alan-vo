# Tests for API endpoints
import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient
from backend.app.models.analysis import CloudProvider, AnalysisStatus, RecommendationType


@pytest.fixture
def mock_cloud_services():
    """Mock all cloud services for API tests."""
    with patch("backend.app.services.analysis.create_aws_service") as mock_aws, \
         patch("backend.app.services.analysis.create_gcp_service") as mock_gcp, \
         patch("backend.app.services.analysis.create_azure_service") as mock_azure, \
         patch("backend.app.services.analysis.create_llm_service") as mock_llm:

        # Mock AWS service
        aws_service = Mock()
        aws_service.detect_idle_instances.return_value = [
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
        aws_service.find_unattached_volumes.return_value = [
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
        aws_service.find_orphaned_elastic_ips.return_value = []
        aws_service.get_cost_summary.return_value = {
            "total_monthly_cost": 500.0,
            "by_service": {"EC2": 300.0, "EBS": 200.0},
            "period_days": 30,
        }
        aws_service.get_rightsize_recommendations.return_value = [
            {
                "type": RecommendationType.RIGHTSIZE.value,
                "resource_id": "i-123",
                "current_type": "t3.large",
                "recommended_type": "t3.medium",
                "estimated_savings": 30.0,
            }
        ]
        mock_aws.return_value = aws_service

        # Mock GCP service
        gcp_service = Mock()
        gcp_service.detect_idle_instances.return_value = []
        gcp_service.find_unattached_disks.return_value = []
        gcp_service.find_orphaned_ips.return_value = []
        gcp_service.get_cost_summary.return_value = {
            "total_monthly_cost": 300.0,
            "by_service": {"Compute Engine": 300.0},
            "period_days": 30,
        }
        mock_gcp.return_value = gcp_service

        # Mock Azure service
        azure_service = Mock()
        azure_service.detect_idle_vms.return_value = []
        azure_service.find_unattached_disks.return_value = []
        azure_service.find_orphaned_public_ips.return_value = []
        azure_service.get_cost_summary.return_value = {
            "total_monthly_cost": 200.0,
            "by_service": {"Virtual Machines": 200.0},
            "period_days": 30,
        }
        mock_azure.return_value = azure_service

        # Mock LLM service
        llm_service = Mock()
        llm_service.api_key = "test-key"
        llm_service.analyze_costs.return_value = "LLM analysis: Found waste."
        llm_service.generate_optimization_plan.return_value = "Plan: Stop idle instances."
        llm_service.answer_question.return_value = "Your biggest waste is idle instances."
        mock_llm.return_value = llm_service

        yield {
            "aws": aws_service,
            "gcp": gcp_service,
            "azure": azure_service,
            "llm": llm_service,
        }


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "degraded")
    assert data["service"] == "cloud-cost-optimizer-alan-vo"
    assert "version" in data


def test_readiness_check(client):
    """Test readiness check endpoint."""
    response = client.get("/api/ready")
    assert response.status_code == 200
    assert response.json()["ready"] is True


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "cloud-cost-optimizer-alan-vo"
    assert "version" in data


def test_create_analysis(client, mock_cloud_services):
    """Test creating a new analysis."""
    response = client.post("/api/analyze", json={
        "cloud_provider": "aws",
        "region": "us-east-1",
        "days": 30,
    })
    assert response.status_code in (200, 201)
    data = response.json()
    assert "id" in data
    assert data["cloud_provider"] == "aws"
    assert data["region"] == "us-east-1"
    assert data["status"] in ("pending", "running", "completed")


def test_list_analyses(client):
    """Test listing analyses."""
    response = client.get("/api/analyses")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_analysis_not_found(client):
    """Test getting non-existent analysis."""
    response = client.get("/api/analyses/99999")
    assert response.status_code == 404


def test_get_stats(client, mock_cloud_services):
    """Test stats endpoint."""
    response = client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_analyses" in data
    assert "completed_analyses" in data
    assert "providers" in data


def test_auth_me_demo_mode(client):
    """Test /api/auth/me in demo mode."""
    response = client.get("/api/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "demo@localhost"
    assert "viewer" in data["roles"]


def test_csrf_token(client):
    """Test CSRF token endpoint."""
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    data = response.json()
    assert "csrf_token" in data
    assert len(data["csrf_token"]) > 0


def test_logout(client):
    """Test logout endpoint."""
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    assert "Logged out" in response.json()["message"]


def test_ask_question_without_analysis(client):
    """Test asking question for non-existent analysis."""
    response = client.post("/api/analyses/99999/ask", json={"question": "What is my cost?"})
    assert response.status_code == 404


def test_rightsize_without_analysis(client):
    """Test rightsize for non-existent analysis."""
    response = client.post("/api/analyses/99999/rightsize", json={"resource_id": "i-123"})
    assert response.status_code == 404


def test_analysis_workflow(client, mock_cloud_services):
    """Test full analysis workflow: create -> list -> get."""
    # Create analysis
    create_resp = client.post("/api/analyze", json={
        "cloud_provider": "aws",
        "region": "us-west-2",
        "days": 7,
    })
    assert create_resp.status_code in (200, 201)
    analysis = create_resp.json()
    analysis_id = analysis["id"]

    # List analyses
    list_resp = client.get("/api/analyses")
    assert list_resp.status_code == 200
    analyses = list_resp.json()
    assert any(a["id"] == analysis_id for a in analyses)

    # Get analysis
    get_resp = client.get(f"/api/analyses/{analysis_id}")
    assert get_resp.status_code == 200
    detail = get_resp.json()
    assert detail["id"] == analysis_id
    assert detail["region"] == "us-west-2"


def test_optimization_plan_creation(client, mock_cloud_services):
    """Test creating optimization plan."""
    # First create an analysis
    create_resp = client.post("/api/analyze", json={
        "cloud_provider": "aws",
        "region": "us-east-1",
        "days": 30,
    })
    assert create_resp.status_code in (200, 201)
    analysis_id = create_resp.json()["id"]

    # Create plan
    plan_resp = client.post(f"/api/analyses/{analysis_id}/plan", json={
        "target_savings": 100.0,
    })
    assert plan_resp.status_code == 200
    plan = plan_resp.json()
    assert plan["analysis_id"] == analysis_id
    assert plan["target_savings_monthly"] == 100.0
    assert "actions" in plan


def test_filter_analyses_by_provider(client, mock_cloud_services):
    """Test filtering analyses by provider."""
    # Create analyses for different providers
    client.post("/api/analyze", json={"cloud_provider": "aws", "region": "us-east-1", "days": 30})
    client.post("/api/analyze", json={"cloud_provider": "gcp", "region": "us-central1", "days": 30})

    aws_resp = client.get("/api/analyses?provider=aws")
    assert aws_resp.status_code == 200
    aws_analyses = aws_resp.json()
    assert all(a["cloud_provider"] == "aws" for a in aws_analyses)

    gcp_resp = client.get("/api/analyses?provider=gcp")
    assert gcp_resp.status_code == 200
    gcp_analyses = gcp_resp.json()
    assert all(a["cloud_provider"] == "gcp" for a in gcp_analyses)


def test_pagination(client, mock_cloud_services):
    """Test pagination of analyses list."""
    # Create multiple analyses
    for i in range(5):
        client.post("/api/analyze", json={"cloud_provider": "aws", "region": f"us-east-{i+1}", "days": 30})

    page1 = client.get("/api/analyses?limit=2&offset=0")
    assert page1.status_code == 200
    assert len(page1.json()) == 2

    page2 = client.get("/api/analyses?limit=2&offset=2")
    assert page2.status_code == 200
    assert len(page2.json()) == 2