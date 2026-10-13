# Analysis domain models
from datetime import datetime
from enum import Enum
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Float, DateTime, ForeignKey, Text, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class CloudProvider(str, Enum):
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


class AnalysisStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class RecommendationType(str, Enum):
    IDLE_INSTANCE = "idle_instance"
    UNATTACHED_VOLUME = "unattached_volume"
    ORPHANED_IP = "orphaned_ip"
    RIGHTSIZE = "rightsize"
    RESERVED_INSTANCE = "reserved_instance"
    COMMITTED_USE = "committed_use"


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cloud_provider = Column(SQLEnum(CloudProvider), nullable=False)
    region = Column(String(64), nullable=False)
    days_analyzed = Column(Integer, default=30)
    status = Column(SQLEnum(AnalysisStatus), default=AnalysisStatus.PENDING)
    total_monthly_cost = Column(Float, default=0.0)
    potential_monthly_savings = Column(Float, default=0.0)
    summary = Column(Text, nullable=True)
    llm_insights = Column(Text, nullable=True)
    raw_data = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    recommendations = relationship("Recommendation", back_populates="analysis", cascade="all, delete-orphan")
    optimization_plans = relationship("OptimizationPlan", back_populates="analysis", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "cloud_provider": self.cloud_provider.value,
            "region": self.region,
            "days_analyzed": self.days_analyzed,
            "status": self.status.value,
            "total_monthly_cost": self.total_monthly_cost,
            "potential_monthly_savings": self.potential_monthly_savings,
            "summary": self.summary,
            "llm_insights": self.llm_insights,
            "raw_data": self.raw_data,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "recommendations": [r.to_dict() for r in self.recommendations],
        }


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    type = Column(SQLEnum(RecommendationType), nullable=False)
    resource_id = Column(String(128), nullable=False)
    resource_type = Column(String(64), nullable=True)
    region = Column(String(64), nullable=True)
    current_cost_monthly = Column(Float, default=0.0)
    recommended_action = Column(Text, nullable=False)
    estimated_savings_monthly = Column(Float, default=0.0)
    confidence = Column(Float, default=1.0)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="recommendations")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "type": self.type.value,
            "resource_id": self.resource_id,
            "resource_type": self.resource_type,
            "region": self.region,
            "current_cost_monthly": self.current_cost_monthly,
            "recommended_action": self.recommended_action,
            "estimated_savings_monthly": self.estimated_savings_monthly,
            "confidence": self.confidence,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class OptimizationPlan(Base):
    __tablename__ = "optimization_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    target_savings_monthly = Column(Float, default=0.0)
    projected_savings_monthly = Column(Float, default=0.0)
    actions = Column(JSON, nullable=False)  # List of prioritized actions
    risk_assessment = Column(Text, nullable=True)
    timeline_weeks = Column(Integer, default=4)
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("Analysis", back_populates="optimization_plans")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "analysis_id": self.analysis_id,
            "target_savings_monthly": self.target_savings_monthly,
            "projected_savings_monthly": self.projected_savings_monthly,
            "actions": self.actions,
            "risk_assessment": self.risk_assessment,
            "timeline_weeks": self.timeline_weeks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }