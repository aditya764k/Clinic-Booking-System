import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SidebarLayout } from '@/components/SidebarLayout';
import { receptionistApi, billingApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import {
  LayoutDashboard, UserPlus, CheckCircle2, User, Calendar, CreditCard, Banknote
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
import { format } from 'date-fns';

declare global {
  interface Window {
    Razorpay: any;
  }
}

const navLinks = [
  { label: 'Dashboard', href: '/receptionist/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Walk-In', href: '/receptionist/walk-in', icon: <UserPlus className="w-5 h-5" /> },
];

export default function WalkIn() {
  const [loading, setLoading] = useState(false);
  const [doctors, setDoctors] = useState<any[]>([]);
  const [slots, setSlots] = useState<any[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [successData, setSuccessData] = useState<any>(null);
  
  // Payment Modal State
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<'razorpay' | 'cash' | null>(null);
  const [cashAmount, setCashAmount] = useState('');
  const [processingPayment, setProcessingPayment] = useState(false);

  const [formData, setFormData] = useState({
    first_name: '',
    last_name: '',
    phone: '',
    date_of_birth: '',
    email: '',
    doctor_id: '',
    slot_id: ''
  });

  const navigate = useNavigate();

  useEffect(() => {
    const fetchDoctors = async () => {
      try {
        const data = await receptionistApi.getDoctors();
        setDoctors(data);
      } catch (err: any) {
        toast.error(err.message || 'Failed to load doctors');
      }
    };
    fetchDoctors();
  }, []);

  useEffect(() => {
    if (formData.doctor_id) {
      const fetchSlots = async () => {
        try {
          setSlotsLoading(true);
          const today = format(new Date(), 'yyyy-MM-dd');
          const data = await receptionistApi.getDoctorSlots(Number(formData.doctor_id), today);
          setSlots(data);
          setFormData(prev => ({ ...prev, slot_id: '' }));
        } catch (err: any) {
          toast.error(err.message || 'Failed to load slots');
          setSlots([]);
        } finally {
          setSlotsLoading(false);
        }
      };
      fetchSlots();
    }
  }, [formData.doctor_id]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.first_name || !formData.phone || !formData.doctor_id || !formData.slot_id) {
      toast.error('Please fill in all required fields.');
      return;
    }

    setLoading(true);
    try {
      // Backend WalkInRegistrationRequest expects first_name + last_name separately
      const payload: any = {
        first_name: formData.first_name.trim(),
        last_name: formData.last_name.trim() || '-',
        phone: formData.phone,
        email: formData.email || null,
        doctor_id: Number(formData.doctor_id),
        slot_id: Number(formData.slot_id)
      };

      const response = await receptionistApi.walkIn(payload);

      const doc = doctors.find(d => d.id === Number(formData.doctor_id));
      const slot = slots.find(s => s.id === Number(formData.slot_id));

      setSuccessData({
        patient_name: `${formData.first_name} ${formData.last_name}`.trim(),
        doctor_name: doc?.full_name,
        time: slot?.slot_start ? format(new Date(slot.slot_start), 'HH:mm') : '',
        invoice_id: response.invoice_id,
        amount: response.amount,
        currency: response.currency
      });
      setCashAmount(response.amount ? response.amount.toString() : '');

    } catch (err: any) {
      if (err.response?.status === 409) {
        toast.error('This slot was just taken. Please select another.');
        const today = format(new Date(), 'yyyy-MM-dd');
        receptionistApi.getDoctorSlots(Number(formData.doctor_id), today).then(setSlots);
        setFormData(prev => ({ ...prev, slot_id: '' }));
      } else {
        toast.error(err.message || 'Registration failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRazorpayPayment = async () => {
    if (!successData?.invoice_id) return;
    if (typeof window.Razorpay === 'undefined') {
      toast.error('Payment gateway not loaded. Please refresh the page.');
      return;
    }
    
    setProcessingPayment(true);
    try {
      const order = await billingApi.createRazorpayOrder(successData.invoice_id);
      
      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID,
        amount: order.amount,
        currency: order.currency,
        name: "Trimurti Clinic",
        description: "Booking Fee Payment",
        order_id: order.order_id,
        handler: async function(response: any) {
          try {
            await billingApi.verifyRazorpayPayment(successData.invoice_id, {
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_order_id: response.razorpay_order_id || order.order_id,
              razorpay_signature: response.razorpay_signature,
              razorpay_invoice_id: response.razorpay_invoice_id || "",
              razorpay_invoice_receipt: response.razorpay_invoice_receipt || ""
            });
            toast.success("Payment verified! Appointment updated.");
            setPaymentModalOpen(false);
            navigate('/receptionist/dashboard');
          } catch (verifyErr: any) {
            toast.error(verifyErr.message || "Payment verification failed.");
          }
        },
        prefill: {
          name: successData.patient_name,
        },
        theme: { color: "#0EA5E9" },
        modal: {
          ondismiss: function() {
            toast.info("Payment was cancelled. You can retry from the dashboard.");
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
    if (!successData?.invoice_id || !cashAmount) return;
    setProcessingPayment(true);
    try {
      await billingApi.payCash(successData.invoice_id, Number(cashAmount));
      toast.success("Cash payment recorded! Appointment updated.");
      setPaymentModalOpen(false);
      navigate('/receptionist/dashboard');
    } catch (err: any) {
      toast.error(err.message || 'Failed to process cash payment');
    } finally {
      setProcessingPayment(false);
    }
  };

  const handleReset = () => {
    setFormData({
      first_name: '',
      last_name: '',
      phone: '',
      date_of_birth: '',
      email: '',
      doctor_id: '',
      slot_id: ''
    });
    setSuccessData(null);
  };

  if (successData) {
    return (
      <SidebarLayout role="receptionist" links={navLinks}>
        <div className="max-w-2xl mx-auto mt-12 text-center p-12 bg-white rounded-3xl shadow-level-3 border border-slate-200">
          <div className="w-20 h-20 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-10 h-10" />
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-2">Patient Registered!</h2>
          <p className="text-slate-600 mb-8 leading-relaxed">
            <span className="font-semibold text-slate-900">{successData.patient_name}</span> has been registered and checked in for their{' '}
            <span className="font-semibold">{successData.time}</span> appointment with{' '}
            <span className="font-semibold">Dr. {successData.doctor_name}</span>.
            They are now in the waiting queue.
          </p>
          <div className="flex flex-col sm:flex-row justify-center gap-4">
            <Button onClick={() => setPaymentModalOpen(true)} size="lg" className="bg-sky-600 hover:bg-sky-700 text-white shadow-sm font-semibold">
              <CreditCard className="w-5 h-5 mr-2" />
              Collect Booking Fee (₹{successData.amount || '---'})
            </Button>
            <Button onClick={() => navigate('/receptionist/dashboard')} size="lg" variant="outline" className="border-slate-300 text-slate-700">
              Skip for Now
            </Button>
            <Button onClick={handleReset} size="lg" variant="ghost">
              Register Another
            </Button>
          </div>
        </div>

      {/* Payment Modal */}
      <Dialog open={paymentModalOpen} onOpenChange={(open) => !open && setPaymentModalOpen(false)}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Process Payment</DialogTitle>
            <DialogDescription>
              Complete the billing for {successData.patient_name}
            </DialogDescription>
          </DialogHeader>

          {!paymentMethod ? (
            <div className="py-6 space-y-4">
              <div className="bg-slate-50 p-4 rounded-lg border border-slate-200 mb-6 flex justify-between items-center">
                <div>
                  <p className="text-sm text-slate-500 mb-1">Invoice ID: #{successData.invoice_id}</p>
                  <p className="text-2xl font-bold text-slate-900">₹{successData.amount || '---'}</p>
                </div>
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

  return (
    <SidebarLayout role="receptionist" links={navLinks}>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Walk-In Registration</h1>
          <p className="text-slate-500">Register a new patient and add them directly to the queue.</p>
        </div>

        <div className="bg-white rounded-2xl shadow-level-1 border border-slate-200 overflow-hidden">
          <form onSubmit={handleSubmit} className="flex flex-col md:flex-row">

            <div className="flex-1 p-6 md:p-8 md:border-r border-slate-100 bg-slate-50/50">
              <div className="flex items-center gap-2 mb-6 text-slate-800">
                <User className="w-5 h-5 text-violet-600" />
                <h2 className="font-semibold">Patient Information</h2>
              </div>

              <div className="space-y-5">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="first_name">First Name <span className="text-red-500">*</span></Label>
                    <Input
                      id="first_name"
                      placeholder="e.g. Jane"
                      value={formData.first_name}
                      onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                      required
                      className="bg-white"
                    />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="last_name">Last Name</Label>
                    <Input
                      id="last_name"
                      placeholder="e.g. Doe"
                      value={formData.last_name}
                      onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                      className="bg-white"
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="phone">Phone Number <span className="text-red-500">*</span></Label>
                  <Input
                    id="phone"
                    placeholder="e.g. 9876543210"
                    value={formData.phone}
                    onChange={(e) => setFormData({...formData, phone: e.target.value})}
                    required
                    className="bg-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="date_of_birth">Date of Birth <span className="text-slate-400 font-normal">(Optional)</span></Label>
                  <Input
                    id="date_of_birth"
                    type="date"
                    value={formData.date_of_birth}
                    onChange={(e) => setFormData({...formData, date_of_birth: e.target.value})}
                    className="bg-white"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">Email</Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="name@example.com"
                    value={formData.email}
                    onChange={(e) => setFormData({...formData, email: e.target.value})}
                    className="bg-white"
                    required
                  />
                </div>
              </div>
            </div>

            <div className="flex-1 p-6 md:p-8">
              <div className="flex items-center gap-2 mb-6 text-slate-800">
                <Calendar className="w-5 h-5 text-violet-600" />
                <h2 className="font-semibold">Appointment Details</h2>
              </div>

              <div className="space-y-6">
                <div className="space-y-2">
                  <Label>Assign Doctor <span className="text-red-500">*</span></Label>
                  <select
                    required
                    className="w-full flex h-10 rounded-md border border-slate-200 bg-white px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-600 focus-visible:ring-offset-2"
                    value={formData.doctor_id}
                    onChange={(e) => setFormData({...formData, doctor_id: e.target.value})}
                  >
                    <option value="" disabled>Select a doctor...</option>
                    {doctors.map(doc => (
                      <option key={doc.id} value={doc.id}>Dr. {doc.full_name} — {doc.specialization || 'General'}</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-2">
                  <Label>Date</Label>
                  <div className="h-10 rounded-md border border-slate-200 bg-slate-100 px-3 py-2 text-sm text-slate-500 flex items-center">
                    {format(new Date(), 'EEEE, MMMM dd, yyyy')} (Today)
                  </div>
                </div>

                <div className="space-y-2">
                  <Label>Select Time Slot <span className="text-red-500">*</span></Label>
                  {!formData.doctor_id ? (
                    <div className="text-sm text-slate-500 p-4 bg-slate-50 rounded-lg border border-slate-200 text-center border-dashed">
                      Select a doctor first to view available slots.
                    </div>
                  ) : slotsLoading ? (
                    <div className="text-sm text-slate-500 p-4 text-center">Loading slots...</div>
                  ) : slots.length === 0 ? (
                    <div className="text-sm p-4 bg-orange-50 text-orange-700 rounded-lg border border-orange-200 text-center">
                      No open slots for this doctor today.
                    </div>
                  ) : (
                    <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                      {slots.map(slot => (
                        <button
                          key={slot.id}
                          type="button"
                          onClick={() => setFormData({...formData, slot_id: slot.id.toString()})}
                          className={`py-2 px-1 text-xs sm:text-sm font-medium rounded-lg border transition-colors ${
                            formData.slot_id === slot.id.toString()
                              ? 'bg-violet-600 border-violet-600 text-white shadow-md'
                              : 'bg-white border-slate-200 text-slate-700 hover:border-violet-500 hover:text-violet-600'
                          }`}
                        >
                          {slot.slot_start ? format(new Date(slot.slot_start), 'HH:mm') : slot.id}
                        </button>
                      ))}
                    </div>
                  )}
                </div>

                <div className="pt-6">
                  <Button
                    type="submit"
                    disabled={loading || !formData.doctor_id || (!formData.slot_id && slots.length > 0)}
                    className="w-full bg-violet-600 hover:bg-violet-700 text-white text-base py-6"
                  >
                    {loading ? 'Processing...' : 'Register & Check In'}
                  </Button>
                </div>
              </div>
            </div>

          </form>
        </div>
      </div>
    </SidebarLayout>
  );
}
