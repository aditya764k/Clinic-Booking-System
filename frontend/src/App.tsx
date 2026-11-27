import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Toaster } from '@/components/ui/sonner';
import { ProtectedRoute } from './components/ProtectedRoute';
import { NotFoundPage } from './components/NotFoundPage';

// We'll lazy load these later or just import directly for now.
// For the single-pass build, we'll create these files shortly.
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import GoogleCallback from './pages/GoogleCallback';

import PatientDashboard from './pages/patient/PatientDashboard';
import BookAppointment from './pages/patient/BookAppointment';
import MyAppointments from './pages/patient/MyAppointments';
import MyInvoices from './pages/patient/MyInvoices';
import PatientProfile from './pages/patient/PatientProfile';

import DoctorDashboard from './pages/doctor/DoctorDashboard';
import Consultation from './pages/doctor/Consultation';
import DoctorSettings from './pages/doctor/DoctorSettings';
import AddColleague from './pages/doctor/AddColleague';
import DoctorProfile from './pages/doctor/DoctorProfile';

import ReceptionistDashboard from './pages/receptionist/ReceptionistDashboard';
import WalkIn from './pages/receptionist/WalkIn';

// Helper component to redirect authenticated users away from public auth routes
function PublicOnlyRoute({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth();
  if (isLoading) return null;
  if (user) {
    if (user.role === 'patient') return <Navigate to="/patient/dashboard" replace />;
    if (user.role === 'doctor') return <Navigate to="/doctor/dashboard" replace />;
    if (user.role === 'receptionist') return <Navigate to="/receptionist/dashboard" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Home />} />
        
        <Route path="/login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
        <Route path="/register" element={<PublicOnlyRoute><Register /></PublicOnlyRoute>} />
        <Route path="/auth/google/callback" element={<GoogleCallback />} />

        {/* Patient Routes */}
        <Route element={<ProtectedRoute allowedRoles={['patient']} />}>
          <Route path="/patient/dashboard" element={<PatientDashboard />} />
          <Route path="/patient/book" element={<BookAppointment />} />
          <Route path="/patient/appointments" element={<MyAppointments />} />
          <Route path="/patient/invoices" element={<MyInvoices />} />
          <Route path="/patient/profile" element={<PatientProfile />} />
        </Route>

        {/* Doctor Routes */}
        <Route element={<ProtectedRoute allowedRoles={['doctor']} />}>
          <Route path="/doctor/dashboard" element={<DoctorDashboard />} />
          <Route path="/doctor/consultation/:id" element={<Consultation />} />
          <Route path="/doctor/settings" element={<DoctorSettings />} />
          <Route path="/doctor/add-colleague" element={<AddColleague />} />
          <Route path="/doctor/profile" element={<DoctorProfile />} />
        </Route>

        {/* Receptionist Routes */}
        <Route element={<ProtectedRoute allowedRoles={['receptionist']} />}>
          <Route path="/receptionist/dashboard" element={<ReceptionistDashboard />} />
          <Route path="/receptionist/walk-in" element={<WalkIn />} />
        </Route>

        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      <Toaster position="top-right" richColors />
    </AuthProvider>
  );
}
