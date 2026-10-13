# Analysis API routes
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.core.database import get_db_session
from backend.app.core.auth import get_current_user, require_roles, verify_csrf
from backend.app.services.analysis import AnalysisService
from backend.app.models.analysis import Analysis, Recommendation, OptimizationPlan, CloudProvider, AnalysisStatus
from backend.app.models.user import User

router = APIRouter(tags=["analysis"])


# Request/Response models
class AnalysisCreate(BaseModel):
    cloud_provider: CloudProvider = Field(..., description="Cloud provider: aws, gcp, or azure")
    region: str = Field(..., description="Cloud region")
    days: int = Field(30, ge=1, le=365, description="Days of cost data to analyze")


class AnalysisResponse(BaseModel):
    id: int
    cloud_provider: str
    region: str
    days_analyzed: int
    status: str
    total_monthly_cost: float
    potential_monthly_savings: float
    summary: Optional[str]
    llm_insights: Optional[str]
    created_at: str
    completed_at: Optional[str]
    recommendations: List[dict] = []


class RecommendationResponse(BaseModel):
    id: int
    type: str
    resource_id: str
    resource_type: Optional[str]
    region: Optional[str]
    current_cost_monthly: float
    recommended_action: str
    estimated_savings_monthly: float
    confidence: float
    details: Optional[dict]


class OptimizationPlanCreate(BaseModel):
    target_savings: float = Field(..., gt=0, description="Target monthly savings in USD")


class OptimizationPlanResponse(BaseModel):
    id: int
    analysis_id: int
    target_savings_monthly: float
    projected_savings_monthly: float
    actions: List[dict]
    risk_assessment: Optional[str]
    timeline_weeks: int
    created_at: str


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)


class QuestionResponse(BaseModel):
    answer: str


class RightsizeRequest(BaseModel):
    resource_id: str = Field(..., min_length=1)


def analysis_to_response(analysis: Analysis) -> AnalysisResponse:
    return AnalysisResponse(
        id=analysis.id,
        cloud_provider=analysis.cloud_provider.value,
        region=analysis.region,
        days_analyzed=analysis.days_analyzed,
        status=analysis.status.value,
        total_monthly_cost=analysis.total_monthly_cost,
        potential_monthly_savings=analysis.potential_monthly_savings,
        summary=analysis.summary,
        llm_insights=analysis.llm_insights,
        created_at=analysis.created_at.isoformat() if analysis.created_at else "",
        completed_at=analysis.completed_at.isoformat() if analysis.completed_at else None,
        recommendations=[r.to_dict() for r in analysis.recommendations],
    )


@router.post("/api/analyze", response_model=AnalysisResponse)
def create_analysis(
    request: AnalysisCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db_session),
    user: User = Depends(require_roles("operator", "admin")),
):
    """Create and start a new cost analysis."""
    service = AnalysisService(db)
    analysis = service.create_analysis(request.cloud_provider, request.region, request.days)
    background_tasks.add_task(service.run_analysis, analysis.id)
    return analysis_to_response(analysis)


@router.get("/api/analyses", response_model=List[AnalysisResponse])
def list_analyses(
    provider: Optional[CloudProvider] = Query(None, description="Filter by cloud provider"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """List all analyses with optional filtering."""
    service = AnalysisService(db)
    analyses = service.list_analyses(provider, limit, offset)
    return [analysis_to_response(a) for a in analyses]


@router.get("/api/analyses/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Get analysis by ID with recommendations."""
    service = AnalysisService(db)
    analysis = service.get_analysis(analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return analysis_to_response(analysis)


@router.post("/api/analyses/{analysis_id}/plan", response_model=OptimizationPlanResponse)
def create_optimization_plan(
    analysis_id: int,
    request: OptimizationPlanCreate,
    db: Session = Depends(get_db_session),
    user: User = Depends(require_roles("operator", "admin")),
):
    """Generate an optimization plan for an analysis."""
    verify_csrf  # CSRF protection for state-changing operation
    service = AnalysisService(db)
    plan = service.generate_optimization_plan(analysis_id, request.target_savings)
    return OptimizationPlanResponse(
        id=plan.id,
        analysis_id=plan.analysis_id,
        target_savings_monthly=plan.target_savings_monthly,
        projected_savings_monthly=plan.projected_savings_monthly,
        actions=plan.actions,
        risk_assessment=plan.risk_assessment,
        timeline_weeks=plan.timeline_weeks,
        created_at=plan.created_at.isoformat() if plan.created_at else "",
    )


@router.get("/api/analyses/{analysis_id}/plan", response_model=List[OptimizationPlanResponse])
def list_optimization_plans(
    analysis_id: int,
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """List optimization plans for an analysis."""
    plans = db.query(OptimizationPlan).filter(OptimizationPlan.analysis_id == analysis_id).all()
    return [
        OptimizationPlanResponse(
            id=p.id,
            analysis_id=p.analysis_id,
            target_savings_monthly=p.target_savings_monthly,
            projected_savings_monthly=p.projected_savings_monthly,
            actions=p.actions,
            risk_assessment=p.risk_assessment,
            timeline_weeks=p.timeline_weeks,
            created_at=p.created_at.isoformat() if p.created_at else "",
        )
        for p in plans
    ]


@router.post("/api/analyses/{analysis_id}/ask", response_model=QuestionResponse)
def ask_question(
    analysis_id: int,
    request: QuestionRequest,
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Ask a natural language question about an analysis."""
    service = AnalysisService(db)
    try:
        answer = service.answer_question(analysis_id, request.question)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return QuestionResponse(answer=answer)


@router.post("/api/analyses/{analysis_id}/rightsize", response_model=List[dict])
def get_rightsize_recommendations(
    analysis_id: int,
    request: RightsizeRequest,
    db: Session = Depends(get_db_session),
    user: User = Depends(require_roles("operator", "admin")),
):
    """Get right-sizing recommendations for a specific resource."""
    service = AnalysisService(db)
    try:
        return service.get_rightsize_recommendations(analysis_id, request.resource_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))




@router.get("/api/stats")
def get_stats(
    db: Session = Depends(get_db_session),
    user: User = Depends(get_current_user),
):
    """Get overall statistics."""
    total_analyses = db.query(Analysis).count()
    completed = db.query(Analysis).filter(Analysis.status == AnalysisStatus.COMPLETED).count()
    total_savings = db.query(Analysis.potential_monthly_savings).filter(Analysis.status == AnalysisStatus.COMPLETED).all()
    total_savings = sum(s[0] for s in total_savings if s[0]) or 0

    # Sum of all recommendation savings
    from sqlalchemy import func
    total_rec_savings = db.query(func.sum(Recommendation.estimated_savings_monthly)).scalar() or 0

    return {
        "total_analyses": total_analyses,
        "completed_analyses": completed,
        "total_potential_savings": round(total_rec_savings, 2),
        "providers": [
            {"provider": "aws", "count": db.query(Analysis).filter(Analysis.cloud_provider == CloudProvider.AWS).count()},
            {"provider": "gcp", "count": db.query(Analysis).filter(Analysis.cloud_provider == CloudProvider.GCP).count()},
            {"provider": "azure", "count": db.query(Analysis).filter(Analysis.cloud_provider == CloudProvider.AZURE).count()},
        ],
    }