// API Client - typed wrapper around axios
import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';
import type {
  Analysis,
  AnalysisCreate,
  OptimizationPlan,
  OptimizationPlanCreate,
  QuestionResponse,
  Stats,
  User,
  CloudProvider,
  Recommendation,
} from '../types/api';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

class ApiClient {
  private client: AxiosInstance;
  private csrfToken: string | null = null;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true, // Important for cookie-based auth
    });

    // Request interceptor to add CSRF token
    this.client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
      if (this.csrfToken && ['post', 'put', 'patch', 'delete'].includes(config.method || '')) {
        config.headers['X-CSRF-Token'] = this.csrfToken;
      }
      return config;
    });

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Handle unauthorized - redirect to login
          window.location.href = '/login';
        }
        return Promise.reject(error);
      }
    );
  }

  setCsrfToken(token: string) {
    this.csrfToken = token;
  }

  // Auth
  async getCurrentUser(): Promise<User> {
    const response = await this.client.get<User>('/auth/me');
    return response.data;
  }

  async getCsrfToken(): Promise<string> {
    const response = await this.client.get<{ csrf_token: string }>('/auth/csrf');
    this.setCsrfToken(response.data.csrf_token);
    return response.data.csrf_token;
  }

  async logout(): Promise<void> {
    await this.client.post('/auth/logout');
    this.csrfToken = null;
  }

  // Analysis
  async createAnalysis(data: AnalysisCreate): Promise<Analysis> {
    const response = await this.client.post<Analysis>('/analyze', data);
    return response.data;
  }

  async listAnalyses(params?: {
    provider?: CloudProvider;
    limit?: number;
    offset?: number;
  }): Promise<Analysis[]> {
    const response = await this.client.get<Analysis[]>('/analyses', { params });
    return response.data;
  }

  async getAnalysis(id: number): Promise<Analysis> {
    const response = await this.client.get<Analysis>(`/analyses/${id}`);
    return response.data;
  }

  async createOptimizationPlan(analysisId: number, data: OptimizationPlanCreate): Promise<OptimizationPlan> {
    const response = await this.client.post<OptimizationPlan>(`/analyses/${analysisId}/plan`, data);
    return response.data;
  }

  async listOptimizationPlans(analysisId: number): Promise<OptimizationPlan[]> {
    const response = await this.client.get<OptimizationPlan[]>(`/analyses/${analysisId}/plan`);
    return response.data;
  }

  async askQuestion(analysisId: number, question: string): Promise<QuestionResponse> {
    const response = await this.client.post<QuestionResponse>(`/analyses/${analysisId}/ask`, { question });
    return response.data;
  }

  async getRightsizeRecommendations(analysisId: number, resourceId: string): Promise<Recommendation[]> {
    const response = await this.client.post<Recommendation[]>(`/analyses/${analysisId}/rightsize`, { resource_id: resourceId });
    return response.data;
  }

  // Stats
  async getStats(): Promise<Stats> {
    const response = await this.client.get<Stats>('/stats');
    return response.data;
  }

  // Health
  async healthCheck(): Promise<{ status: string }> {
    const response = await this.client.get<{ status: string }>('/health');
    return response.data;
  }
}

export const api = new ApiClient();