import { Input, Button, Badge } from './ui';
import { formatCurrency } from '../utils/helpers';
import type { OptimizationPlan } from '../types/api';

interface PlanTabProps {
  completed: boolean;
  plans: OptimizationPlan[];
  targetSavings: number;
  onTargetSavingsChange: (value: number) => void;
  onGeneratePlan: () => Promise<void>;
  planLoading: boolean;
}

export function PlanTab({ completed, plans, targetSavings, onTargetSavingsChange, onGeneratePlan, planLoading }: PlanTabProps) {
  if (!completed) {
    return (
      <div className="space-y-4">
        <h3 className="text-lg font-semibold text-gray-900">Optimization Plan</h3>
        <p className="text-sm text-gray-500">Optimization plans can be generated once the analysis completes.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Optimization Plan</h3>
      <form
        onSubmit={(e) => { e.preventDefault(); onGeneratePlan(); }}
        className="flex flex-col sm:flex-row gap-3 items-end"
      >
        <Input
          label="Target monthly savings (USD)"
          type="number"
          min={1}
          value={targetSavings}
          onChange={(e) => onTargetSavingsChange(Math.max(1, Number(e.target.value) || 1))}
          disabled={planLoading}
        />
        <Button type="submit" disabled={planLoading} loading={planLoading}>
          Generate Plan
        </Button>
      </form>
      {plans.length > 0 ? (
        <div className="space-y-4">
          {plans.map((p) => (
            <div key={p.id} className="p-4 border border-gray-200 rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">Plan #{p.id}</h4>
                <Badge variant="success">
                  {formatCurrency(p.projected_savings_monthly)}/mo projected
                </Badge>
              </div>
              <p className="text-sm text-gray-600 mb-2">Timeline: {p.timeline_weeks} weeks</p>
              {p.risk_assessment && <p className="text-sm text-gray-600 mb-2">{p.risk_assessment}</p>}
              <ul className="space-y-1">
                {(p.actions ?? []).map((a, i) => (
                  <li key={i} className="text-sm text-gray-700">
                    <span className="font-medium">{a.action}</span> — {a.type} ({a.effort} effort, {a.risk} risk): {formatCurrency(a.estimated_savings)}/mo
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500">No optimization plans generated yet.</p>
      )}
    </div>
  );
}