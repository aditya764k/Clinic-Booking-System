import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { SidebarLayout } from '@/components/SidebarLayout';
import { appointmentApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { PageLoader } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { 
  LayoutDashboard, CalendarPlus, CalendarDays, FileText, 
  Receipt, Download, CreditCard, Banknote, User
} from 'lucide-react';
import { format } from 'date-fns';

const navLinks = [
  { label: 'Dashboard', href: '/patient/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Book Appointment', href: '/patient/book', icon: <CalendarPlus className="w-5 h-5" /> },
  { label: 'My Appointments', href: '/patient/appointments', icon: <CalendarDays className="w-5 h-5" /> },
  { label: 'My Invoices', href: '/patient/invoices', icon: <FileText className="w-5 h-5" /> },
  { label: 'Profile', href: '/patient/profile', icon: <User className="w-5 h-5" /> },
];

export default function MyInvoices() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [invoices, setInvoices] = useState<any[]>([]);

  useEffect(() => {
    const fetchInvoices = async () => {
      try {
        setLoading(true);
        setError(null);
        // Backend doesn't have a direct invoices endpoint for patients, so we extract from appointments
        const data = await appointmentApi.getMyQueue();
        const paidVisits = data.filter((a: any) => a.status === 'paid' || a.status === 'completed');
        setInvoices(paidVisits);
      } catch (err: any) {
        setError(err.message || 'Failed to load invoices');
      } finally {
        setLoading(false);
      }
    };
    fetchInvoices();
  }, []);

  return (
    <SidebarLayout role="patient" links={navLinks}>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">My Invoices</h1>
          <p className="text-slate-500">View and download your billing history.</p>
        </div>

        {loading ? (
          <PageLoader />
        ) : error ? (
          <ErrorMessage error={error} onRetry={() => window.location.reload()} />
        ) : invoices.length === 0 ? (
          <div className="text-center py-16 bg-white rounded-2xl border border-slate-200 shadow-sm border-dashed">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Receipt className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="font-semibold text-slate-700 mb-2">No invoices yet</h3>
            <p className="text-slate-500 max-w-md mx-auto mb-6">
              Your invoices will appear here automatically after your visit is billed by the receptionist.
            </p>
            <Link to="/patient/book">
              <Button className="bg-primary hover:bg-blue-800 text-white font-medium">
                Book an Appointment
              </Button>
            </Link>
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="grid grid-cols-4 md:grid-cols-6 gap-4 p-4 bg-slate-50 border-b border-slate-200 font-semibold text-xs text-slate-500 uppercase tracking-wider">
              <div className="col-span-2 md:col-span-2">Visit</div>
              <div className="hidden md:block col-span-1">Date</div>
              <div className="col-span-1">Status</div>
              <div className="col-span-1 text-right md:text-left">Amount</div>
              <div className="hidden md:block col-span-1 text-right">Action</div>
            </div>
            <div className="divide-y divide-slate-100">
              {invoices.map(inv => (
                <div key={inv.id} className="grid grid-cols-4 md:grid-cols-6 gap-4 p-4 items-center hover:bg-slate-50 transition-colors">
                  <div className="col-span-2 md:col-span-2">
                    <p className="font-semibold text-slate-900">Dr. {inv.doctor_name}</p>
                    <p className="text-xs text-slate-500 md:hidden">{inv.slot_start ? format(new Date(inv.slot_start), 'MMM dd, yyyy') : ''}</p>
                  </div>
                  <div className="hidden md:block col-span-1 text-sm text-slate-600">
                    {inv.slot_start ? format(new Date(inv.slot_start), 'MMM dd, yyyy') : ''}
                  </div>
                  <div className="col-span-1">
                    {inv.status === 'paid' ? (
                      <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 border border-emerald-200 px-2 py-0.5 rounded text-xs font-medium">
                        <CheckCircle2 className="w-3 h-3" /> Paid
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 bg-orange-50 text-orange-700 border border-orange-200 px-2 py-0.5 rounded text-xs font-medium">
                        Pending
                      </span>
                    )}
                  </div>
                  <div className="col-span-1 text-right md:text-left">
                    <span className="font-semibold text-slate-900">₹{inv.invoice?.amount || '---'}</span>
                    {inv.invoice?.payment_method && (
                      <p className="text-[10px] text-slate-400 uppercase tracking-wider mt-0.5 flex justify-end md:justify-start items-center gap-1">
                        {inv.invoice.payment_method === 'cash' ? <Banknote className="w-3 h-3" /> : <CreditCard className="w-3 h-3" />}
                        {inv.invoice.payment_method}
                      </p>
                    )}
                  </div>
                  <div className="hidden md:flex col-span-1 justify-end">
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      className="text-primary hover:bg-blue-50" 
                      disabled={inv.status !== 'paid'}
                      onClick={async () => {
                        try {
                          const res = await appointmentApi.downloadInvoice(inv.invoice!.id);
                          window.open(res.url, '_blank');
                        } catch (err: any) {
                          alert(err.message || 'Failed to download invoice');
                        }
                      }}
                    >
                      <Download className="w-4 h-4 mr-2" /> PDF
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </SidebarLayout>
  );
}

function CheckCircle2(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/></svg>
  );
}
