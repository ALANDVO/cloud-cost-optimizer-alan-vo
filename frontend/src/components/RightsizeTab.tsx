import { useState, FormEvent } from 'react';
import { Input, Button } from './ui';

interface RightsizeTabProps {
  completed: boolean;
  onRunRightsize: (resourceId: string) => Promise<void>;
  rightsizeResults: unknown[];
  rightsizeLoading: boolean;
}

export function RightsizeTab({ completed, onRunRightsize, rightsizeResults, rightsizeLoading }: RightsizeTabProps) {
  const [resourceId, setResourceId] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (resourceId.trim()) {
      onRunRightsize(resourceId.trim());
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Right-size a Resource</h3>
      <p className="text-sm text-gray-500">
        Enter a resource id (e.g. an instance id) to get a tailored sizing recommendation.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <Input
          placeholder="Resource id, e.g. i-1234567890abcdef0"
          value={resourceId}
          onChange={(e) => setResourceId(e.target.value)}
          disabled={!completed || rightsizeLoading}
        />
        <Button type="submit" disabled={!completed || rightsizeLoading || !resourceId.trim()} loading={rightsizeLoading}>
          Analyze
        </Button>
      </form>
      {rightsizeResults.length > 0 && (
        <div className="space-y-2">
          {rightsizeResults.map((r, i) => (
            <div key={i} className="p-3 border border-gray-200 rounded-lg">
              <pre className="text-xs text-gray-700 whitespace-pre-wrap">{JSON.stringify(r, null, 2)}</pre>
            </div>
          ))}
        </div>
      )}
      {rightsizeResults.length === 0 && !rightsizeLoading && resourceId && (
        <p className="text-sm text-gray-500">No right-size recommendation returned for that resource.</p>
      )}
    </div>
  );
}