import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SidebarLayout } from '@/components/SidebarLayout';
import { receptionistApi, schedulingApi, billingApi, appointmentApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { toast } from 'sonner';
import { PageLoader } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { 
  LayoutDashboard, CalendarPlus, CalendarDays, FileText, 
  ChevronRight, ArrowLeft, Stethoscope, Clock, CheckCircle2, User
} from 'lucide-react';
import { format } from 'date-fns';

declare global {
  interface Window {
    Razorpay: any;
  }
}

const navLinks = [
  { label: 'Dashboard', href: '/patient/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Book Appointment', href: '/patient/book', icon: <CalendarPlus className="w-5 h-5" /> },
  { label: 'My Appointments', href: '/patient/appointments', icon: <CalendarDays className="w-5 h-5" /> },
  { label: 'My Invoices', href: '/patient/invoices', icon: <FileText className="w-5 h-5" /> },
  { label: 'Profile', href: '/patient/profile', icon: <User className="w-5 h-5" /> },
];

export default function BookAppointment() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  const [doctors, setDoctors] = useState<any[]>([]);
  const [selectedDoctor, setSelectedDoctor] = useState<any>(null);
  
  const [date, setDate] = useState<Date | undefined>(undefined);
  const [slots, setSlots] = useState<any[]>([]);
  const [slotsLoading, setSlotsLoading] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState<any>(null);

  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingSuccess, setBookingSuccess] = useState(false);
  
  const navigate = useNavigate();

  useEffect(() => {
    const fetchDoctors = async () => {
      try {
        setLoading(true);
        const data = await receptionistApi.getDoctors();
        setDoctors(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load doctors');
      } finally {
        setLoading(false);
      }
    };
    fetchDoctors();
  }, []);

  useEffect(() => {
    if (selectedDoctor && date) {
      const fetchSlots = async () => {
        try {
          setSlotsLoading(true);
          setSelectedSlot(null);
          const dateStr = format(date, 'yyyy-MM-dd');
          const data = await schedulingApi.getOpenSlots(selectedDoctor.id, dateStr);
          setSlots(data);
        } catch (err: any) {
          toast.error(err.message || 'Failed to load slots');
          setSlots([]);
        } finally {
          setSlotsLoading(false);
        }
      };
      fetchSlots();
    }
  }, [selectedDoctor, date]);

  const handleBook = async () => {
    if (!selectedSlot || !selectedDoctor) return;
    
    try {
      setBookingLoading(true);
      const bookingData = await schedulingApi.bookAppointment(selectedSlot.id);
      
      // Trigger Razorpay for Booking Fee
      if (typeof window.Razorpay === 'undefined') {
        toast.error('Payment gateway not loaded. Please refresh the page.');
        setBookingLoading(false);
        return;
      }

      const options = {
        key: import.meta.env.VITE_RAZORPAY_KEY_ID,
        amount: bookingData.amount,
        currency: bookingData.currency,
        name: "Trimurti Clinic",
        description: `Booking Fee - Dr. ${selectedDoctor.full_name}`,
        order_id: bookingData.order_id,
        handler: async function(response: any) {
          try {
            await billingApi.verifyRazorpayPayment(bookingData.invoice_id, {
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_order_id: response.razorpay_order_id || bookingData.order_id,
              razorpay_signature: response.razorpay_signature,
              razorpay_invoice_id: response.razorpay_invoice_id || "",
              razorpay_invoice_receipt: response.razorpay_invoice_receipt || ""
            });
            toast.success("Payment successful! Appointment booked.");
            setBookingSuccess(true);
          } catch (verifyErr: any) {
            toast.error(verifyErr.message || "Failed to verify payment");
          }
        },
        theme: { color: "#0ea5e9" },
        modal: {
          ondismiss: function() {
            toast.info("Payment cancelled. Appointment not booked.");
          }
        }
      };
      
      const rzp = new window.Razorpay(options);
      rzp.open();

    } catch (err: any) {
      toast.error(err.message || 'Failed to book appointment');
      if (err.response?.status === 409) {
        // Slot just taken, reload slots
        const dateStr = format(date!, 'yyyy-MM-dd');
        schedulingApi.getOpenSlots(selectedDoctor.id, dateStr).then(setSlots);
        setSelectedSlot(null);
        setStep(2); // Go back to slot picking
      }
    } finally {
      setBookingLoading(false);
    }
  };

  if (bookingSuccess) {
    return (
      <SidebarLayout role="patient" links={navLinks}>
        <div className="max-w-2xl mx-auto mt-12 text-center p-12 bg-white rounded-2xl shadow-level-3 border border-slate-200">
          <div className="w-20 h-20 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-10 h-10" />
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-2">Booking Confirmed!</h2>
          <p className="text-slate-600 mb-8">
            Your appointment with <span className="font-semibold">Dr. {selectedDoctor?.full_name}</span> has been scheduled for{' '}
            <span className="font-semibold">{format(date!, 'MMM dd, yyyy')}</span> at <span className="font-semibold">{selectedSlot ? format(new Date(selectedSlot.slot_start), 'HH:mm') : ''}</span>.
          </p>
          <div className="flex justify-center gap-4">
            <Button onClick={() => navigate('/patient/appointments')} size="lg" className="bg-primary hover:bg-blue-800 text-white">
              Go to My Appointments
            </Button>
            <Button 
              onClick={async () => {
                  try {
                      // Note: using appointmentApi as that's where downloadInvoice is exported in api.ts
                      const res = await appointmentApi.downloadInvoice(bookingData!.invoice_id);
                      window.open(res.url, '_blank');
                  } catch(e) {
                      toast.error("Failed to download receipt");
                  }
              }} 
              variant="outline" 
              size="lg"
            >
              <FileText className="w-5 h-5 mr-2" /> Download Receipt
            </Button>
          </div>
        </div>
      </SidebarLayout>
    );
  }

  return (
    <SidebarLayout role="patient" links={navLinks}>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Book an Appointment</h1>
          <p className="text-slate-500">Follow the steps to schedule your visit.</p>
        </div>

        {/* Stepper */}
        <div className="flex items-center gap-2 mb-8 text-sm font-medium">
          <div className={`flex items-center gap-2 ${step >= 1 ? 'text-primary' : 'text-slate-400'}`}>
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step >= 1 ? 'bg-primary text-white' : 'bg-slate-200'}`}>1</span>
            Doctor
          </div>
          <ChevronRight className="w-4 h-4 text-slate-300 mx-2" />
          <div className={`flex items-center gap-2 ${step >= 2 ? 'text-primary' : 'text-slate-400'}`}>
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step >= 2 ? 'bg-primary text-white' : 'bg-slate-200'}`}>2</span>
            Date & Time
          </div>
          <ChevronRight className="w-4 h-4 text-slate-300 mx-2" />
          <div className={`flex items-center gap-2 ${step >= 3 ? 'text-primary' : 'text-slate-400'}`}>
            <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs ${step >= 3 ? 'bg-primary text-white' : 'bg-slate-200'}`}>3</span>
            Confirm
          </div>
        </div>

        <div className="bg-white rounded-2xl shadow-level-1 border border-slate-200 p-6 sm:p-8 min-h-[400px]">
          {loading ? (
            <PageLoader />
          ) : error ? (
            <ErrorMessage error={error} onRetry={() => window.location.reload()} />
          ) : (
            <>
              {/* STEP 1: DOCTOR */}
              {step === 1 && (
                <div className="space-y-6 animate-in fade-in slide-in-from-right-4">
                  <h2 className="text-xl font-bold text-slate-900">Choose a Specialist</h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {doctors.map(doctor => (
                      <div 
                        key={doctor.id}
                        onClick={() => { setSelectedDoctor(doctor); setStep(2); }}
                        className="cursor-pointer border rounded-xl p-4 flex items-center gap-4 hover:border-primary hover:bg-blue-50 transition-colors bg-white shadow-sm"
                      >
                        <div className="w-14 h-14 rounded-full bg-slate-100 flex items-center justify-center text-slate-400">
                          <Stethoscope className="w-6 h-6" />
                        </div>
                        <div>
                          <h3 className="font-semibold text-slate-900">{doctor.full_name.startsWith('Dr.') ? doctor.full_name : `Dr. ${doctor.full_name}`}</h3>
                          <p className="text-sm text-slate-500 capitalize">{doctor.specialization || 'General Physician'}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* STEP 2: DATE & SLOT */}
              {step === 2 && (
                <div className="space-y-6 animate-in fade-in slide-in-from-right-4">
                  <div className="flex items-center gap-4 border-b border-slate-100 pb-4">
                    <Button variant="ghost" size="icon" onClick={() => setStep(1)} className="-ml-2 text-slate-500">
                      <ArrowLeft className="w-5 h-5" />
                    </Button>
                    <div>
                      <h2 className="text-xl font-bold text-slate-900">Choose Date & Time</h2>
                      <p className="text-sm text-slate-500">with Dr. {selectedDoctor?.full_name}</p>
                    </div>
                  </div>

                  <div className="flex flex-col md:flex-row gap-8">
                    <div className="flex-1">
                      <Calendar
                        mode="single"
                        selected={date}
                        onSelect={setDate}
                        disabled={(d) => d < new Date(new Date().setHours(0,0,0,0))}
                        className="rounded-xl border border-slate-200 shadow-sm p-4 bg-white w-full"
                        classNames={{
                          root: "w-full relative",
                          months: "w-full relative",
                          month: "w-full",
                          month_grid: "w-full",
                          week: "flex w-full justify-between mt-2",
                          weekdays: "flex w-full justify-between",
                        }}
                      />
                    </div>
                    <div className="flex-1 min-w-[280px]">
                      {date ? (
                        slotsLoading ? (
                          <div className="flex justify-center p-8"><PageLoader /></div>
                        ) : slots.length > 0 ? (
                          <div className="space-y-4">
                            <h3 className="font-semibold text-slate-700">Available Slots on {format(date, 'MMM dd')}</h3>
                            <div className="grid grid-cols-3 gap-2">
                              {slots.map(slot => (
                                <button
                                  key={slot.id}
                                  onClick={() => setSelectedSlot(slot)}
                                  className={`py-2 px-1 text-sm font-medium rounded-lg border transition-colors ${
                                    selectedSlot?.id === slot.id
                                      ? 'bg-primary border-primary text-white shadow-md'
                                      : 'bg-white border-slate-200 text-slate-700 hover:border-primary hover:text-primary'
                                  }`}
                                >
                                  {format(new Date(slot.slot_start), 'HH:mm')}
                                </button>
                              ))}
                            </div>
                            <Button 
                              className="w-full mt-6 bg-primary hover:bg-blue-800 text-white" 
                              disabled={!selectedSlot}
                              onClick={() => setStep(3)}
                            >
                              Continue
                            </Button>
                          </div>
                        ) : (
                          <div className="text-center p-8 bg-slate-50 rounded-xl border border-slate-200">
                            <Clock className="w-8 h-8 text-slate-400 mx-auto mb-2" />
                            <p className="text-slate-600 font-medium">No slots available</p>
                            <p className="text-slate-500 text-sm">Please try another date.</p>
                          </div>
                        )
                      ) : (
                        <div className="h-full flex items-center justify-center text-slate-400 text-sm">
                          Select a date to view slots
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* STEP 3: CONFIRM */}
              {step === 3 && (
                <div className="space-y-6 animate-in fade-in slide-in-from-right-4">
                  <div className="flex items-center gap-4 border-b border-slate-100 pb-4">
                    <Button variant="ghost" size="icon" onClick={() => setStep(2)} className="-ml-2 text-slate-500">
                      <ArrowLeft className="w-5 h-5" />
                    </Button>
                    <h2 className="text-xl font-bold text-slate-900">Confirm Booking</h2>
                  </div>

                  <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 max-w-lg mx-auto">
                    <div className="space-y-4">
                      <div className="flex justify-between pb-4 border-b border-slate-200">
                        <span className="text-slate-500">Doctor</span>
                        <span className="font-semibold text-slate-900">Dr. {selectedDoctor?.full_name}</span>
                      </div>
                      <div className="flex justify-between pb-4 border-b border-slate-200">
                        <span className="text-slate-500">Date</span>
                        <span className="font-semibold text-slate-900">{date ? format(date, 'MMMM dd, yyyy') : ''}</span>
                      </div>
                      {selectedSlot && (
              <div className="mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-100 dark:border-blue-800">
                <h4 className="font-medium text-blue-900 dark:text-blue-100 mb-4">Booking Summary</h4>
                
                <div className="space-y-3 text-sm mb-6">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Doctor</span>
                    <span className="font-medium">Dr. {selectedDoctor?.full_name}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Date & Time</span>
                    <span className="font-medium">
                      {format(date!, 'MMM d, yyyy')} • {format(new Date(selectedSlot.slot_start), 'h:mm a')}
                    </span>
                  </div>
                  <div className="pt-3 border-t flex justify-between font-medium">
                    <span>Consultation Fee</span>
                    <span>₹{selectedDoctor?.consultation_fee || 500}</span>
                  </div>
                </div>

                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1" onClick={() => setSelectedSlot(null)}>
                    Change Time
                  </Button>
                  <Button 
                    className="flex-1"
                    onClick={handleBook}
                    disabled={bookingLoading}
                  >
                    {bookingLoading ? <PageLoader /> : 'Pay & Confirm Booking'}
                  </Button>
                </div>
              </div>
            )}
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </SidebarLayout>
  );
}
