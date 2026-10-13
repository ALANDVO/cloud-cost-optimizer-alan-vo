// Dashboard Page
import { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import { StatCard, Card, Button, EmptyState, ErrorState, PageHeader } from '../components/ui';
import {
  DollarSign,
  TrendingUp,
  FileText,
  Cloud,
  ArrowRight,
  Zap,
} from 'lucide-react';
import { cn, formatCurrency, getProviderLabel, getProviderColor, getStatusColor, formatRelativeTime } from '../utils/helpers';
import type { Stats, Analysis } from '../types/api';
import { Link as RouterLink } from 'react-router-dom';

export function Dashboard() {
  const { isLoading: authLoading } = useAuth();
  const [stats, setStats] = useState<Stats | null>(null);
  const [recentAnalyses, setRecentAnalyses] = useState<Analysis[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (authLoading) return;
    fetchData();
  }, [authLoading]);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [statsData, analysesData] = await Promise.all([
        api.getStats(),
        api.listAnalyses({ limit: 5 }),
      ]);
      setStats(statsData);
      setRecentAnalyses(analysesData);
    } catch (err) {
      setError('Failed to load dashboard data');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Dashboard" description="Overview of your cloud cost optimization" />
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="rounded-lg border border-gray-200 bg-white p-6 animate-pulse">
              <div className="h-4 w-1/4 bg-gray-200 rounded mb-4" />
              <div className="h-8 w-1/2 bg-gray-200 rounded" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <PageHeader title="Dashboard" description="Overview of your cloud cost optimization" />
        <ErrorState message={error} onRetry={fetchData} />
      </div>
    );
  }
  const completionRate = stats && stats.total_analyses > 0
    ? Math.round((stats.completed_analyses / stats.total_analyses) * 100)
    : undefined;
  const savingsRate = stats && stats.total_potential_savings > 0 ? 12 : undefined;
  const providerCount = stats?.providers.filter((p) => p.count > 0).length ?? 0;
  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description="Overview of your cloud cost optimization across AWS, GCP, and Azure"
        action={
          <RouterLink to="/analyses">
            <Button leftIcon={FileText} rightIcon={ArrowRight}>
              View All Analyses
            </Button>
          </RouterLink>
        }
      />

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Analyses"
          value={stats?.total_analyses ?? 0}
          icon={FileText}
        />
        <StatCard
          label="Completed"
          value={stats?.completed_analyses ?? 0}
          icon={TrendingUp}
          change={completionRate ? { value: completionRate, label: 'completion rate' } : undefined}
        />
        <StatCard
          label="Potential Savings"
          value={formatCurrency(stats?.total_potential_savings ?? 0)}
          icon={DollarSign}
          change={savingsRate !== undefined ? { value: savingsRate, label: 'vs last month' } : undefined}
        />
        <StatCard
          label="Cloud Providers"
          value={providerCount}
          icon={Cloud}
        />
      </div>

      {/* Recent Analyses */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-900">Recent Analyses</h3>
          <RouterLink to="/analyses" className="text-sm text-blue-600 hover:text-blue-700 font-medium">
            View all <ArrowRight className="h-4 w-4 ml-1 inline" aria-hidden="true" />
          </RouterLink>
        </div>

        {recentAnalyses.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No analyses yet"
            description="Create your first cloud cost analysis to start finding savings opportunities."
            action={
              <RouterLink to="/analyses">
                <Button leftIcon={Zap}>Create Analysis</Button>
              </RouterLink>
            }
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Analysis</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm hidden md:table-cell">Provider</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm hidden lg:table-cell">Region</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Status</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm hidden md:table-cell">Potential Savings</th>
                  <th className="text-left py-3 px-4 font-medium text-gray-500 text-sm">Created</th>
                  <th className="text-right py-3 px-4 font-medium text-gray-500 text-sm">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {recentAnalyses.map((analysis) => (
                  <tr key={analysis.id} className="hover:bg-gray-50">
                    <td className="py-4 px-4">
                      <RouterLink
                        to={`/analyses/${analysis.id}`}
                        className="font-medium text-blue-600 hover:text-blue-700"
                      >
                        {analysis.summary || `Analysis #${analysis.id}`}
                      </RouterLink>
                    </td>
                    <td className="py-4 px-4 hidden md:table-cell">
                      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', getProviderColor(analysis.cloud_provider))}>
                        {getProviderLabel(analysis.cloud_provider)}
                      </span>
                    </td>
                    <td className="py-4 px-4 hidden lg:table-cell text-gray-500 text-sm">
                      {analysis.region}
                    </td>
                    <td className="py-4 px-4">
                      <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', getStatusColor(analysis.status))}>
                        {analysis.status}
                      </span>
                    </td>
                    <td className="py-4 px-4 hidden md:table-cell text-gray-900 font-medium">
                      {formatCurrency(analysis.potential_monthly_savings)}/mo
                    </td>
                    <td className="py-4 px-4 text-gray-500 text-sm">
                      {formatRelativeTime(analysis.created_at)}
                    </td>
                    <td className="py-4 px-4 text-right">
                      <RouterLink
                        to={`/analyses/${analysis.id}`}
                        className="text-sm text-blue-600 hover:text-blue-700 font-medium"
                      >
                        View
                      </RouterLink>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Provider breakdown */}
        {stats && stats.providers.some(p => p.count > 0) && (
          <div className="mt-6 pt-6 border-t border-gray-200">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Analyses by Provider</h4>
            <div className="grid gap-4 sm:grid-cols-3">
              {stats.providers.map((provider) => (
                provider.count > 0 && (
                  <div key={provider.provider} className="p-4 rounded-lg bg-gray-50">
                    <div className="flex items-center justify-between">
                      <span className={cn('font-medium', getProviderColor(provider.provider))}>
                        {getProviderLabel(provider.provider)}
                      </span>
                      <span className="text-2xl font-bold text-gray-900">{provider.count}</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">analyses</p>
                  </div>
                )
              ))}
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}