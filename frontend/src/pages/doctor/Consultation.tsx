import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { clinicalNoteApi, appointmentApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { PageLoader } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { 
  ArrowLeft, Sparkles, CheckCircle, FileText, User, Plus, Trash2, History, X, FileDown
} from 'lucide-react';
import { Label } from '@/components/ui/label';
import { format } from 'date-fns';

export default function Consultation() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [appointment, setAppointment] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loadingAppt, setLoadingAppt] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Phases: 'A' (Shorthand), 'B' (Review AI), 'C' (Manual)
  const [phase, setPhase] = useState<'A' | 'B' | 'C'>('A');
  const [shorthand, setShorthand] = useState('');
  
  const [draft, setDraft] = useState({
    symptoms: '',
    diagnosis: '',
    treatmentPlan: '',
    prescriptions: [] as any[],
    labTests: [] as any[],
    followUpDate: '',
    additionalTreatmentCharges: '',
    treatmentChargeDescription: ''
  });

  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiLoadingText, setAiLoadingText] = useState('Analysing symptoms...');
  const [completing, setCompleting] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    const fetchAppt = async () => {
      try {
        const dateStr = format(new Date(), 'yyyy-MM-dd');
        const queue = await appointmentApi.getMyQueue(dateStr);
        const appt = queue.find((a: any) => a.id === Number(id));
        if (!appt) {
          throw new Error('Appointment not found in today\'s queue. It may have already been completed.');
        }
        setAppointment(appt);
        
        // Fetch patient history
        try {
          const hist = await clinicalNoteApi.getPatientHistory(appt.patient_id);
          setHistory(hist);
        } catch (hErr) {
          console.error("Failed to load history", hErr);
        }
        
      } catch (err: any) {
        setError(err.message || 'Cannot load appointment details');
      } finally {
        setLoadingAppt(false);
      }
    };
    fetchAppt();

    const saved = sessionStorage.getItem(`consultation_${id}`);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        setPhase(parsed.phase || 'A');
        setShorthand(parsed.shorthand || '');
        setDraft(parsed.draft || { symptoms: '', diagnosis: '', treatmentPlan: '', prescriptions: [], labTests: [], followUpDate: '' });
      } catch {
        // Ignore corrupt sessionStorage
      }
    }
  }, [id]);

  useEffect(() => {
    if (!showSuccess) {
      sessionStorage.setItem(`consultation_${id}`, JSON.stringify({ phase, shorthand, draft }));
    }
  }, [phase, shorthand, draft, id, showSuccess]);

  const handleGenerateAI = async () => {
    if (shorthand.length < 10) {
      toast.error('Please enter at least 10 characters for a meaningful draft.');
      return;
    }
    
    setAiGenerating(true);
    setAiLoadingText('Analysing symptoms...');
    
    const interval = setInterval(() => {
      setAiLoadingText(prev => 
        prev === 'Analysing symptoms...' ? 'Generating draft...' : 
        prev === 'Generating draft...' ? 'Almost ready...' : 'Analysing symptoms...'
      );
    }, 2000);

    try {
      const response = await clinicalNoteApi.generateDraft(Number(id), shorthand);
      if (response) {
        setDraft({
          symptoms: response.symptoms || '',
          diagnosis: response.diagnosis || '',
          treatmentPlan: response.treatment_plan || '',
          prescriptions: response.prescriptions || [],
          labTests: response.lab_tests_recommended || [],
          followUpDate: response.follow_up_date || '',
          additionalTreatmentCharges: '',
          treatmentChargeDescription: ''
        });
        setPhase('B');
      } else {
        setPhase('C');
      }
    } catch {
      setPhase('C');
    } finally {
      clearInterval(interval);
      setAiGenerating(false);
    }
  };

  const handleConfirmAndComplete = async () => {
    if (!draft.symptoms.trim() || !draft.diagnosis.trim() || !draft.treatmentPlan.trim()) {
      toast.error('Symptoms, Diagnosis, and Treatment Plan must be filled.');
      return;
    }

    setCompleting(true);
    try {
      await clinicalNoteApi.finalizeNote(Number(id), {
        symptoms: draft.symptoms,
        diagnosis: draft.diagnosis,
        treatment_plan: draft.treatmentPlan,
        prescriptions: draft.prescriptions,
        lab_tests_recommended: draft.labTests,
        follow_up_date: draft.followUpDate || null,
        additional_treatment_charges: draft.additionalTreatmentCharges ? parseFloat(draft.additionalTreatmentCharges) : null,
        treatment_charge_description: draft.treatmentChargeDescription || null
      });

      try {
        await clinicalNoteApi.completeVisit(Number(id));
        sessionStorage.removeItem(`consultation_${id}`);
        setShowSuccess(true);
      } catch (completeErr: any) {
        toast.error('Note saved but could not mark complete. Please retry completing.');
      }
    } catch (finalizeErr: any) {
      toast.error(finalizeErr.message || 'Failed to save clinical note.');
    } finally {
      setCompleting(false);
    }
  };

  const addPrescription = () => {
    setDraft({
      ...draft,
      prescriptions: [...draft.prescriptions, { medicine_name: '', dosage: '', frequency: '', duration: '', instructions: '' }]
    });
  };

  const updatePrescription = (index: number, field: string, value: string) => {
    const updated = [...draft.prescriptions];
    updated[index][field] = value;
    setDraft({ ...draft, prescriptions: updated });
  };

  const removePrescription = (index: number) => {
    const updated = draft.prescriptions.filter((_, i) => i !== index);
    setDraft({ ...draft, prescriptions: updated });
  };

  const addLabTest = () => {
    setDraft({
      ...draft,
      labTests: [...draft.labTests, { test_name: '', reason: '' }]
    });
  };

  const updateLabTest = (index: number, field: string, value: string) => {
    const updated = [...draft.labTests];
    updated[index][field] = value;
    setDraft({ ...draft, labTests: updated });
  };

  const removeLabTest = (index: number) => {
    const updated = draft.labTests.filter((_, i) => i !== index);
    setDraft({ ...draft, labTests: updated });
  };

  const renderDraftFields = () => (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label>Symptoms</Label>
        <textarea
          value={draft.symptoms}
          onChange={(e) => setDraft({...draft, symptoms: e.target.value})}
          className="w-full min-h-[80px] p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-y bg-white"
        />
      </div>
      <div className="space-y-2">
        <Label>Diagnosis</Label>
        <textarea
          value={draft.diagnosis}
          onChange={(e) => setDraft({...draft, diagnosis: e.target.value})}
          className="w-full min-h-[80px] p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-y bg-white"
        />
      </div>
      <div className="space-y-2">
        <Label>Treatment Plan</Label>
        <textarea
          value={draft.treatmentPlan}
          onChange={(e) => setDraft({...draft, treatmentPlan: e.target.value})}
          className="w-full min-h-[80px] p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-y bg-white"
        />
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label className="text-base font-semibold">Prescriptions</Label>
          <Button variant="outline" size="sm" onClick={addPrescription}>
            <Plus className="w-4 h-4 mr-1" /> Add Medicine
          </Button>
        </div>
        {draft.prescriptions.map((rx, idx) => (
          <div key={idx} className="p-4 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-3 relative">
            <Button variant="ghost" size="icon" onClick={() => removePrescription(idx)} className="absolute top-2 right-2 text-red-500 hover:text-red-700 hover:bg-red-50">
              <Trash2 className="w-4 h-4" />
            </Button>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pr-8">
              <input placeholder="Medicine Name" value={rx.medicine_name} onChange={(e) => updatePrescription(idx, 'medicine_name', e.target.value)} className="p-2 border rounded text-sm bg-white" />
              <input placeholder="Dosage (e.g. 500mg)" value={rx.dosage} onChange={(e) => updatePrescription(idx, 'dosage', e.target.value)} className="p-2 border rounded text-sm bg-white" />
              <input placeholder="Frequency (e.g. BID)" value={rx.frequency} onChange={(e) => updatePrescription(idx, 'frequency', e.target.value)} className="p-2 border rounded text-sm bg-white" />
              <input placeholder="Duration (e.g. 3 days)" value={rx.duration} onChange={(e) => updatePrescription(idx, 'duration', e.target.value)} className="p-2 border rounded text-sm bg-white" />
              <input placeholder="Instructions" value={rx.instructions} onChange={(e) => updatePrescription(idx, 'instructions', e.target.value)} className="p-2 border rounded text-sm bg-white md:col-span-2" />
            </div>
          </div>
        ))}
        {draft.prescriptions.length === 0 && <p className="text-sm text-slate-500 italic">No medicines prescribed.</p>}
      </div>

      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Label className="text-base font-semibold">Lab Tests</Label>
          <Button variant="outline" size="sm" onClick={addLabTest}>
            <Plus className="w-4 h-4 mr-1" /> Add Lab Test
          </Button>
        </div>
        {draft.labTests.map((lab, idx) => (
          <div key={idx} className="p-4 bg-slate-50 border border-slate-200 rounded-lg flex flex-col gap-3 relative">
            <Button variant="ghost" size="icon" onClick={() => removeLabTest(idx)} className="absolute top-2 right-2 text-red-500 hover:text-red-700 hover:bg-red-50">
              <Trash2 className="w-4 h-4" />
            </Button>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pr-8">
              <input placeholder="Test Name" value={lab.test_name} onChange={(e) => updateLabTest(idx, 'test_name', e.target.value)} className="p-2 border rounded text-sm bg-white" />
              <input placeholder="Reason" value={lab.reason} onChange={(e) => updateLabTest(idx, 'reason', e.target.value)} className="p-2 border rounded text-sm bg-white" />
            </div>
          </div>
        ))}
        {draft.labTests.length === 0 && <p className="text-sm text-slate-500 italic">No lab tests recommended.</p>}
      </div>

      <div className="space-y-2">
        <Label>Follow-up Date</Label>
        <input 
          type="date"
          value={draft.followUpDate}
          onChange={(e) => setDraft({...draft, followUpDate: e.target.value})}
          className="w-full p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white"
        />
      </div>

      <div className="pt-4 border-t border-slate-200">
        <h3 className="font-semibold text-slate-800 mb-4">Additional Treatment Charges (Optional)</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <Label>Charge Amount (₹)</Label>
            <input 
              type="number"
              min="0"
              step="0.01"
              placeholder="e.g. 500"
              value={draft.additionalTreatmentCharges}
              onChange={(e) => setDraft({...draft, additionalTreatmentCharges: e.target.value})}
              className="w-full p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white"
            />
          </div>
          <div className="space-y-2">
            <Label>Charge Description</Label>
            <input 
              type="text"
              placeholder="e.g. Dressing, Injection, etc."
              value={draft.treatmentChargeDescription}
              onChange={(e) => setDraft({...draft, treatmentChargeDescription: e.target.value})}
              className="w-full p-3 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent bg-white"
            />
          </div>
        </div>
      </div>
      
      <div className="pt-4 flex flex-col sm:flex-row gap-4 items-center justify-between border-t border-slate-200 mt-6 pt-6">
        <Button 
          onClick={handleConfirmAndComplete} 
          disabled={completing}
          className="w-full sm:w-auto bg-emerald-600 hover:bg-emerald-700 text-white font-bold px-8"
        >
          {completing ? 'Completing...' : 'Confirm & Complete Visit'}
        </Button>
        {phase === 'B' && (
          <button 
            onClick={() => {
              setDraft({ symptoms: '', diagnosis: '', treatmentPlan: '', prescriptions: [], labTests: [], followUpDate: '', additionalTreatmentCharges: '', treatmentChargeDescription: '' });
              setPhase('A');
            }}
            className="text-sm font-medium text-slate-500 hover:text-primary whitespace-nowrap"
          >
            Re-enter shorthand
          </button>
        )}
      </div>
    </div>
  );

  if (showSuccess) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
        <div className="bg-white rounded-3xl p-8 max-w-md w-full shadow-level-3 border border-slate-200 text-center animate-in zoom-in-95 duration-300">
          <div className="w-20 h-20 bg-emerald-100 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10" />
          </div>
          <h2 className="text-2xl font-bold text-slate-900 mb-2">Visit Completed!</h2>
          <p className="text-slate-500 mb-8">
            The patient has been marked as completed. The prescription has been generated.
          </p>
          <Button 
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={() => navigate('/doctor/dashboard')}
          >
            Back to My Queue
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50 font-sans flex flex-col relative overflow-hidden">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 py-4 px-6 sticky top-0 z-10 shadow-sm">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={() => navigate('/doctor/dashboard')} className="text-slate-500 shrink-0">
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="font-bold text-lg text-slate-900 leading-tight">Consultation</h1>
              <span className="text-xs font-medium text-indigo-600 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-indigo-500 animate-pulse"></span> In Progress
              </span>
            </div>
          </div>
          <Button variant="outline" onClick={() => setShowHistory(true)} className="flex items-center gap-2">
            <History className="w-4 h-4" /> Patient History
          </Button>
        </div>
      </header>

      {/* History Slide-out Panel */}
      <div className={`fixed inset-y-0 right-0 w-full max-w-md bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-in-out ${showHistory ? 'translate-x-0' : 'translate-x-full'}`}>
        <div className="flex items-center justify-between p-6 border-b border-slate-200 bg-slate-50">
          <h2 className="text-lg font-bold text-slate-900 flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-600" /> Past Medical History
          </h2>
          <Button variant="ghost" size="icon" onClick={() => setShowHistory(false)}>
            <X className="w-5 h-5" />
          </Button>
        </div>
        <div className="p-6 overflow-y-auto h-[calc(100vh-80px)] space-y-6">
          {history.length === 0 ? (
            <p className="text-slate-500 text-center py-8">No past clinical notes found for this patient.</p>
          ) : (
            history.map((note, i) => (
              <div key={i} className="border border-slate-200 rounded-xl p-5 shadow-sm">
                <div className="flex justify-between items-center mb-3 border-b pb-2">
                  <span className="font-semibold text-slate-900 text-sm">
                    {new Date(note.finalized_at).toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' })}
                  </span>
                  <Button variant="ghost" size="sm" className="h-7 text-xs text-indigo-600" onClick={async () => {
                    try {
                      const res = await clinicalNoteApi.downloadPrescription(note.appointment_id);
                      window.open(res.url, '_blank');
                    } catch (e) {
                      toast.error("Could not download prescription");
                    }
                  }}>
                    <FileDown className="w-3.5 h-3.5 mr-1" /> PDF
                  </Button>
                </div>
                {note.diagnosis && (
                  <div className="mb-2">
                    <span className="text-xs font-semibold text-slate-500 uppercase block mb-1">Diagnosis</span>
                    <p className="text-sm text-slate-800">{note.diagnosis}</p>
                  </div>
                )}
                {note.prescriptions && note.prescriptions.length > 0 && (
                  <div>
                    <span className="text-xs font-semibold text-slate-500 uppercase block mb-1">Medicines</span>
                    <ul className="list-disc pl-4 text-sm text-slate-700">
                      {note.prescriptions.map((rx: any, idx: number) => (
                        <li key={idx}>{rx.medicine_name} {rx.dosage} ({rx.frequency})</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
      
      {/* Overlay for History Panel */}
      {showHistory && (
        <div className="fixed inset-0 bg-slate-900/20 backdrop-blur-sm z-40 transition-opacity" onClick={() => setShowHistory(false)}></div>
      )}

      <main className="flex-1 max-w-6xl mx-auto w-full p-4 lg:p-8">
        {loadingAppt ? (
          <PageLoader />
        ) : error ? (
          <ErrorMessage error={error} onRetry={() => window.location.reload()} />
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full">
            
            {/* Left Panel: Patient Info */}
            <div className="lg:col-span-4 space-y-6">
              <div className="bg-white rounded-2xl p-6 border border-slate-200 shadow-sm sticky top-24">
                <div className="w-16 h-16 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 mb-4 mx-auto">
                  <User className="w-8 h-8" />
                </div>
                <h2 className="text-xl font-bold text-slate-900 text-center mb-1">{appointment?.patient_name}</h2>
                <div className="flex flex-col gap-2 mt-6">
                  <div className="flex justify-between text-sm py-2 border-b border-slate-100">
                    <span className="text-slate-500">Time Slot</span>
                    <span className="font-medium text-slate-900">
                      {appointment?.slot_start
                        ? new Date(appointment.slot_start).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false })
                        : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm py-2 border-b border-slate-100">
                    <span className="text-slate-500">Status</span>
                    <span className="font-medium text-indigo-600 uppercase tracking-wider text-[10px] bg-indigo-50 px-2 py-0.5 rounded-full border border-indigo-100">
                      Active
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Right Panel: Clinical Notes */}
            <div className="lg:col-span-8 bg-white rounded-2xl border border-slate-200 shadow-sm flex flex-col overflow-hidden relative">
              <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center gap-2">
                <FileText className="w-5 h-5 text-slate-500" />
                <h3 className="font-semibold text-slate-900">Clinical Prescription</h3>
              </div>
              
              <div className="p-6 md:p-8 flex-1">
                
                {/* Phase A: Shorthand */}
                {phase === 'A' && (
                  <div className="h-full flex flex-col animate-in fade-in">
                    <Label className="mb-2 text-base text-slate-700">Enter shorthand symptoms & observations...</Label>
                    <textarea
                      value={shorthand}
                      onChange={(e) => setShorthand(e.target.value)}
                      placeholder="e.g., fever 3d, cough, viral pharyngitis, paracetamol 500mg bid 3d, cbc test, see me nxt wk"
                      className="flex-1 w-full p-4 border border-slate-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent resize-none bg-slate-50/50 min-h-[300px]"
                    />
                    <div className="flex items-center justify-between mt-4">
                      <span className="text-xs text-slate-400 font-medium">
                        {shorthand.length} chars (min 10)
                      </span>
                      <Button 
                        onClick={handleGenerateAI}
                        disabled={aiGenerating || shorthand.length < 10}
                        className="bg-indigo-600 hover:bg-indigo-700 text-white font-medium pl-4 pr-6"
                      >
                        {aiGenerating ? (
                          <div className="flex items-center gap-2">
                            <Sparkles className="w-4 h-4 animate-spin-slow" />
                            {aiLoadingText}
                          </div>
                        ) : (
                          <div className="flex items-center gap-2">
                            <Sparkles className="w-4 h-4" />
                            Generate AI Prescription
                          </div>
                        )}
                      </Button>
                    </div>
                  </div>
                )}

                {/* Phase B: AI Draft Review */}
                {phase === 'B' && (
                  <div className="animate-in slide-in-from-right-8 duration-500">
                    <div className="mb-6 bg-amber-50 border border-amber-200 border-l-[4px] border-l-amber-600 rounded-r-lg p-4 flex items-start gap-3">
                      <Sparkles className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                      <p className="text-sm font-medium text-amber-800 leading-relaxed">
                        <span className="font-bold">AI Draft</span> — Please review and edit before confirming. You are responsible for the final prescription.
                      </p>
                    </div>
                    {renderDraftFields()}
                  </div>
                )}

                {/* Phase C: Manual Entry */}
                {phase === 'C' && (
                  <div className="animate-in fade-in">
                    <div className="mb-6 bg-slate-100 border border-slate-200 rounded-lg p-4 text-center">
                      <p className="text-sm font-medium text-slate-600">
                        AI draft unavailable. Please enter the prescription manually.
                      </p>
                    </div>
                    {renderDraftFields()}
                  </div>
                )}

              </div>
            </div>

          </div>
        )}
      </main>
    </div>
  );
}
