import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Dashboard } from '../Dashboard';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
    getStats: vi.fn(),
    listAnalyses: vi.fn(),
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

function renderInRouter(ui: React.ReactElement) {
  return render(<MemoryRouter>{ui}</MemoryRouter>);
}

describe('Dashboard', () => {
  beforeEach(() => {
    mockedApi.getStats.mockResolvedValue({
      total_analyses: 3,
      completed_analyses: 2,
      total_potential_savings: 1500.0,
      providers: [
        { provider: 'aws', count: 2 },
        { provider: 'gcp', count: 1 },
        { provider: 'azure', count: 0 },
      ],
    });
    mockedApi.listAnalyses.mockResolvedValue([
      {
        id: 1,
        cloud_provider: 'aws',
        region: 'us-east-1',
        days_analyzed: 30,
        status: 'completed',
        total_monthly_cost: 500.0,
        potential_monthly_savings: 75.0,
        summary: 'Found 2 recommendations with $75.00/mo potential savings',
        llm_insights: null,
        raw_data: null,
        created_at: '2025-01-01T00:00:00Z',
        completed_at: '2025-01-01T00:05:00Z',
        recommendations: [],
      },
    ]);
  });

  afterEach(() => vi.clearAllMocks());

  it('renders stats cards and recent analyses from the API', async () => {
    renderInRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Total Analyses')).toBeInTheDocument();
      expect(screen.getByText('3')).toBeInTheDocument();
      expect(screen.getByText(/\$1,500/)).toBeInTheDocument();
    });

    // Recent analysis row rendered
    await waitFor(() => {
      expect(screen.getByText('Found 2 recommendations with $75.00/mo potential savings')).toBeInTheDocument();
    });

    expect(mockedApi.getStats).toHaveBeenCalledTimes(1);
    expect(mockedApi.listAnalyses).toHaveBeenCalledWith({ limit: 5 });
  });

  it('shows an empty state when there are no recent analyses', async () => {
    mockedApi.listAnalyses.mockResolvedValueOnce([]);

    renderInRouter(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('No analyses yet')).toBeInTheDocument();
      expect(screen.getByText('Create your first cloud cost analysis to start finding savings opportunities.')).toBeInTheDocument();
    });
    expect(screen.getByRole('link', { name: 'Create Analysis' })).toBeInTheDocument();
  });
});