import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { AnalysisDetail } from '../AnalysisDetail';
import { api } from '../../api/client';
import type { Analysis } from '../../types/api';
vi.mock('../../api/client', () => ({
  api: {
    getAnalysis: vi.fn(),
    listOptimizationPlans: vi.fn(),
    getRightsizeRecommendations: vi.fn(),
    askQuestion: vi.fn(),
    createOptimizationPlan: vi.fn(),
    getCsrfToken: vi.fn(),
    getCurrentUser: vi.fn(),
    logout: vi.fn(),
  },
}));

vi.mock('../../hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 1, sub: 'demo-user', email: 'demo@localhost', name: 'Demo User', roles: ['viewer'] },
    isLoading: false,
    isAuthenticated: true,
    login: vi.fn(),
    logout: vi.fn(),
    refreshUser: vi.fn(),
  }),
}));

const mockedApi = vi.mocked(api);

const ANALYSIS: Analysis = {
  id: 1,
  cloud_provider: 'aws',
  region: 'us-east-1',
  days_analyzed: 30,
  status: 'completed',
  total_monthly_cost: 500.0,
  potential_monthly_savings: 75.0,
  summary: 'Found 2 recommendations',
  llm_insights: null,
  raw_data: { total_monthly_cost: 500.0, by_service: { EC2: 300.0, EBS: 200.0 } },
  created_at: '2025-01-01T00:00:00Z',
  completed_at: '2025-01-01T00:05:00Z',
  recommendations: [],
};

function renderDetail() {
  return render(
    <MemoryRouter initialEntries={['/analyses/1']}>
      <Routes>
        <Route path="/analyses/:id" element={<AnalysisDetail />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('AnalysisDetail', () => {
  beforeEach(() => {
    mockedApi.getAnalysis.mockResolvedValue(ANALYSIS);
    mockedApi.listOptimizationPlans.mockResolvedValue([]);
  });

  afterEach(() => vi.clearAllMocks());

  it('loads the analysis and renders summary cards', async () => {
    renderDetail();

    expect(await screen.findByRole('heading', { name: 'Found 2 recommendations' })).toBeInTheDocument();
    expect(screen.getByText('Total Monthly Cost')).toBeInTheDocument();
    expect(screen.getAllByText(/\$500/)).toHaveLength(2);
    expect(screen.getAllByText(/\$75/)).toHaveLength(2);
    expect(screen.getAllByText('us-east-1').length).toBeGreaterThanOrEqual(1);
    expect(mockedApi.getAnalysis).toHaveBeenCalledWith(1);
  });

  it('renders the Ask Cost AI workflow and shows the answer after submit', async () => {
    mockedApi.askQuestion.mockResolvedValue({ answer: 'Your biggest waste is idle instances.' });

    renderDetail();

    await screen.findByRole('heading', { name: 'Found 2 recommendations' });

    fireEvent.click(screen.getByRole('button', { name: 'Ask Cost AI' }));

    const questionInput = screen.getByPlaceholderText('e.g. Where is my biggest waste this month?');
    fireEvent.change(questionInput, { target: { value: 'Where is my biggest waste?' } });
    fireEvent.click(screen.getByRole('button', { name: 'Ask' }));

    expect(await screen.findByText('Your biggest waste is idle instances.')).toBeInTheDocument();
    expect(mockedApi.askQuestion).toHaveBeenCalledWith(1, 'Where is my biggest waste?');
  });
});