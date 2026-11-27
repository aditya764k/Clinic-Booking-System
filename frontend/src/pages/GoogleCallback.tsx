import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { LoadingSpinner } from '@/components/LoadingSpinner';

export default function GoogleCallback() {
  const { handleGoogleCallback, user } = useAuth();
  const navigate = useNavigate();
  const hasAttempted = useRef(false);

  useEffect(() => {
    const processCallback = async () => {
      if (hasAttempted.current) return;
      hasAttempted.current = true;

      try {
        await handleGoogleCallback();
      } catch {
        navigate('/login?error=google_auth_failed', { replace: true });
      }
    };

    processCallback();
  }, [handleGoogleCallback, navigate]);

  useEffect(() => {
    if (user && hasAttempted.current) {
      if (user.role === 'doctor') navigate('/doctor/dashboard', { replace: true });
      else if (user.role === 'receptionist') navigate('/receptionist/dashboard', { replace: true });
      else navigate('/patient/dashboard', { replace: true });
    }
  }, [user, navigate]);

  return <LoadingSpinner fullScreen />;
}
