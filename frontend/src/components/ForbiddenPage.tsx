import { ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useNavigate } from 'react-router-dom';

export function ForbiddenPage() {
  const navigate = useNavigate();
  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-50 p-6 text-center">
      <ShieldAlert className="w-16 h-16 text-red-500 mb-6" />
      <h1 className="text-3xl font-bold text-slate-900 mb-2">Access Denied</h1>
      <p className="text-slate-500 mb-8 max-w-md">
        You do not have permission to view this page. Ensure you are logged in with the correct role.
      </p>
      <Button onClick={() => navigate('/')}>Return to Homepage</Button>
    </div>
  );
}
