import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SidebarLayout } from '@/components/SidebarLayout';
import { appointmentApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { PageLoader } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { 
  LayoutDashboard, Settings, Calendar as CalendarIcon, Clock, User, UserPlus
} from 'lucide-react';
import { format } from 'date-fns';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { Calendar } from '@/components/ui/calendar';

const navLinks = [
  { label: 'Dashboard', href: '/doctor/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Add Colleague', href: '/doctor/add-colleague', icon: <UserPlus className="w-5 h-5" /> },
  { label: 'Settings', href: '/doctor/settings', icon: <Settings className="w-5 h-5" /> },
  { label: 'Profile', href: '/doctor/profile', icon: <User className="w-5 h-5" /> },
];

export default function DoctorDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [queue, setQueue] = useState<any[]>([]);
  const [date, setDate] = useState<Date>(new Date());
  
  const navigate = useNavigate();

  const fetchQueue = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      setError(null);
      const dateStr = format(date, 'yyyy-MM-dd');
      const data = await appointmentApi.getMyQueue(dateStr);
      setQueue(data);
    } catch (err: any) {
      if (!silent) setError(err.message || 'Failed to load queue');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchQueue();
    // Auto-poll every 30 seconds
    const interval = setInterval(() => {
      fetchQueue(true);
    }, 30000);
    return () => clearInterval(interval);
  }, [date]);

  const handleStartConsultation = async (id: number) => {
    try {
      await appointmentApi.startConsultation(id);
      navigate(`/doctor/consultation/${id}`);
    } catch (err: any) {
      toast.error(err.message || 'Cannot start consultation');
    }
  };

  // Swimlanes
  const waiting = queue.filter(a => a.status === 'checked_in');
  const inConsultation = queue.filter(a => a.status === 'in_consultation');
  const completed = queue.filter(a => a.status === 'completed');
  const done = queue.filter(a => ['paid', 'billing_pending'].includes(a.status));

  const QueueCard = ({ app, type }: { app: any, type: 'waiting' | 'in_consultation' | 'completed' | 'done' }) => (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200 mb-3 hover:shadow-md transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <div>
          <h4 className="font-bold text-slate-900 leading-tight">{app.patient_name}</h4>
          <div className="flex items-center gap-1 text-xs text-slate-500 mt-1">
            <Clock className="w-3 h-3" /> {format(new Date(app.slot_start), 'HH:mm')}
          </div>
        </div>
        {type === 'in_consultation' && (
          <span className="flex h-2 w-2 relative mt-1">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
          </span>
        )}
      </div>
      
      {type === 'waiting' && (
        <Button 
          className="w-full bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm"
          onClick={() => handleStartConsultation(app.id)}
        >
          Start Consultation
        </Button>
      )}
      {type === 'in_consultation' && (
        <Button 
          className="w-full bg-indigo-600 hover:bg-indigo-700 text-white shadow-sm"
          onClick={() => navigate(`/doctor/consultation/${app.id}`)}
        >
          Continue
        </Button>
      )}
      {(type === 'completed' || type === 'done') && (
        <div className="bg-slate-50 border border-slate-100 rounded-lg p-2 text-center text-xs font-medium text-slate-500">
          Completed
        </div>
      )}
    </div>
  );

  return (
    <SidebarLayout role="doctor" links={navLinks}>
      <div className="h-full flex flex-col">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Queue Management</h1>
            <p className="text-slate-500">Manage your consultations for the day.</p>
          </div>
          
          <Popover>
            {/* @ts-ignore */}
            <PopoverTrigger asChild>
              <Button variant="outline" className="w-[240px] justify-start text-left font-medium bg-white">
                <CalendarIcon className="mr-2 h-4 w-4 text-emerald-600" />
                {format(date, 'EEEE, MMMM dd, yyyy')}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="end">
              <Calendar
                mode="single"
                selected={date}
                onSelect={(d) => d && setDate(d)}
                // @ts-ignore
                initialFocus
              />
            </PopoverContent>
          </Popover>
        </div>

        {loading ? (
          <PageLoader />
        ) : error ? (
          <ErrorMessage error={error} onRetry={() => fetchQueue()} />
        ) : queue.length === 0 ? (
          <div className="flex-1 flex flex-col items-center justify-center text-center p-12 bg-white rounded-2xl border border-slate-200 border-dashed">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <User className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="font-semibold text-slate-700 mb-1">No appointments for {format(date, 'MMM dd')}</h3>
            <p className="text-slate-500">Enjoy your day!</p>
          </div>
        ) : (
          <div className="flex-1 grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 items-start">
            
            {/* Column: Waiting */}
            <div className="flex flex-col bg-slate-50/50 rounded-2xl p-4 border border-slate-200/60 min-h-[500px]">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-700 uppercase text-xs tracking-wider">Waiting</h3>
                <span className="bg-amber-100 text-amber-700 text-xs font-bold px-2 py-0.5 rounded-full">{waiting.length}</span>
              </div>
              <div className="flex-1 overflow-y-auto pr-1">
                {waiting.map(app => <QueueCard key={app.id} app={app} type="waiting" />)}
              </div>
            </div>

            {/* Column: In Consultation */}
            <div className="flex flex-col bg-indigo-50/30 rounded-2xl p-4 border border-indigo-100 min-h-[500px]">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-indigo-700 uppercase text-xs tracking-wider">In Consultation</h3>
                <span className="bg-indigo-100 text-indigo-700 text-xs font-bold px-2 py-0.5 rounded-full">{inConsultation.length}</span>
              </div>
              <div className="flex-1 overflow-y-auto pr-1">
                {inConsultation.map(app => <QueueCard key={app.id} app={app} type="in_consultation" />)}
              </div>
            </div>

            {/* Column: Completed */}
            <div className="flex flex-col bg-slate-50/50 rounded-2xl p-4 border border-slate-200/60 min-h-[500px]">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-slate-700 uppercase text-xs tracking-wider">Completed</h3>
                <span className="bg-slate-200 text-slate-700 text-xs font-bold px-2 py-0.5 rounded-full">{completed.length}</span>
              </div>
              <div className="flex-1 overflow-y-auto pr-1">
                {completed.map(app => <QueueCard key={app.id} app={app} type="completed" />)}
              </div>
            </div>

            {/* Column: Done/Paid */}
            <div className="flex flex-col bg-emerald-50/30 rounded-2xl p-4 border border-emerald-100 min-h-[500px]">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-semibold text-emerald-700 uppercase text-xs tracking-wider">Done & Paid</h3>
                <span className="bg-emerald-100 text-emerald-700 text-xs font-bold px-2 py-0.5 rounded-full">{done.length}</span>
              </div>
              <div className="flex-1 overflow-y-auto pr-1">
                {done.map(app => <QueueCard key={app.id} app={app} type="done" />)}
              </div>
            </div>

          </div>
        )}
      </div>
    </SidebarLayout>
  );
}
