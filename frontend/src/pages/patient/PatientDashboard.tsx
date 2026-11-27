import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { SidebarLayout } from '@/components/SidebarLayout';
import { appointmentApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { PageLoader } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { 
  Clock, CheckCircle, Receipt, Activity, LayoutDashboard, CalendarPlus, CalendarDays, FileText, User
} from 'lucide-react';
import { format } from 'date-fns';

export default function PatientDashboard() {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [isCancelling, setIsCancelling] = useState<number | null>(null);

  const navLinks = [
    { label: 'Dashboard', href: '/patient/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
    { label: 'Book Appointment', href: '/patient/book', icon: <CalendarPlus className="w-5 h-5" /> },
    { label: 'My Appointments', href: '/patient/appointments', icon: <CalendarDays className="w-5 h-5" /> },
    { label: 'My Invoices', href: '/patient/invoices', icon: <FileText className="w-5 h-5" /> },
    { label: 'Profile', href: '/patient/profile', icon: <User className="w-5 h-5" /> },
  ];

  const fetchAppointments = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await appointmentApi.getMyQueue();
      setAppointments(data);
    } catch (err: any) {
      setError(err.message || 'Failed to load appointments');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, []);

  const handleCancel = async (id: number) => {
    if (!window.confirm("Are you sure you want to cancel this appointment?")) return;
    
    setIsCancelling(id);
    try {
      await appointmentApi.cancel(id);
      toast.success("Appointment cancelled successfully.");
      fetchAppointments();
    } catch (err: any) {
      toast.error(err.message || "Cannot cancel appointment");
    } finally {
      setIsCancelling(null);
    }
  };

  // Derive stats
  const upcoming = appointments.filter(a => ['booked', 'checked_in', 'in_consultation'].includes(a.status));
  const past = appointments.filter(a => ['completed', 'paid'].includes(a.status));
  const pendingBilling = appointments.filter(a => a.status === 'billing_pending' || (a.status === 'completed' && !a.invoice));

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'booked': return <span className="bg-blue-50 text-blue-600 border border-blue-200 px-2 py-1 rounded-full text-xs font-medium">Booked</span>;
      case 'checked_in': return <span className="bg-amber-50 text-amber-600 border border-amber-200 px-2 py-1 rounded-full text-xs font-medium">Checked In</span>;
      case 'in_consultation': return (
        <span className="bg-indigo-50 text-indigo-600 border border-indigo-200 px-2 py-1 rounded-full text-xs font-medium flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></span> In Consultation
        </span>
      );
      case 'completed': return <span className="bg-teal-50 text-teal-600 border border-teal-200 px-2 py-1 rounded-full text-xs font-medium">Completed</span>;
      case 'billing_pending': return <span className="bg-orange-50 text-orange-600 border border-orange-200 px-2 py-1 rounded-full text-xs font-medium">Billing Pending</span>;
      case 'paid': return <span className="bg-emerald-50 text-emerald-600 border border-emerald-200 px-2 py-1 rounded-full text-xs font-medium">Paid</span>;
      case 'cancelled': return <span className="bg-red-50 text-red-600 border border-red-200 px-2 py-1 rounded-full text-xs font-medium">Cancelled</span>;
      case 'no_show': return <span className="bg-slate-50 text-slate-600 border border-slate-200 px-2 py-1 rounded-full text-xs font-medium">No Show</span>;
      default: return <span className="bg-slate-100 text-slate-600 px-2 py-1 rounded-full text-xs">{status}</span>;
    }
  };

  return (
    <SidebarLayout role="patient" links={navLinks}>
      <div className="max-w-5xl mx-auto space-y-8">
        {/* Welcome Banner */}
        <div className="flex items-center gap-4 bg-white p-6 rounded-2xl shadow-level-1 border border-slate-200">
          <div className="w-14 h-14 rounded-full bg-sky-50 flex items-center justify-center text-sky-600">
            <Activity className="w-7 h-7" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              {getGreeting()}, {(user?.full_name || 'User').split(' ')[0]}!
            </h1>
            <p className="text-slate-500">Welcome to your patient dashboard.</p>
          </div>
        </div>

        {loading ? (
          <PageLoader />
        ) : error ? (
          <ErrorMessage error={error} onRetry={fetchAppointments} />
        ) : (
          <>
            {/* Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white rounded-2xl p-6 shadow-level-2 border border-slate-200">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-500 mb-1">Upcoming Appointments</p>
                    <h3 className="text-3xl font-bold text-sky-600">{upcoming.length}</h3>
                  </div>
                  <div className="w-10 h-10 rounded-full bg-sky-50 flex items-center justify-center text-sky-500">
                    <Clock className="w-5 h-5" />
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-2xl p-6 shadow-level-2 border border-slate-200">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-500 mb-1">Past Visits</p>
                    <h3 className="text-3xl font-bold text-emerald-600">{past.length}</h3>
                  </div>
                  <div className="w-10 h-10 rounded-full bg-emerald-50 flex items-center justify-center text-emerald-500">
                    <CheckCircle className="w-5 h-5" />
                  </div>
                </div>
              </div>
              <div className="bg-white rounded-2xl p-6 shadow-level-2 border border-slate-200">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="text-sm font-medium text-slate-500 mb-1">Pending Invoices</p>
                    <h3 className="text-3xl font-bold text-amber-600">{pendingBilling.length}</h3>
                  </div>
                  <div className="w-10 h-10 rounded-full bg-amber-50 flex items-center justify-center text-amber-500">
                    <Receipt className="w-5 h-5" />
                  </div>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              {/* Upcoming Appointments */}
              <div className="lg:col-span-2 space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-slate-900">Upcoming Appointments</h2>
                  <Link to="/patient/appointments" className="text-sm font-medium text-primary hover:underline">
                    View All
                  </Link>
                </div>
                
                {upcoming.length === 0 ? (
                  <div className="bg-white rounded-2xl p-8 text-center border border-slate-200 shadow-sm border-dashed">
                    <CalendarDays className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                    <h3 className="font-semibold text-slate-700 mb-1">No upcoming appointments</h3>
                    <p className="text-slate-500 text-sm mb-4">You're all caught up! Need to see a doctor?</p>
                    <Link to="/patient/book">
                      <Button className="bg-primary hover:bg-blue-800 text-white">
                        Book Now
                      </Button>
                    </Link>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {upcoming.slice(0, 3).map(app => (
                      <div key={app.id} className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                        <div className="flex items-start gap-4">
                          <div className="w-12 h-12 rounded-xl bg-slate-50 border border-slate-100 flex flex-col items-center justify-center shrink-0">
                            <span className="text-xs font-medium text-slate-500 uppercase">
                              {format(new Date(app.slot_start), 'MMM')}
                            </span>
                            <span className="text-lg font-bold text-slate-900 leading-tight">
                              {format(new Date(app.slot_start), 'dd')}
                            </span>
                          </div>
                          <div>
                            <h4 className="font-semibold text-slate-900 mb-1">Dr. {app.doctor_name}</h4>
                            <div className="flex items-center gap-3 text-sm text-slate-500">
                              <span className="flex items-center gap-1"><Clock className="w-3 h-3" /> {format(new Date(app.slot_start), 'HH:mm')}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-4">
                          {getStatusBadge(app.status)}
                          {app.status === 'booked' && (
                            <Button 
                              variant="outline" 
                              size="sm" 
                              className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
                              onClick={() => handleCancel(app.id)}
                              disabled={isCancelling === app.id}
                            >
                              Cancel
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Sidebar Cards */}
              <div className="space-y-6">
                {/* Shortcut Card */}
                <Link to="/patient/book" className="block bg-gradient-to-br from-primary to-sky-500 rounded-2xl p-6 text-white shadow-level-2 hover:shadow-level-3 transition-shadow relative overflow-hidden group">
                  <div className="relative z-10">
                    <CalendarPlus className="w-8 h-8 mb-4 text-blue-100" />
                    <h3 className="text-lg font-bold mb-1">Book Appointment</h3>
                    <p className="text-blue-100 text-sm">Schedule a new visit instantly.</p>
                  </div>
                  <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-white opacity-10 rounded-full group-hover:scale-150 transition-transform duration-500"></div>
                </Link>

                {/* Recent Activity */}
                <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm">
                  <h3 className="font-bold text-slate-900 mb-4 flex items-center gap-2">
                    <History className="w-4 h-4 text-slate-400" /> Recent Activity
                  </h3>
                  {past.length === 0 ? (
                    <p className="text-sm text-slate-500 text-center py-4">No recent past visits.</p>
                  ) : (
                    <div className="space-y-4">
                      {past.slice(0, 3).map(app => (
                        <div key={app.id} className="flex items-start gap-3 pb-4 border-b border-slate-100 last:border-0 last:pb-0">
                          <div className="w-2 h-2 mt-1.5 rounded-full bg-emerald-400 shrink-0"></div>
                          <div>
                            <p className="text-sm font-medium text-slate-900">Visit with Dr. {app.doctor_name}</p>
                            <p className="text-xs text-slate-500">{format(new Date(app.slot_start), 'MMM dd, yyyy')}</p>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </SidebarLayout>
  );
}

function History(props: any) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M12 7v5l4 2" />
    </svg>
  );
}
