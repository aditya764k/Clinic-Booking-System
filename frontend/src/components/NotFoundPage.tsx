import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 p-6 text-center">
      <div className="text-6xl font-hero text-slate-300 mb-4">404</div>
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Page Not Found</h1>
      <p className="text-slate-500 mb-8">The page you're looking for doesn't exist or has been moved.</p>
      <Button onClick={() => navigate('/')}>Return Home</Button>
    </div>
  );
}
