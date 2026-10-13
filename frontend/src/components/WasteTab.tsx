import type { Analysis } from '../types/api';
import { RecommendationRow } from './RecommendationRow';

interface WasteTabProps {
  analysis: Analysis;
  completed: boolean;
}

export function WasteTab({ analysis, completed }: WasteTabProps) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Waste Detection</h3>
      {analysis.status === 'running' && (
        <p className="text-sm text-gray-500">Waste findings appear here once the analysis completes.</p>
      )}
      {analysis.recommendations && analysis.recommendations.length > 0 ? (
        <div className="space-y-2">
          {analysis.recommendations.map((rec) => (
            <RecommendationRow key={rec.id} rec={rec} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-gray-500">
          {completed ? 'No waste detected in this analysis.' : 'No waste detected yet.'}
        </p>
      )}
    </div>
  );
}