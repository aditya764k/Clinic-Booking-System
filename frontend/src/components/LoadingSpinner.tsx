import { Loader2 } from 'lucide-react';

export function LoadingSpinner({ fullScreen = false }: { fullScreen?: boolean }) {
  const containerClasses = fullScreen
    ? 'fixed inset-0 flex flex-col items-center justify-center bg-slate-50 z-50'
    : 'flex flex-col items-center justify-center p-8 w-full';

  return (
    <div className={containerClasses}>
      <Loader2 className="h-10 w-10 animate-spin text-primary mb-4" />
      <h2 className="text-xl font-hero text-slate-900">Trimurti Clinic</h2>
      <p className="text-slate-500 text-sm animate-pulse">Loading...</p>
    </div>
  );
}

export function PageLoader() {
  return (
    <div className="flex justify-center p-12">
      <Loader2 className="h-8 w-8 animate-spin text-primary opacity-50" />
    </div>
  );
}
