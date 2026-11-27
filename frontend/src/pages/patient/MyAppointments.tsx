import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { SidebarLayout } from '@/components/SidebarLayout';
import { appointmentApi, clinicalNoteApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { PageLoader } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { 
  LayoutDashboard, CalendarPlus, CalendarDays, FileText, Clock, Info, User
} from 'lucide-react';
import { format } from 'date-fns';

const navLinks = [
  { label: 'Dashboard', href: '/patient/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Book Appointment', href: '/patient/book', icon: <CalendarPlus className="w-5 h-5" /> },
  { label: 'My Appointments', href: '/patient/appointments', icon: <CalendarDays className="w-5 h-5" /> },
  { label: 'My Invoices', href: '/patient/invoices', icon: <FileText className="w-5 h-5" /> },
  { label: 'Profile', href: '/patient/profile', icon: <User className="w-5 h-5" /> },
];

export default function MyAppointments() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [appointments, setAppointments] = useState<any[]>([]);
  const [isCancelling, setIsCancelling] = useState<number | null>(null);

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

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'booked': return <span className="bg-sky-50 text-sky-600 border border-sky-200 px-2.5 py-1 rounded-full text-xs font-semibold">Booked</span>;
      case 'checked_in': return <span className="bg-amber-50 text-amber-600 border border-amber-200 px-2.5 py-1 rounded-full text-xs font-semibold">Checked In</span>;
      case 'in_consultation': return (
        <span className="bg-indigo-50 text-indigo-600 border border-indigo-200 px-2.5 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span> Active
        </span>
      );
      case 'completed': return <span className="bg-teal-50 text-teal-600 border border-teal-200 px-2.5 py-1 rounded-full text-xs font-semibold">Completed</span>;
      case 'billing_pending': return <span className="bg-orange-50 text-orange-600 border border-orange-200 px-2.5 py-1 rounded-full text-xs font-semibold">Billing Pending</span>;
      case 'paid': return <span className="bg-emerald-50 text-emerald-600 border border-emerald-200 px-2.5 py-1 rounded-full text-xs font-semibold">Paid</span>;
      case 'cancelled': return <span className="bg-red-50 text-red-600 border border-red-200 px-2.5 py-1 rounded-full text-xs font-semibold">Cancelled</span>;
      case 'no_show': return <span className="bg-slate-50 text-slate-600 border border-slate-200 px-2.5 py-1 rounded-full text-xs font-semibold">No Show</span>;
      default: return <span className="bg-slate-100 text-slate-600 px-2.5 py-1 rounded-full text-xs font-semibold">{status}</span>;
    }
  };

  const upcoming = appointments.filter(a => ['booked', 'checked_in', 'in_consultation'].includes(a.status));
  const past = appointments.filter(a => ['completed', 'billing_pending', 'paid'].includes(a.status));
  const cancelled = appointments.filter(a => ['cancelled', 'no_show'].includes(a.status));

  const AppointmentCard = ({ app, isUpcoming }: { app: any, isUpcoming: boolean }) => (
    <div className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-4 transition-all hover:shadow-md">
      <div className="flex items-start gap-4">
        <div className="w-14 h-14 rounded-xl bg-slate-50 border border-slate-100 flex flex-col items-center justify-center shrink-0 shadow-inner">
          <span className="text-xs font-medium text-slate-500 uppercase">
            {format(new Date(app.slot_start), 'MMM')}
          </span>
          <span className="text-xl font-bold text-slate-900 leading-tight">
            {format(new Date(app.slot_start), 'dd')}
          </span>
        </div>
        <div>
          <h4 className="text-lg font-semibold text-slate-900 mb-1">{app.doctor_name.startsWith('Dr.') ? app.doctor_name : `Dr. ${app.doctor_name}`}</h4>
          <div className="flex items-center gap-3 text-sm text-slate-500 mb-2">
            <span className="flex items-center gap-1.5 font-medium"><Clock className="w-4 h-4 text-primary" /> {format(new Date(app.slot_start), 'HH:mm')}</span>
          </div>
          {getStatusBadge(app.status)}
        </div>
      </div>
      
      <div className="flex sm:flex-col justify-end gap-2 shrink-0">
        {isUpcoming && app.status === 'booked' ? (
          <div className="flex gap-2 flex-col sm:flex-row">
            {app.invoice?.id && app.invoice?.status === 'paid' && (
              <Button 
                variant="outline" 
                className="text-emerald-600 border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700 font-medium text-sm h-9"
                onClick={async () => {
                  try {
                    const res = await appointmentApi.downloadInvoice(app.invoice.id);
                    window.open(res.url, '_blank');
                  } catch(e) {
                    toast.error("Could not download receipt");
                  }
                }}
              >
                <FileText className="w-4 h-4 mr-2" /> Receipt
              </Button>
            )}
            <Button 
              variant="outline" 
              className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700 font-medium text-sm h-9"
              onClick={() => handleCancel(app.id)}
              disabled={isCancelling === app.id}
            >
              {isCancelling === app.id ? 'Cancelling...' : 'Cancel'}
            </Button>
          </div>
        ) : isUpcoming ? (
          <div className="flex items-center gap-2 text-xs text-amber-600 bg-amber-50 px-3 py-2 rounded-lg border border-amber-100">
            <Info className="w-4 h-4" /> Cannot cancel now
          </div>
        ) : (!isUpcoming && (app.status === 'completed' || app.status === 'billing_pending' || app.status === 'paid')) ? (
          <div className="flex gap-2 flex-col sm:flex-row">
            {app.invoice?.id && app.invoice?.status === 'paid' && (
              <Button 
                variant="outline" 
                className="text-emerald-600 border-emerald-200 hover:bg-emerald-50 hover:text-emerald-700 font-medium text-sm h-9"
                onClick={async () => {
                  try {
                    const res = await appointmentApi.downloadInvoice(app.invoice.id);
                    window.open(res.url, '_blank');
                  } catch(e) {
                    toast.error("Could not download receipt");
                  }
                }}
              >
                <FileText className="w-4 h-4 mr-2" /> Receipt
              </Button>
            )}
            <Button 
              variant="outline" 
              className="text-indigo-600 border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700 font-medium text-sm h-9"
              onClick={async () => {
                try {
                  const res = await clinicalNoteApi.downloadPrescription(app.id);
                  window.open(res.url, '_blank');
                } catch (err: any) {
                  toast.error("Prescription not available yet.");
                }
              }}
            >
              <FileText className="w-4 h-4 mr-2" /> Download Prescription
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  );

  return (
    <SidebarLayout role="patient" links={navLinks}>
      <div className="max-w-4xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">My Appointments</h1>
            <p className="text-slate-500">View and manage your medical visits.</p>
          </div>
          <Link to="/patient/book">
            <Button className="bg-primary hover:bg-blue-800 text-white font-medium">
              <CalendarPlus className="w-4 h-4 mr-2" /> Book Another
            </Button>
          </Link>
        </div>

        {loading ? (
          <PageLoader />
        ) : error ? (
          <ErrorMessage error={error} onRetry={fetchAppointments} />
        ) : (
          <Tabs defaultValue="upcoming" className="w-full">
            <TabsList className="grid w-full grid-cols-3 max-w-md mb-8 p-1 bg-slate-100 rounded-lg">
              <TabsTrigger value="upcoming" className="data-[selected]:bg-primary data-[selected]:text-white data-[selected]:shadow-md rounded-md py-2 font-semibold transition-all text-slate-500 hover:text-slate-700">Upcoming ({upcoming.length})</TabsTrigger>
              <TabsTrigger value="past" className="data-[selected]:bg-primary data-[selected]:text-white data-[selected]:shadow-md rounded-md py-2 font-semibold transition-all text-slate-500 hover:text-slate-700">Past ({past.length})</TabsTrigger>
              <TabsTrigger value="cancelled" className="data-[selected]:bg-primary data-[selected]:text-white data-[selected]:shadow-md rounded-md py-2 font-semibold transition-all text-slate-500 hover:text-slate-700">Cancelled ({cancelled.length})</TabsTrigger>
            </TabsList>

            <TabsContent value="upcoming" className="space-y-4">
              {upcoming.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-2xl border border-slate-200 shadow-sm">
                  <CalendarDays className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <h3 className="font-semibold text-slate-700">No upcoming appointments</h3>
                </div>
              ) : (
                upcoming.map(app => <AppointmentCard key={app.id} app={app} isUpcoming={true} />)
              )}
            </TabsContent>

            <TabsContent value="past" className="space-y-4">
              {past.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-2xl border border-slate-200 shadow-sm">
                  <FileText className="w-12 h-12 text-slate-300 mx-auto mb-3" />
                  <h3 className="font-semibold text-slate-700">No past visits yet</h3>
                </div>
              ) : (
                past.map(app => <AppointmentCard key={app.id} app={app} isUpcoming={false} />)
              )}
            </TabsContent>

            <TabsContent value="cancelled" className="space-y-4">
              {cancelled.length === 0 ? (
                <div className="text-center py-12 bg-white rounded-2xl border border-slate-200 shadow-sm">
                  <h3 className="font-semibold text-slate-700">No cancelled appointments</h3>
                </div>
              ) : (
                cancelled.map(app => <AppointmentCard key={app.id} app={app} isUpcoming={false} />)
              )}
            </TabsContent>
          </Tabs>
        )}
      </div>
    </SidebarLayout>
  );
}
