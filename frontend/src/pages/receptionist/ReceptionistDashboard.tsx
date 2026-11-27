import { useState, useEffect } from 'react';
import { SidebarLayout } from '@/components/SidebarLayout';
import { receptionistApi, appointmentApi, billingApi, clinicalNoteApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { PageLoader } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { 
  LayoutDashboard, UserPlus, RefreshCw,
  CreditCard, Banknote, UserCheck, Stethoscope, FileText, Ban
} from 'lucide-react';
import { format } from 'date-fns';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

declare global {
  interface Window {
    Razorpay: any;
  }
}

const navLinks = [
  { label: 'Dashboard', href: '/receptionist/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Walk-In', href: '/receptionist/walk-in', icon: <UserPlus className="w-5 h-5" /> },
];

export default function ReceptionistDashboard() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [analytics, setAnalytics] = useState<any>(null);
  const [queue, setQueue] = useState<any[]>([]);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  // Payment Modal State
  const [paymentAppt, setPaymentAppt] = useState<any>(null);
  const [invoiceId, setInvoiceId] = useState<number | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<'razorpay' | 'cash' | null>(null);
  const [cashAmount, setCashAmount] = useState('');
  const [processingPayment, setProcessingPayment] = useState(false);

  const fetchDashboardData = async (silent = false) => {
    try {
      if (!silent) setLoading(true);
      setError(null);
      const todayDateStr = format(new Date(), 'yyyy-MM-dd');
      
      const [queueData, analyticsData] = await Promise.all([
        appointmentApi.getTodayQueue(todayDateStr),
        receptionistApi.getAnalytics()
      ]);
      setAnalytics(analyticsData);
      setQueue(queueData);
      setLastRefresh(new Date());
    } catch (err: any) {
      if (!silent) setError(err.message || 'Failed to load dashboard data');
    } finally {
      if (!silent) setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
    const interval = setInterval(() => {
      fetchDashboardData(true);
    }, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleCheckIn = async (id: number) => {
    try {
      await appointmentApi.checkIn(id);
      toast.success('Patient checked in successfully');
      fetchDashboardData(true);
    } catch (err: any) {
      toast.error(err.message || 'Failed to check in patient');
    }
  };

  const handleCancel = async (id: number) => {
    if (!window.confirm("Are you sure you want to cancel this appointment?")) return;
    try {
      await appointmentApi.cancel(id);
      toast.success('Appointment cancelled');
      fetchDashboardData(true);
    } catch (err: any) {
      toast.error(err.message || 'Failed to cancel appointment');
    }
  };

  // Billing Flow
  const openPaymentModal = async (appt: any) => {
    setPaymentAppt(appt);
    setPaymentMethod(null);
    setInvoiceId(null);
    setCashAmount('');
    
    if (appt.invoice) {
      setInvoiceId(appt.invoice.id);
      if (appt.invoice.amount) setCashAmount(appt.invoice.amount.toString());
    } else {
      toast.error('No pending invoice found for this appointment.');
      setPaymentAppt(null);
    }
  };

  const handleRazorpayPayment = async () => {
    if (!invoiceId || !paymentAppt) return;
    if (typeof window.Razorpay === 'undefined') {
      toast.error('Payment gateway not loaded. Please refresh the page.');
      return;
    }
    
    setProcessingPayment(true);
    try {
      const order = await billingApi.createRazorpayOrder(invoiceId);
      
      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID,
        amount: order.amount,
        currency: order.currency,
        name: "Trimurti Clinic",
        description: "Consultation Payment",
        order_id: order.order_id,
        handler: async function(response: any) {
          try {
            await billingApi.verifyRazorpayPayment(invoiceId, {
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_order_id: response.razorpay_order_id || order.order_id,
              razorpay_signature: response.razorpay_signature,
              razorpay_invoice_id: response.razorpay_invoice_id || "",
              razorpay_invoice_receipt: response.razorpay_invoice_receipt || ""
            });
            toast.success("Payment verified! Appointment updated.");
            setPaymentAppt(null);
            fetchDashboardData(true);
          } catch (verifyErr: any) {
            toast.error(verifyErr.message || "Payment verification failed.");
          }
        },
        prefill: {
          name: paymentAppt.patient_name,
        },
        theme: { color: "#0EA5E9" },
        modal: {
          ondismiss: function() {
            toast.info("Payment was cancelled. You can retry when ready.");
          }
        }
      };
      const rzp = new window.Razorpay(options);
      rzp.open();
    } catch (err: any) {
      toast.error(err.message || 'Failed to initiate Razorpay order');
    } finally {
      setProcessingPayment(false);
    }
  };

  const handleCashPayment = async () => {
    if (!invoiceId || !cashAmount) return;
    setProcessingPayment(true);
    try {
      await billingApi.payCash(invoiceId, Number(cashAmount));
      toast.success("Cash payment recorded! Appointment updated.");
      setPaymentAppt(null);
      fetchDashboardData(true);
    } catch (err: any) {
      toast.error(err.message || 'Failed to record cash payment');
    } finally {
      setProcessingPayment(false);
    }
  };

  // Group Queue
  const groups = {
    waiting: queue.filter(a => a.status === 'checked_in'),
    booked: queue.filter(a => a.status === 'booked' || a.status === 'payment_pending'),
    in_consultation: queue.filter(a => a.status === 'in_consultation'),
    completed: queue.filter(a => a.status === 'completed' || a.status === 'billing_pending'),
    paid: queue.filter(a => a.status === 'paid'),
    cancelled: queue.filter(a => ['cancelled', 'no_show'].includes(a.status))
  };


  return (
    <SidebarLayout role="receptionist" links={navLinks}>
      <div className="max-w-6xl mx-auto">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-8">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
            <p className="text-slate-500">
              Today: {format(new Date(), 'EEEE, dd MMM yyyy')}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs text-slate-400">Last updated: {format(lastRefresh, 'HH:mm:ss')}</span>
            <Button variant="outline" size="sm" onClick={() => fetchDashboardData(true)} className="bg-white">
              <RefreshCw className="w-4 h-4 mr-2" /> Refresh
            </Button>
          </div>
        </div>

        {loading ? (
          <PageLoader />
        ) : error ? (
          <ErrorMessage error={error} onRetry={() => fetchDashboardData()} />
        ) : (
          <>
            {/* Analytics Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <div className="bg-white p-5 rounded-2xl shadow-level-2 border-y border-r border-slate-200 border-l-[4px] border-l-amber-500 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-amber-50 flex items-center justify-center text-amber-600">
                  <UserCheck className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase font-semibold">Total Checked In</p>
                  <p className="text-2xl font-bold text-slate-900">{analytics?.checked_in_count ?? 0}</p>
                </div>
              </div>
              
              <div className="bg-white p-5 rounded-2xl shadow-level-2 border-y border-r border-slate-200 border-l-[4px] border-l-emerald-600 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-emerald-50 flex items-center justify-center text-emerald-600">
                  <Stethoscope className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase font-semibold">Consultations Completed</p>
                  <p className="text-2xl font-bold text-slate-900">{analytics?.completed_count ?? 0}</p>
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl shadow-level-2 border-y border-r border-slate-200 border-l-[4px] border-l-sky-500 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-sky-50 flex items-center justify-center text-sky-600">
                  <CreditCard className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase font-semibold">Revenue (Razorpay)</p>
                  <p className="text-2xl font-bold text-slate-900">₹{analytics?.revenue_razorpay || 0}</p>
                </div>
              </div>

              <div className="bg-white p-5 rounded-2xl shadow-level-2 border-y border-r border-slate-200 border-l-[4px] border-l-green-600 flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center text-green-600">
                  <Banknote className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-xs text-slate-500 uppercase font-semibold">Revenue (Cash)</p>
                  <p className="text-2xl font-bold text-slate-900">₹{analytics?.revenue_cash || 0}</p>
                </div>
              </div>
            </div>

            {/* Tabs & Data Table */}
            <div className="bg-white rounded-2xl shadow-level-1 border border-slate-200 overflow-hidden">
              <Tabs defaultValue="all" className="w-full">
                <div className="border-b border-slate-200 px-6 py-3 overflow-x-auto hide-scrollbar">
                  <TabsList className="bg-transparent space-x-2 h-auto p-0">
                    <TabsTrigger value="all" className="data-[state=active]:bg-slate-100 data-[state=active]:shadow-none rounded-lg px-4 py-2">
                      All <span className="ml-2 bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full text-xs">{queue.length}</span>
                    </TabsTrigger>
                    <TabsTrigger value="booked" className="data-[state=active]:bg-sky-50 data-[state=active]:text-sky-700 data-[state=active]:shadow-none rounded-lg px-4 py-2">
                      Booked <span className="ml-2 bg-sky-100 text-sky-700 px-2 py-0.5 rounded-full text-xs">{groups.booked.length}</span>
                    </TabsTrigger>
                    <TabsTrigger value="waiting" className="data-[state=active]:bg-amber-50 data-[state=active]:text-amber-700 data-[state=active]:shadow-none rounded-lg px-4 py-2">
                      Waiting <span className="ml-2 bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full text-xs">{groups.waiting.length}</span>
                    </TabsTrigger>
                    <TabsTrigger value="in_consultation" className="data-[state=active]:bg-indigo-50 data-[state=active]:text-indigo-700 data-[state=active]:shadow-none rounded-lg px-4 py-2">
                      Consulting <span className="ml-2 bg-indigo-100 text-indigo-700 px-2 py-0.5 rounded-full text-xs">{groups.in_consultation.length}</span>
                    </TabsTrigger>
                    <TabsTrigger value="completed" className="data-[state=active]:bg-orange-50 data-[state=active]:text-orange-700 data-[state=active]:shadow-none rounded-lg px-4 py-2">
                      Billing <span className="ml-2 bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full text-xs">{groups.completed.length}</span>
                    </TabsTrigger>
                    <TabsTrigger value="history" className="data-[state=active]:bg-slate-100 data-[state=active]:shadow-none rounded-lg px-4 py-2">
                      History <span className="ml-2 bg-slate-200 text-slate-600 px-2 py-0.5 rounded-full text-xs">{groups.paid.length + groups.cancelled.length}</span>
                    </TabsTrigger>
                  </TabsList>
                </div>

                {['all', 'booked', 'waiting', 'in_consultation', 'completed', 'history'].map((tabVal) => {
                  const items = tabVal === 'all' ? queue 
                    : tabVal === 'history' ? [...groups.paid, ...groups.cancelled]
                    : groups[tabVal as keyof typeof groups];

                  return (
                    <TabsContent key={tabVal} value={tabVal} className="m-0 p-0 outline-none">
                      <div className="overflow-x-auto">
                        <table className="w-full text-left border-collapse min-w-[800px]">
                          <thead>
                            <tr className="border-b border-slate-200 bg-slate-50/50 text-sm text-slate-500 uppercase tracking-wider">
                              <th className="py-4 px-6 font-semibold w-24">Time</th>
                              <th className="py-4 px-6 font-semibold">Patient</th>
                              <th className="py-4 px-6 font-semibold">Doctor</th>
                              <th className="py-4 px-6 font-semibold w-40">Status</th>
                              <th className="py-4 px-6 font-semibold text-right w-64">Actions</th>
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-100">
                            {items.length === 0 ? (
                              <tr>
                                <td colSpan={5} className="py-12 text-center text-slate-400">
                                  No patients found in this category.
                                </td>
                              </tr>
                            ) : (
                              items.map((app) => (
                                <tr key={app.id} className="hover:bg-slate-50 transition-colors group">
                                  <td className="py-4 px-6 font-medium text-slate-700">
                                    {app.slot_start ? new Date(app.slot_start).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false }) : '--:--'}
                                  </td>
                                  <td className="py-4 px-6">
                                    <span className="font-bold text-slate-900">{app.patient_name}</span>
                                  </td>
                                  <td className="py-4 px-6 text-slate-600">
                                    Dr. {app.doctor_name}
                                  </td>
                                  <td className="py-4 px-6">
                                    {app.status === 'payment_pending' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-red-50 text-red-700 border border-red-100"><CreditCard className="w-3.5 h-3.5" /> Unpaid</span>}
                                    {app.status === 'booked' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-sky-50 text-sky-700 border border-sky-100"><CalendarIcon className="w-3.5 h-3.5" /> Booked</span>}
                                    {app.status === 'checked_in' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-amber-50 text-amber-700 border border-amber-100"><UserCheck className="w-3.5 h-3.5" /> Waiting</span>}
                                    {app.status === 'in_consultation' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 border border-indigo-100"><Stethoscope className="w-3.5 h-3.5" /> Consulting</span>}
                                    {(app.status === 'completed' || app.status === 'billing_pending') && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-orange-50 text-orange-700 border border-orange-100"><FileText className="w-3.5 h-3.5" /> Billing</span>}
                                    {app.status === 'paid' && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 text-emerald-700 border border-emerald-100"><CreditCard className="w-3.5 h-3.5" /> Paid</span>}
                                    {(app.status === 'cancelled' || app.status === 'no_show') && <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200"><Ban className="w-3.5 h-3.5" /> Cancelled</span>}
                                  </td>
                                  <td className="py-4 px-6 text-right">
                                    <div className="flex items-center justify-end gap-2 opacity-100 md:opacity-0 group-hover:opacity-100 transition-opacity">
                                      {app.status === 'booked' && (
                                        <>
                                          <Button size="sm" onClick={() => handleCheckIn(app.id)} className="bg-sky-600 hover:bg-sky-700 text-white shadow-sm h-8 px-4 text-xs">Check In</Button>
                                          <Button variant="ghost" size="sm" onClick={() => handleCancel(app.id)} className="text-red-500 hover:text-red-600 hover:bg-red-50 h-8 px-3 text-xs">Cancel</Button>
                                        </>
                                      )}
                                      {app.status === 'checked_in' && (
                                        <>
                                          <span className="text-[11px] text-amber-600 font-medium px-2 mr-2">Ready for Doctor</span>
                                          <Button variant="ghost" size="sm" onClick={() => handleCancel(app.id)} className="text-red-500 hover:text-red-600 hover:bg-red-50 h-8 px-3 text-xs">Cancel</Button>
                                        </>
                                      )}
                                      {app.status === 'in_consultation' && (
                                        <span className="flex items-center gap-2 text-indigo-600 text-[11px] font-semibold pr-2">
                                          <span className="relative flex h-2 w-2">
                                            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
                                            <span className="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
                                          </span>
                                          IN PROGRESS
                                        </span>
                                      )}
                                      {(app.status === 'completed' || app.status === 'billing_pending' || app.status === 'paid') && (
                                        <Button 
                                          variant="ghost" 
                                          size="sm" 
                                          onClick={async () => {
                                            try {
                                              const res = await clinicalNoteApi.downloadPrescription(app.id);
                                              window.open(res.url, '_blank');
                                            } catch (err: any) {
                                              toast.error('Prescription not available yet');
                                            }
                                          }}
                                          className="text-indigo-600 hover:bg-indigo-50 h-8 px-2 text-xs"
                                        >
                                          <FileText className="w-3.5 h-3.5 mr-1" /> Print Rx
                                        </Button>
                                      )}
                                      {(app.status === 'completed' || app.status === 'billing_pending' || app.status === 'payment_pending') && (
                                        <Button size="sm" onClick={() => openPaymentModal(app)} className="bg-orange-600 hover:bg-orange-700 text-white shadow-sm h-8 px-4 text-xs">
                                          {app.status === 'payment_pending' ? 'Collect Booking Fee' : 'Bill This Visit'}
                                        </Button>
                                      )}
                                      {app.status === 'paid' && (
                                        <div className="flex items-center justify-end gap-2 pr-2">
                                          <span className="text-[11px] font-bold text-slate-500">
                                            {app.invoice?.receipt_number || 'Receipt Generated'}
                                          </span>
                                          <Button 
                                            variant="ghost" 
                                            size="sm" 
                                            onClick={async () => {
                                              try {
                                                const res = await appointmentApi.downloadInvoice(app.invoice!.id);
                                                window.open(res.url, '_blank');
                                              } catch (err: any) {
                                                toast.error(err.message || 'Failed to download invoice');
                                              }
                                            }}
                                            className="text-primary hover:bg-blue-50 h-8 px-2 text-xs"
                                          >
                                            <FileText className="w-3.5 h-3.5 mr-1" /> PDF Invoice
                                          </Button>
                                        </div>
                                      )}
                                      {(app.status === 'cancelled' || app.status === 'no_show') && (
                                        <span className="text-[11px] font-medium text-slate-400 pr-2 uppercase">
                                          {app.status.replace('_', ' ')}
                                        </span>
                                      )}
                                    </div>
                                  </td>
                                </tr>
                              ))
                            )}
                          </tbody>
                        </table>
                      </div>
                    </TabsContent>
                  );
                })}
              </Tabs>
            </div>
          </>
        )}
      </div>

      {/* Payment Modal */}
      <Dialog open={!!paymentAppt} onOpenChange={(open) => !open && setPaymentAppt(null)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Process Payment</DialogTitle>
            <DialogDescription>
              Complete the billing for {paymentAppt?.patient_name}
            </DialogDescription>
          </DialogHeader>

          {!invoiceId ? (
            <div className="py-12 flex justify-center"><PageLoader /></div>
          ) : !paymentMethod ? (
            <div className="py-6 space-y-4">
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6">
                <p className="text-sm text-slate-500 mb-1">Invoice ID: #{invoiceId}</p>
                <p className="text-2xl font-bold text-slate-900">₹{cashAmount || '---'}</p>
              </div>
              <h4 className="text-sm font-medium text-slate-700 mb-2">Select Payment Method</h4>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setPaymentMethod('razorpay')}
                  className="flex flex-col items-center justify-center p-6 border border-slate-200 rounded-xl hover:border-sky-500 hover:bg-sky-50 transition-colors"
                >
                  <CreditCard className="w-8 h-8 text-sky-600 mb-2" />
                  <span className="font-semibold text-slate-900">Razorpay</span>
                </button>
                <button
                  onClick={() => setPaymentMethod('cash')}
                  className="flex flex-col items-center justify-center p-6 border border-slate-200 rounded-xl hover:border-emerald-500 hover:bg-emerald-50 transition-colors"
                >
                  <Banknote className="w-8 h-8 text-emerald-600 mb-2" />
                  <span className="font-semibold text-slate-900">Cash</span>
                </button>
              </div>
            </div>
          ) : paymentMethod === 'razorpay' ? (
            <div className="py-6 space-y-6 text-center">
              <CreditCard className="w-12 h-12 text-sky-600 mx-auto" />
              <div>
                <p className="text-lg font-bold text-slate-900 mb-2">Pay via Razorpay</p>
                <p className="text-sm text-slate-500">The Razorpay checkout widget will open.</p>
              </div>
              <Button 
                onClick={handleRazorpayPayment} 
                disabled={processingPayment}
                className="w-full bg-sky-600 hover:bg-sky-700 text-white"
              >
                {processingPayment ? 'Opening Checkout...' : 'Open Checkout Widget'}
              </Button>
              <Button variant="ghost" onClick={() => setPaymentMethod(null)} disabled={processingPayment}>
                Back to Methods
              </Button>
            </div>
          ) : (
            <div className="py-6 space-y-6">
              <div className="text-center mb-6">
                <Banknote className="w-12 h-12 text-emerald-600 mx-auto mb-2" />
                <p className="text-lg font-bold text-slate-900">Cash Payment</p>
              </div>
              <div className="space-y-2">
                <Label>Amount Received (₹)</Label>
                <Input 
                  type="number" 
                  value={cashAmount} 
                  onChange={(e) => setCashAmount(e.target.value)} 
                  className="text-lg font-semibold"
                />
              </div>
              <div className="flex flex-col gap-2 pt-2">
                <Button 
                  onClick={handleCashPayment} 
                  disabled={processingPayment || !cashAmount}
                  className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  {processingPayment ? 'Processing...' : 'Confirm Cash Received'}
                </Button>
                <Button variant="ghost" onClick={() => setPaymentMethod(null)} disabled={processingPayment}>
                  Back to Methods
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </SidebarLayout>
  );
}

function CalendarIcon(props: any) {
  return (
    <svg {...props} xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/></svg>
  );
}
