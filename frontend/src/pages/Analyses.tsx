// Analyses List Page
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import { Card, Button, EmptyState, ErrorState, PageHeader, Select } from '../components/ui';
import {
  Plus,
  Search,
  ChevronLeft,
  ChevronRight,
  Cloud,
  Download,
} from 'lucide-react';
import { cn, formatCurrency, getProviderLabel, getProviderColor, getStatusColor, formatRelativeTime } from '../utils/helpers';
import type { Analysis, CloudProvider } from '../types/api';
import { Link } from 'react-router-dom';

export function Analyses() {
  const { isLoading: authLoading } = useAuth();
  const [analyses, setAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [providerFilter, setProviderFilter] = useState<CloudProvider | ''>('');
  const [page, setPage] = useState(0);
  const pageSize = 10;
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    if (authLoading) return;
    fetchAnalyses();
  }, [authLoading, page, search, providerFilter]);

  const fetchAnalyses = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.listAnalyses({
        provider: providerFilter || undefined,
        limit: pageSize,
        offset: page * pageSize,
      });
      setAnalyses(data);
      // For simplicity, we'll just use the returned count
      // In a real app, the API would return total count
      setTotalCount(data.length + page * pageSize);
    } catch (err) {
      setError('Failed to load analyses');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const filteredAnalyses = analyses.filter((a) =>
    a.summary?.toLowerCase().includes(search.toLowerCase()) ||
    a.region.toLowerCase().includes(search.toLowerCase()) ||
    a.id.toString().includes(search)
  );

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Analyses"
          description="View and manage your cloud cost analyses"
          action={<Button leftIcon={Plus}><Link to="/analyses/new">New Analysis</Link></Button>}
        />
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-lg border border-gray-200 bg-white p-6 animate-pulse">
              <div className="h-4 w-1/4 bg-gray-200 rounded mb-4" />
              <div className="flex gap-4">
                <div className="h-4 w-24 bg-gray-200 rounded" />
                <div className="h-4 w-32 bg-gray-200 rounded" />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Analyses"
          description="View and manage your cloud cost analyses"
          action={<Button leftIcon={Plus}><Link to="/analyses/new">New Analysis</Link></Button>}
        />
        <ErrorState message={error} onRetry={fetchAnalyses} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Analyses"
        description="View and manage your cloud cost analyses across all providers"
        action={
          <Link to="/analyses/new">
            <Button leftIcon={Plus}>New Analysis</Button>
          </Link>
        }
      />

      <Card>
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6 p-4 bg-gray-50 rounded-lg">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" aria-hidden="true" />
            <input
              type="text"
              placeholder="Search analyses..."
              value={search}
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <Select
            label="Provider"
            value={providerFilter}
            onChange={(e) => { setProviderFilter(e.target.value as CloudProvider); setPage(0); }}
            options={[
              { value: '', label: 'All Providers' },
              { value: 'aws', label: 'AWS' },
              { value: 'gcp', label: 'GCP' },
              { value: 'azure', label: 'Azure' },
            ]}
            className="w-full sm:w-48"
          />
        </div>

        {/* Results */}
        {filteredAnalyses.length === 0 ? (
          <EmptyState
            icon={Cloud}
            title={search || providerFilter ? 'No matching analyses' : 'No analyses yet'}
            description={search || providerFilter
              ? 'Try adjusting your search or filter criteria.'
              : 'Create your first cloud cost analysis to start finding savings opportunities.'}
            action={
              <Link to="/analyses/new">
                <Button leftIcon={Plus}>Create Analysis</Button>
              </Link>
            }
          />
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Analysis</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Provider</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Region</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Days</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Status</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Total Cost</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Potential Savings</th>
                    <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Created</th>
                    <th className="text-right py-3 px-4 font-medium text-gray-500 text-sm">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {filteredAnalyses.map((analysis) => (
                    <tr key={analysis.id} className="hover:bg-gray-50">
                      <td className="py-4 px-4">
                        <Link
                          to={`/analyses/${analysis.id}`}
                          className="font-medium text-blue-600 hover:text-blue-700"
                        >
                          {analysis.summary || `Analysis #${analysis.id}`}
                        </Link>
                      </td>
                      <td className="py-4 px-4">
                        <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', getProviderColor(analysis.cloud_provider))}>
                          {getProviderLabel(analysis.cloud_provider)}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-gray-500">{analysis.region}</td>
                      <td className="py-4 px-4 text-gray-500">{analysis.days_analyzed}</td>
                      <td className="py-4 px-4">
                        <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(analysis.status))}>
                          {analysis.status}
                        </span>
                      </td>
                      <td className="py-4 px-4 text-gray-900 font-medium">{formatCurrency(analysis.total_monthly_cost)}/mo</td>
                      <td className="py-4 px-4 text-gray-900 font-medium text-green-600">{formatCurrency(analysis.potential_monthly_savings)}/mo</td>
                      <td className="py-4 px-4 text-gray-500 text-sm">{formatRelativeTime(analysis.created_at)}</td>
                      <td className="py-4 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            to={`/analyses/${analysis.id}`}
                            className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                          >
                            View
                          </Link>
                          {analysis.status === 'completed' && (
                            <Button variant="ghost" size="sm" leftIcon={Download}>
                              Export
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {(totalCount > pageSize || page > 0) && (
              <div className="mt-6 flex items-center justify-between">
                <p className="text-sm text-gray-500">
                  Showing {page * pageSize + 1} to {Math.min((page + 1) * pageSize, totalCount)} of {totalCount} results
                </p>
                <div className="flex gap-2">
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                    leftIcon={ChevronLeft}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => setPage(p => p + 1)}
                    disabled={filteredAnalyses.length < pageSize}
                    rightIcon={ChevronRight}
                  >
                    Next
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}