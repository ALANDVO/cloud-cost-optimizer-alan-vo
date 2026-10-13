import { Badge } from './ui';
import { formatCurrency, getRecommendationTypeLabel } from '../utils/helpers';
import type { Analysis } from '../types/api';

interface RecommendationRowProps {
  rec: Analysis['recommendations'][number];
}

export function RecommendationRow({ rec }: RecommendationRowProps) {
  return (
    <div className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <Badge variant="default">{getRecommendationTypeLabel(rec.type)}</Badge>
            <span className="text-sm font-medium text-gray-900 truncate">{rec.resource_type}</span>
            <span className="text-sm text-gray-500">{rec.resource_id}</span>
          </div>
          <p className="mt-1 text-sm text-gray-600">{rec.recommended_action}</p>
        </div>
        <div className="flex items-center gap-4 shrink-0">
          <div className="text-right">
            <p className="text-sm text-gray-500">Current</p>
            <p className="font-medium text-gray-900">{formatCurrency(rec.current_cost_monthly)}/mo</p>
          </div>
          <div className="text-right">
            <p className="text-sm text-gray-500">Savings</p>
            <p className="font-medium text-green-600">{formatCurrency(rec.estimated_savings_monthly)}/mo</p>
          </div>
        </div>
      </div>
    </div>
  );
}