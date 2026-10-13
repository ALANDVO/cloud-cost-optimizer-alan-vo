// Analysis Detail - view analysis, recommendations, and run workflows
import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Card, Button, Badge, StatCard, LoadingState, ErrorState, PageHeader } from '../components/ui';
import {
  Download, Search, DollarSign, AlertCircle, RefreshCw, Send, Target,
  BarChart3,
} from 'lucide-react';
import { cn, formatCurrency, getProviderLabel } from '../utils/helpers';
import type { Analysis, OptimizationPlan, QuestionResponse } from '../types/api';
import { OverviewTab } from '../components/OverviewTab';
import { WasteTab } from '../components/WasteTab';
import { RightsizeTab } from '../components/RightsizeTab';
import { AskTab } from '../components/AskTab';
import { PlanTab } from '../components/PlanTab';

type Tab = 'overview' | 'waste' | 'rightsize' | 'ask' | 'plan';

function StatusBadge({ status }: { status: string }) {
  return (
    <Badge variant={status === 'completed' ? 'success' : status === 'failed' ? 'danger' : 'warning'}>
      {status}
    </Badge>
  );
}

export function AnalysisDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const analysisId = Number(id);

  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>('overview');

  // Rightsize form state
  const [rightsizeResults, setRightsizeResults] = useState<unknown[]>([]);
  const [rightsizeLoading, setRightsizeLoading] = useState(false);

  // Ask form state
  const [answer, setAnswer] = useState<QuestionResponse | null>(null);
  const [askLoading, setAskLoading] = useState(false);

  // Plan form state
  const [targetSavings, setTargetSavings] = useState<number>(100);
  const [plans] = useState<OptimizationPlan[]>([]);
  const [planLoading, setPlanLoading] = useState(false);

  // Initial fetch + polling while running/pending
  useEffect(() => {
    let cancelled = false;
    let interval: number | undefined;

    const fetchAnalysis = async () => {
      try {
        const data = await api.getAnalysis(analysisId);
        if (!cancelled) {
          setAnalysis(data);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load analysis');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    fetchAnalysis();

    // Poll while running/pending
    if (!loading) {
      interval = setInterval(() => {
        if (analysis?.status === 'running' || analysis?.status === 'pending') {
          fetchAnalysis();
        }
      }, 5000);
    }

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [analysisId, loading, analysis?.status]);

  const runRightsize = async (id: string) => {
    setRightsizeLoading(true);
    try {
      const results = await api.getRightsizeRecommendations(analysisId, id);
      setRightsizeResults(results);
    } catch (err) {
      setRightsizeResults([{ error: err instanceof Error ? err.message : 'Failed' }]);
    } finally {
      setRightsizeLoading(false);
    }
  };

  const runAsk = async (q: string) => {
    setAskLoading(true);
    try {
      const resp = await api.askQuestion(analysisId, q);
      setAnswer(resp);
    } catch (err) {
      setAnswer({ answer: err instanceof Error ? err.message : 'Failed to get answer' });
    } finally {
      setAskLoading(false);
    }
  };

  const generatePlan = async () => {
    setPlanLoading(true);
    try {
      await api.createOptimizationPlan(analysisId, { target_savings: targetSavings });
    } catch (err) {
      console.error('Failed to generate plan:', err);
    } finally {
      setPlanLoading(false);
    }
  };

  const exportJson = () => {
    if (analysis) {
      const blob = new Blob([JSON.stringify(analysis, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `analysis-${analysis.id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
  };

  const handleRetry = () => {
    setLoading(true);
    setError(null);
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Loading analysis…" />
        <LoadingState message="Fetching analysis data…" />
      </div>
    );
  }

  if (error || !analysis) {
    return (
      <div className="space-y-6">
        <PageHeader title="Analysis not found" />
        <ErrorState message={error || 'Analysis not found'} onRetry={handleRetry} />
      </div>
    );
  }

  const completed = analysis.status === 'completed';
  const costByService = analysis.raw_data?.by_service as Record<string, number> | undefined;
  const savingsRate = analysis.total_monthly_cost
    ? Math.round((analysis.potential_monthly_savings / analysis.total_monthly_cost) * 100)
    : 0;

  const tabs = [
    { key: 'overview', label: 'Overview', icon: BarChart3 },
    { key: 'waste', label: 'Waste Detection', icon: AlertCircle },
    { key: 'rightsize', label: 'Right-size', icon: Search },
    { key: 'ask', label: 'Ask Cost AI', icon: Send },
    { key: 'plan', label: 'Optimization Plan', icon: Target },
  ] as const;

  return (
    <div className="space-y-6">
      <PageHeader
        title={analysis.summary || `Analysis #${analysis.id}`}
        description={`Costs analyzed over ${analysis.days_analyzed} days`}
        action={
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => navigate('/analyses')}>Back to analyses</Button>
            <Button variant="secondary" size="sm" leftIcon={Download} onClick={exportJson} disabled={!completed}>
              Export
            </Button>
          </div>
        }
      />

      {/* Summary cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Provider" value={getProviderLabel(analysis.cloud_provider)} icon={undefined} />
        <StatCard label="Region" value={analysis.region} />
        <StatCard label="Total Monthly Cost" value={formatCurrency(analysis.total_monthly_cost)} icon={DollarSign} />
        <StatCard
          label="Potential Savings"
          value={formatCurrency(analysis.potential_monthly_savings)}
          change={completed && analysis.potential_monthly_savings > 0
            ? { value: savingsRate, label: 'of spend' }
            : undefined}
        />
      </div>

      {/* Status + summary card */}
      <Card>
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <StatusBadge status={analysis.status} />
            <span className="text-sm text-gray-500">
              {analysis.status === 'running' ? 'Analyzing your cloud resources…' :
               analysis.status === 'completed' ? `${analysis.recommendations?.length ?? 0} recommendations found` :
               analysis.status === 'failed' ? 'Analysis encountered an error' : 'Queued'}
            </span>
          </div>
          {analysis.status === 'running' && <RefreshCw className="h-4 w-4 animate-spin text-gray-400" aria-hidden="true" />}
        </div>
        <p className="text-sm text-gray-600">{analysis.summary || 'No summary available yet.'}</p>
        {completed && analysis.llm_insights && (
          <div className="mt-4 p-4 bg-blue-50 rounded-lg">
            <p className="text-sm text-gray-800">{analysis.llm_insights}</p>
          </div>
        )}
      </Card>

      {/* Cost by service */}
      {completed && costByService && Object.keys(costByService).length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Cost by Service</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(costByService).map(([svc, cost]) => (
              <div key={svc} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="text-sm text-gray-700">{svc}</span>
                <span className="font-medium text-gray-900">{formatCurrency(cost)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Tabs for workflows */}
      <nav className="flex gap-1 border-b border-gray-200 overflow-x-auto" aria-label="Analysis workflows">
        {tabs.map((t) => {
          const Icon = t.icon;
          return (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={cn(
                'flex items-center gap-2 px-4 py-2 border-b-2 text-sm font-medium transition-colors whitespace-nowrap',
                activeTab === t.key
                  ? 'border-blue-600 text-blue-700'
                  : 'border-transparent text-gray-600 hover:text-gray-900 hover:bg-gray-50'
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
              {t.label}
            </button>
          );
        })}
      </nav>

      {/* Tab panels */}
      <Card>
        {activeTab === 'overview' && <OverviewTab analysis={analysis} completed={completed} />}
        {activeTab === 'waste' && <WasteTab analysis={analysis} completed={completed} />}
        {activeTab === 'rightsize' && (
          <RightsizeTab
            completed={completed}
            onRunRightsize={runRightsize}
            rightsizeResults={rightsizeResults}
            rightsizeLoading={rightsizeLoading}
          />
        )}
        {activeTab === 'ask' && (
          <AskTab
            completed={completed}
            onRunAsk={runAsk}
            answer={answer}
            askLoading={askLoading}
          />
        )}
        {activeTab === 'plan' && (
          <PlanTab
            completed={completed}
            plans={plans}
            targetSavings={targetSavings}
            onTargetSavingsChange={setTargetSavings}
            onGeneratePlan={generatePlan}
            planLoading={planLoading}
          />
        )}
      </Card>
    </div>
  );
}