import { useState, FormEvent } from 'react';
import { Input, Button } from './ui';
import type { QuestionResponse } from '../types/api';

interface AskTabProps {
  completed: boolean;
  onRunAsk: (question: string) => Promise<void>;
  answer: QuestionResponse | null;
  askLoading: boolean;
}

export function AskTab({ completed, onRunAsk, answer, askLoading }: AskTabProps) {
  const [question, setQuestion] = useState('');

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (question.trim()) {
      onRunAsk(question.trim());
      setQuestion('');
    }
  };

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold text-gray-900">Ask Cost AI</h3>
      <p className="text-sm text-gray-500">
        Ask a natural-language question about this analysis. Advisory and grounded in the
        detected recommendations when an LLM is configured.
      </p>
      <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3">
        <Input
          placeholder="e.g. Where is my biggest waste this month?"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          disabled={!completed || askLoading}
        />
        <Button type="submit" disabled={!completed || askLoading || !question.trim()} loading={askLoading}>
          Ask
        </Button>
      </form>
      {answer && (
        <div className="p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-gray-800">{answer.answer}</p>
        </div>
      )}
    </div>
  );
}