# Analysis orchestration service
from datetime import datetime
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from backend.app.models.analysis import Analysis, Recommendation, OptimizationPlan, CloudProvider, AnalysisStatus, RecommendationType
from backend.app.services.aws import create_aws_service
from backend.app.services.gcp import create_gcp_service
from backend.app.services.azure import create_azure_service
from backend.app.services.llm import create_llm_service
from backend.app.core.config import get_settings


class AnalysisService:
    """Orchestrates cloud cost analysis across providers."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.llm = create_llm_service()

    def _get_cloud_service(self, provider: CloudProvider, region: str = None):
        """Get cloud provider service instance."""
        if provider == CloudProvider.AWS:
            return create_aws_service(region or self.settings.AWS_DEFAULT_REGION)
        elif provider == CloudProvider.GCP:
            return create_gcp_service(self.settings.GCP_PROJECT_ID or "unknown-project")
        elif provider == CloudProvider.AZURE:
            return create_azure_service(self.settings.AZURE_SUBSCRIPTION_ID or "unknown-subscription")
        raise ValueError(f"Unsupported provider: {provider}")

    def create_analysis(
        self,
        provider: CloudProvider,
        region: str,
        days: int = 30,
    ) -> Analysis:
        """Create a new analysis record."""
        analysis = Analysis(
            cloud_provider=provider,
            region=region,
            days_analyzed=days,
            status=AnalysisStatus.PENDING,
        )
        self.db.add(analysis)
        self.db.commit()
        self.db.refresh(analysis)
        return analysis

    def run_analysis(self, analysis_id: int) -> Analysis:
        """Run the full analysis for a given analysis ID."""
        analysis = self.db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        analysis.status = AnalysisStatus.RUNNING
        self.db.commit()

        try:
            provider = analysis.cloud_provider
            region = analysis.region
            days = analysis.days_analyzed

            service = self._get_cloud_service(provider, region)

            all_recommendations = []
            cost_summary = {"total_monthly_cost": 0.0, "by_service": {}}

            # Run waste detection
            if provider == CloudProvider.AWS:
                idle = service.detect_idle_instances(days=days)
                unattached = service.find_unattached_volumes()
                orphaned = service.find_orphaned_elastic_ips()
                cost_summary = service.get_cost_summary(days=days)
                all_recommendations.extend(idle)
                all_recommendations.extend(unattached)
                all_recommendations.extend(orphaned)
            elif provider == CloudProvider.GCP:
                idle = service.detect_idle_instances(days=days)
                unattached = service.find_unattached_disks()
                orphaned = service.find_orphaned_ips()
                cost_summary = service.get_cost_summary(days=days)
                all_recommendations.extend(idle)
                all_recommendations.extend(unattached)
                all_recommendations.extend(orphaned)
            elif provider == CloudProvider.AZURE:
                idle = service.detect_idle_vms(days=days)
                unattached = service.find_unattached_disks()
                orphaned = service.find_orphaned_public_ips()
                cost_summary = service.get_cost_summary(days=days)
                all_recommendations.extend(idle)
                all_recommendations.extend(unattached)
                all_recommendations.extend(orphaned)

            # Persist recommendations
            total_savings = 0.0
            for rec_data in all_recommendations:
                rec = Recommendation(
                    analysis_id=analysis.id,
                    type=RecommendationType(rec_data["type"]),
                    resource_id=rec_data["resource_id"],
                    resource_type=rec_data.get("resource_type"),
                    region=rec_data.get("region"),
                    current_cost_monthly=rec_data.get("current_cost_monthly", 0.0),
                    recommended_action=rec_data["recommended_action"],
                    estimated_savings_monthly=rec_data.get("estimated_savings_monthly", 0.0),
                    confidence=rec_data.get("confidence", 1.0),
                    details=rec_data.get("details"),
                )
                self.db.add(rec)
                total_savings += rec.estimated_savings_monthly

            # Generate LLM insights if API key available
            llm_insights = None
            if self.llm.api_key:
                try:
                    llm_insights = self.llm.analyze_costs(cost_summary, all_recommendations)
                except Exception:
                    pass  # Silently fail LLM calls

            # Update analysis
            analysis.status = AnalysisStatus.COMPLETED
            analysis.total_monthly_cost = cost_summary.get("total_monthly_cost", 0.0)
            analysis.potential_monthly_savings = total_savings
            analysis.summary = f"Found {len(all_recommendations)} recommendations with ${total_savings:,.2f}/mo potential savings"
            analysis.llm_insights = llm_insights
            analysis.raw_data = cost_summary
            analysis.completed_at = datetime.utcnow()

            self.db.commit()
            self.db.refresh(analysis)
            return analysis

        except Exception as e:
            analysis.status = AnalysisStatus.FAILED
            analysis.summary = f"Analysis failed: {str(e)}"
            self.db.commit()
            raise

    def get_analysis(self, analysis_id: int) -> Optional[Analysis]:
        """Get analysis by ID."""
        return self.db.query(Analysis).filter(Analysis.id == analysis_id).first()

    def list_analyses(self, provider: Optional[CloudProvider] = None, limit: int = 50, offset: int = 0) -> List[Analysis]:
        """List analyses with optional filtering."""
        query = self.db.query(Analysis).order_by(Analysis.created_at.desc())
        if provider:
            query = query.filter(Analysis.cloud_provider == provider)
        return query.offset(offset).limit(limit).all()

    def generate_optimization_plan(
        self,
        analysis_id: int,
        target_savings: float,
    ) -> OptimizationPlan:
        """Generate an optimization plan for an analysis."""
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        if analysis.status != AnalysisStatus.COMPLETED:
            raise ValueError("Analysis must be completed before generating plan")

        # Prepare data for LLM
        recommendations = [r.to_dict() for r in analysis.recommendations]
        analysis_data = {
            "cloud_provider": analysis.cloud_provider.value,
            "region": analysis.region,
            "total_monthly_cost": analysis.total_monthly_cost,
            "potential_monthly_savings": analysis.potential_monthly_savings,
            "recommendations": recommendations,
        }

        # Generate plan using LLM
        actions = []
        projected_savings = 0.0
        risk_assessment = "Standard risk assessment applied."

        if self.llm.api_key:
            try:
                llm_plan = self.llm.generate_optimization_plan(analysis_data, target_savings)
                # Parse LLM output into structured actions (simplified)
                actions = self._parse_plan_actions(llm_plan, recommendations)
                projected_savings = sum(a.get("estimated_savings", 0) for a in actions)
                risk_assessment = "LLM-generated plan with risk considerations."
            except Exception:
                pass

        # Fallback: simple priority-based plan
        if not actions:
            actions, projected_savings = self._create_fallback_plan(recommendations, target_savings)

        plan = OptimizationPlan(
            analysis_id=analysis.id,
            target_savings_monthly=target_savings,
            projected_savings_monthly=projected_savings,
            actions=actions,
            risk_assessment=risk_assessment,
            timeline_weeks=4,
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)
        return plan

    def _parse_plan_actions(self, llm_output: str, recommendations: List[Dict]) -> List[Dict]:
        """Parse LLM plan output into structured actions (simplified)."""
        # In a real implementation, this would parse the LLM output
        # For now, return priority-sorted recommendations
        sorted_recs = sorted(recommendations, key=lambda r: -r.get("estimated_savings_monthly", 0))
        actions = []
        for i, rec in enumerate(sorted_recs):
            actions.append({
                "priority": "high" if i < 3 else "medium" if i < 6 else "low",
                "action": rec.get("recommended_action", ""),
                "resource_id": rec.get("resource_id", ""),
                "type": rec.get("type", ""),
                "estimated_savings": rec.get("estimated_savings_monthly", 0),
                "effort": "low",
                "risk": "low",
            })
        return actions

    def _create_fallback_plan(self, recommendations: List[Dict], target_savings: float) -> tuple:
        """Create a simple priority-based plan without LLM."""
        sorted_recs = sorted(recommendations, key=lambda r: -r.get("estimated_savings_monthly", 0))
        actions = []
        total = 0.0
        for i, rec in enumerate(sorted_recs):
            if total >= target_savings:
                break
            savings = rec.get("estimated_savings_monthly", 0)
            actions.append({
                "priority": "high" if i < 3 else "medium" if i < 6 else "low",
                "action": rec.get("recommended_action", ""),
                "resource_id": rec.get("resource_id", ""),
                "type": rec.get("type", ""),
                "estimated_savings": savings,
                "effort": "low",
                "risk": "low",
            })
            total += savings
        return actions, total

    def answer_question(self, analysis_id: int, question: str) -> str:
        """Answer a natural language question about an analysis."""
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        if analysis.status != AnalysisStatus.COMPLETED:
            raise ValueError("Analysis must be completed")

        context = {
            "cloud_provider": analysis.cloud_provider.value,
            "region": analysis.region,
            "total_monthly_cost": analysis.total_monthly_cost,
            "potential_monthly_savings": analysis.potential_monthly_savings,
            "summary": analysis.summary,
            "recommendations": [r.to_dict() for r in analysis.recommendations],
        }

        if not self.llm.api_key:
            return "LLM not configured. Please set LLM_API_KEY to enable natural language queries."

        return self.llm.answer_question(question, context)

    def get_rightsize_recommendations(self, analysis_id: int, resource_id: str) -> List[Dict[str, Any]]:
        """Get right-sizing recommendations for a specific resource."""
        analysis = self.get_analysis(analysis_id)
        if not analysis:
            raise ValueError(f"Analysis {analysis_id} not found")

        if analysis.cloud_provider != CloudProvider.AWS:
            return [{"error": "Right-sizing currently only supported for AWS"}]

        service = self._get_cloud_service(analysis.cloud_provider, analysis.region)
        return service.get_rightsize_recommendations(resource_id)