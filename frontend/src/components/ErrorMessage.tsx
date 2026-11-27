import { AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorMessageProps {
  error: string;
  onRetry?: () => void;
}

export function ErrorMessage({ error, onRetry }: ErrorMessageProps) {
  return (
    <div className="p-6 bg-red-50 rounded-xl border border-red-100 flex flex-col items-center text-center max-w-md mx-auto my-8">
      <AlertCircle className="w-10 h-10 text-red-500 mb-3" />
      <h3 className="text-red-900 font-semibold mb-1">Something went wrong</h3>
      <p className="text-sm text-red-700 mb-4">{error}</p>
      {onRetry && (
        <Button variant="outline" onClick={onRetry} className="bg-white hover:bg-red-50 text-red-700 border-red-200 hover:border-red-300">
          Try Again
        </Button>
      )}
    </div>
  );
}
