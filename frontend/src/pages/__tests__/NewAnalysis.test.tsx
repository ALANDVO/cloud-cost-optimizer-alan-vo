import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, useParams } from 'react-router-dom';
import type { ReactElement } from 'react';
import { NewAnalysis } from '../NewAnalysis';
import { api } from '../../api/client';
import type { Analysis } from '../../types/api';

vi.mock('../../api/client', () => ({
  api: { createAnalysis: vi.fn() },
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

function DetailMarker() {
  const { id } = useParams();
  return <div data-testid="detail">Detail for analysis {id}</div>;
}

function renderWithRouter(ui: ReactElement) {
  return render(
    <MemoryRouter initialEntries={['/analyses/new']}>
      <Routes>
        <Route path="/analyses/new" element={ui} />
        <Route path="/analyses/:id" element={<DetailMarker />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('NewAnalysis', () => {
  beforeEach(() => {
    mockedApi.createAnalysis.mockResolvedValue({
      id: 42,
      cloud_provider: 'aws',
      region: 'us-east-1',
      days_analyzed: 30,
      status: 'pending',
      total_monthly_cost: 0,
      potential_monthly_savings: 0,
      summary: '',
      llm_insights: null,
      raw_data: null,
      created_at: '2025-01-01T00:00:00Z',
      completed_at: null,
      recommendations: [],
    } as Analysis);
  });

  afterEach(() => vi.clearAllMocks());

  it('prevents submission when region is empty', async () => {
    renderWithRouter(<NewAnalysis />);

    const form = screen.getByRole('button', { name: 'Start Analysis' }).closest('form')!;
    fireEvent.submit(form);

    expect(await screen.findByText('Region is required')).toBeInTheDocument();
    expect(mockedApi.createAnalysis).not.toHaveBeenCalled();
  });

  it('submits the form and navigates to the detail page on success', async () => {
    renderWithRouter(<NewAnalysis />);

    const select = screen.getByLabelText('Cloud Provider');
    fireEvent.change(select, { target: { value: 'gcp' } });
    const region = screen.getByLabelText('Region');
    fireEvent.change(region, { target: { value: '  us-central1  ' } });
    const days = screen.getByLabelText('Days of history') as HTMLInputElement;
    fireEvent.change(days, { target: { value: '14' } });

    const form = screen.getByRole('button', { name: 'Start Analysis' }).closest('form')!;
    fireEvent.submit(form);

    await waitFor(() => {
      expect(mockedApi.createAnalysis).toHaveBeenCalledWith({
        cloud_provider: 'gcp',
        region: 'us-central1',
        days: 14,
      });
      expect(screen.getByTestId('detail')).toHaveTextContent('Detail for analysis 42');
    });
  });
});