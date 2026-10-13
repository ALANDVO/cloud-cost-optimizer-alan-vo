// API Types - matches backend models

export type CloudProvider = 'aws' | 'gcp' | 'azure';
export type AnalysisStatus = 'pending' | 'running' | 'completed' | 'failed';
export type RecommendationType =
  | 'idle_instance'
  | 'unattached_volume'
  | 'orphaned_ip'
  | 'rightsize'
  | 'reserved_instance'
  | 'committed_use';

export interface Analysis {
  id: number;
  cloud_provider: CloudProvider;
  region: string;
  days_analyzed: number;
  status: AnalysisStatus;
  total_monthly_cost: number;
  potential_monthly_savings: number;
  summary: string | null;
  llm_insights: string | null;
  raw_data: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
  recommendations: Recommendation[];
}

export interface Recommendation {
  id: number;
  analysis_id: number;
  type: RecommendationType;
  resource_id: string;
  resource_type: string | null;
  region: string | null;
  current_cost_monthly: number;
  recommended_action: string;
  estimated_savings_monthly: number;
  confidence: number;
  details: Record<string, unknown> | null;
  created_at: string;
}

export interface OptimizationPlan {
  id: number;
  analysis_id: number;
  target_savings_monthly: number;
  projected_savings_monthly: number;
  actions: PlanAction[];
  risk_assessment: string | null;
  timeline_weeks: number;
  created_at: string;
}

export interface PlanAction {
  priority: 'high' | 'medium' | 'low';
  action: string;
  resource_id: string;
  type: string;
  estimated_savings: number;
  effort: 'low' | 'medium' | 'high';
  risk: 'low' | 'medium' | 'high';
}

export interface AnalysisCreate {
  cloud_provider: CloudProvider;
  region: string;
  days: number;
}

export interface OptimizationPlanCreate {
  target_savings: number;
}

export interface QuestionRequest {
  question: string;
}

export interface QuestionResponse {
  answer: string;
}

export interface RightsizeRequest {
  resource_id: string;
}

export interface Stats {
  total_analyses: number;
  completed_analyses: number;
  total_potential_savings: number;
  providers: { provider: string; count: number }[];
}

export interface User {
  id: number;
  sub: string;
  email: string;
  name: string | null;
  roles: string[];
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}