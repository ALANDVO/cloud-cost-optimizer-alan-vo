import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { Analyses } from '../Analyses';
import { api } from '../../api/client';

vi.mock('../../api/client', () => ({
  api: {
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

describe('Analyses', () => {
  beforeEach(() => {
    mockedApi.listAnalyses.mockResolvedValue([]);
  });

  afterEach(() => vi.clearAllMocks());

  it('shows an empty state with a link to create an analysis', async () => {
    render(
      <MemoryRouter>
        <Analyses />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('No analyses yet')).toBeInTheDocument();
    });
    expect(screen.getByRole('link', { name: 'Create Analysis' })).toHaveAttribute('href', '/analyses/new');
  });

  it('lists analyses and filters by provider', async () => {
    mockedApi.listAnalyses.mockResolvedValueOnce([
      {
        id: 1,
        cloud_provider: 'aws',
        region: 'us-east-1',
        days_analyzed: 30,
        status: 'completed',
        total_monthly_cost: 500.0,
        potential_monthly_savings: 75.0,
        summary: 'AWS Analysis',
        llm_insights: null,
        raw_data: null,
        created_at: '2025-01-01T00:00:00Z',
        completed_at: null,
        recommendations: [],
      },
    ]);

    render(
      <MemoryRouter>
        <Analyses />
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(screen.getByText('AWS Analysis')).toBeInTheDocument();
    });
    expect(screen.getByText('us-east-1')).toBeInTheDocument();

    // Provider filter is wired to the API call
    const select = screen.getByLabelText('Provider');
    fireEvent.change(select, { target: { value: 'gcp' } });

    await waitFor(() => {
      expect(mockedApi.listAnalyses).toHaveBeenCalledWith({ provider: 'gcp', limit: 10, offset: 0 });
    });
  });
});