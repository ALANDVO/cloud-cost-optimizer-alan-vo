import { formatCurrency } from '../utils/helpers';
import type { Analysis } from '../types/api';

interface OverviewTabProps {
  analysis: Analysis;
  completed: boolean;
}

export function OverviewTab({ analysis, completed }: OverviewTabProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Overview</h3>
      <p className="text-sm text-gray-600">
        This analysis covers {analysis.cloud_provider} resources in <strong>{analysis.region}</strong>
        over {analysis.days_analyzed} days of cost and utilization data.
      </p>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="p-4 bg-gray-50 rounded-lg">
          <p className="text-sm font-medium text-gray-500">Total Cost (/mo)</p>
          <p className="mt-1 text-2xl font-bold text-gray-900">{formatCurrency(analysis.total_monthly_cost)}</p>
        </div>
        <div className="p-4 bg-gray-50 rounded-lg">
          <p className="text-sm font-medium text-gray-500">Identified Savings (/mo)</p>
          <p className="mt-1 text-2xl font-bold text-green-600">{formatCurrency(analysis.potential_monthly_savings)}</p>
        </div>
      </div>
      {!completed && analysis.status === 'running' && (
        <p className="text-sm text-gray-500">
          The analysis is still running. The overview and recommendations will update automatically.
        </p>
      )}
    </div>
  );
}