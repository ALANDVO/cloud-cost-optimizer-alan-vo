// New Analysis - form to kick off a cost analysis
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { Card, Button, Input, Select, PageHeader, ErrorState } from '../components/ui';
import { Cloud, BarChart3 } from 'lucide-react';
import type { CloudProvider, AnalysisCreate } from '../types/api';
import { getRegionSuggestions, validateRegion } from '../utils/helpers';

const PROVIDERS: { value: CloudProvider; label: string }[] = [
  { value: 'aws', label: 'AWS' },
  { value: 'gcp', label: 'GCP' },
  { value: 'azure', label: 'Azure' },
];

export function NewAnalysis() {
  const navigate = useNavigate();
  const [provider, setProvider] = useState<CloudProvider>('aws');
  const [region, setRegion] = useState('');
  const [days, setDays] = useState(30);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!region.trim()) {
      setError('Region is required');
      return;
    }
    if (!validateRegion(provider, region.trim())) {
      setError(`Invalid region for ${provider.toUpperCase()}. Please select a valid region.`);
      return;
    }
    try {
      setSubmitting(true);
      const payload: AnalysisCreate = { cloud_provider: provider, region: region.trim(), days };
      const created = await api.createAnalysis(payload);
      navigate(`/analyses/${created.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to start analysis');
    } finally {
      setSubmitting(false);
    }
  };

  const regionSuggestions = getRegionSuggestions(provider);

  return (
    <div className="space-y-6">
      <PageHeader
        title="New Cost Analysis"
        description="Analyze cloud spend and find waste across AWS, GCP, and Azure"
      />

      {error && <ErrorState message={error} onRetry={() => setError(null)} />}

      <Card className="max-w-2xl">
        <form onSubmit={handleSubmit} className="space-y-6">
          <Select
            label="Cloud Provider"
            value={provider}
            onChange={(e) => setProvider(e.target.value as CloudProvider)}
            options={PROVIDERS}
          />
          <Input
            label="Region"
            placeholder="e.g. us-east-1, us-central1, eastus"
            value={region}
            onChange={(e) => setRegion(e.target.value)}
            required
            list={`region-suggestions-${provider}`}
          />
          <datalist id={`region-suggestions-${provider}`}>
            {regionSuggestions.map((r) => (
              <option key={r} value={r} />
            ))}
          </datalist>
          <Input
            label="Days of history"
            type="number"
            min={1}
            max={365}
            value={days}
            onChange={(e) => setDays(Math.min(365, Math.max(1, Number(e.target.value))))}
            helperText="Number of days of cost data to analyze (1–365)"
            required
          />
          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Cloud className="h-4 w-4" />
              <span>Results appear in 5–15 seconds; the page polls automatically.</span>
            </div>
            <Button type="submit" leftIcon={BarChart3} loading={submitting} disabled={submitting}>
              {submitting ? 'Starting...' : 'Start Analysis'}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
