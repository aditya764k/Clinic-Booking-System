import { useState, useEffect } from 'react';
import { SidebarLayout } from '@/components/SidebarLayout';
import { schedulingApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { 
  LayoutDashboard, Settings, Calendar as CalendarIcon, Clock, UserPlus, User
} from 'lucide-react';
import { Label } from '@/components/ui/label';
import { format } from 'date-fns';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import { useAuth } from '@/contexts/AuthContext';

const navLinks = [
  { label: 'Dashboard', href: '/doctor/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Add Colleague', href: '/doctor/add-colleague', icon: <UserPlus className="w-5 h-5" /> },
  { label: 'Settings', href: '/doctor/settings', icon: <Settings className="w-5 h-5" /> },
  { label: 'Profile', href: '/doctor/profile', icon: <User className="w-5 h-5" /> },
];

const DAYS = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'];

export default function DoctorSettings() {
  const { user } = useAuth();
  const [savingHours, setSavingHours] = useState(false);
  const [generating, setGenerating] = useState(false);
  
  // Working Hours State
  const [slotDuration, setSlotDuration] = useState(20);
  const [schedule, setSchedule] = useState<Record<string, { start: string, end: string } | null>>({
    monday: { start: '09:00', end: '17:00' },
    tuesday: { start: '09:00', end: '17:00' },
    wednesday: { start: '09:00', end: '17:00' },
    thursday: { start: '09:00', end: '17:00' },
    friday: { start: '09:00', end: '17:00' },
    saturday: { start: '09:00', end: '17:00' },
    sunday: { start: '09:00', end: '17:00' },
  });

  // Generate Slots State
  const [dateRange, setDateRange] = useState<{ from: Date | undefined; to: Date | undefined }>({
    from: undefined,
    to: undefined,
  });
  const [genProgress, setGenProgress] = useState<{ current: number, total: number, failed: number } | null>(null);

  useEffect(() => {
    const fetchHours = async () => {
      try {
        const config = await schedulingApi.getWorkingHours();
        setSlotDuration(config.slot_duration_minutes || 20);
        setSchedule(prev => {
          const newSchedule = { ...prev };
          DAYS.forEach(day => {
            if (config.schedule[day]) {
              newSchedule[day] = config.schedule[day];
            } else {
              newSchedule[day] = null;
            }
          });
          return newSchedule;
        });
      } catch (err: any) {
        console.error('Failed to load working hours', err);
      }
    };
    if (user?.profile_id) {
      fetchHours();
    }
  }, [user]);

  const handleSaveHours = async () => {
    setSavingHours(true);
    try {
      await schedulingApi.updateWorkingHours({
        slot_duration_minutes: slotDuration,
        schedule
      });
      toast.success('Working hours saved!');
    } catch (err: any) {
      toast.error(err.message || 'Failed to save working hours');
    } finally {
      setSavingHours(false);
    }
  };

  const handleGenerateSlots = async () => {
    if (!dateRange.from || !dateRange.to) {
      toast.error('Please select a date range.');
      return;
    }
    
    if (!user?.profile_id) {
      toast.error('Doctor profile ID not found. Please contact support or re-login.');
      setGenerating(false);
      return;
    }

    setGenerating(true);
    
    const startDate = new Date(dateRange.from);
    const endDate = new Date(dateRange.to);
    
    // Calculate all dates in range
    const datesToGenerate: string[] = [];
    for (let d = new Date(startDate); d <= endDate; d.setDate(d.getDate() + 1)) {
      datesToGenerate.push(format(new Date(d), 'yyyy-MM-dd'));
    }

    setGenProgress({ current: 0, total: datesToGenerate.length, failed: 0 });
    
    let failedCount = 0;
    
    for (let i = 0; i < datesToGenerate.length; i++) {
      try {
        await schedulingApi.generateSlots(user.profile_id, datesToGenerate[i]);
      } catch (e) {
        failedCount++;
      }
      setGenProgress(prev => prev ? { ...prev, current: i + 1, failed: failedCount } : null);
    }

    setGenerating(false);
    if (failedCount > 0) {
      toast.warning(`Slots generated. ${failedCount} dates failed (they might have been generated already).`);
    } else {
      toast.success(`Successfully generated slots for ${datesToGenerate.length} dates!`);
    }
    setGenProgress(null);
  };

  return (
    <SidebarLayout role="doctor" links={navLinks}>
      <div className="max-w-4xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Settings</h1>
          <p className="text-slate-500">Configure your working hours and manage slot availability.</p>
        </div>

        {/* Working Hours */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center gap-3">
            <Clock className="w-5 h-5 text-emerald-600" />
            <h2 className="font-semibold text-slate-900">Working Hours Configuration</h2>
          </div>
          
          <div className="p-6 md:p-8 space-y-8">
            <div className="space-y-3">
              <Label className="text-slate-700">Slot Duration (Minutes)</Label>
              <div className="flex items-center gap-4">
                {[15, 20, 30].map(duration => (
                  <button
                    key={duration}
                    onClick={() => setSlotDuration(duration)}
                    className={`px-4 py-2 rounded-lg border text-sm font-medium transition-colors ${
                      slotDuration === duration 
                        ? 'bg-emerald-50 border-emerald-500 text-emerald-700' 
                        : 'bg-white border-slate-200 text-slate-600 hover:border-emerald-300'
                    }`}
                  >
                    {duration} mins
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-4">
              <Label className="text-slate-700">Weekly Schedule</Label>
              <div className="border border-slate-200 rounded-xl divide-y divide-slate-100">
                {DAYS.map(day => {
                  const isActive = schedule[day] !== null;
                  return (
                    <div key={day} className="p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <label className="flex items-center gap-4 w-40 cursor-pointer group">
                        <input 
                          type="checkbox"
                          className="w-5 h-5 rounded border-slate-300 text-emerald-600 focus:ring-emerald-500 cursor-pointer"
                          checked={isActive} 
                          onChange={(e) => {
                            const checked = e.target.checked;
                            setSchedule(prev => ({
                              ...prev,
                              [day]: checked ? { start: '09:00', end: '17:00' } : null
                            }));
                          }} 
                        />
                        <span className="font-medium capitalize text-slate-700 group-hover:text-emerald-700 transition-colors">{day}</span>
                      </label>
                      <div className="flex items-center gap-2 sm:ml-auto">
                        <select 
                          disabled={!isActive}
                          value={isActive ? schedule[day]!.start : ''}
                          onChange={(e) => setSchedule(prev => ({...prev, [day]: { ...prev[day]!, start: e.target.value }}))}
                          className="bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-emerald-500 outline-none disabled:bg-slate-50 disabled:text-slate-400"
                        >
                          {Array.from({length: 24}).map((_, i) => {
                            const hr = i.toString().padStart(2, '0');
                            return (
                              <option key={`${hr}:00`} value={`${hr}:00`}>{hr}:00</option>
                            );
                          })}
                        </select>
                        <span className="text-slate-400">to</span>
                        <select 
                          disabled={!isActive}
                          value={isActive ? schedule[day]!.end : ''}
                          onChange={(e) => setSchedule(prev => ({...prev, [day]: { ...prev[day]!, end: e.target.value }}))}
                          className="bg-white border border-slate-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-emerald-500 outline-none disabled:bg-slate-50 disabled:text-slate-400"
                        >
                          {Array.from({length: 24}).map((_, i) => {
                            const hr = i.toString().padStart(2, '0');
                            return (
                              <option key={`${hr}:00`} value={`${hr}:00`}>{hr}:00</option>
                            );
                          })}
                        </select>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            <Button 
              onClick={handleSaveHours} 
              disabled={savingHours}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              {savingHours ? 'Saving...' : 'Save Working Hours'}
            </Button>
          </div>
        </div>

        {/* Generate Slots */}
        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="bg-slate-50 border-b border-slate-200 px-6 py-4 flex items-center gap-3">
            <CalendarIcon className="w-5 h-5 text-emerald-600" />
            <h2 className="font-semibold text-slate-900">Generate Slots</h2>
          </div>
          
          <div className="p-6 md:p-8 space-y-6">
            <p className="text-sm text-slate-500">
              Generate available appointment slots for a specific date range based on your working hours configuration.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4">
              <div className="flex flex-col gap-2 flex-1">
                <Label>From Date</Label>
                <Popover>
                  {/* @ts-ignore */}
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="justify-start text-left font-medium bg-white">
                      <CalendarIcon className="mr-2 h-4 w-4 text-emerald-600" />
                      {dateRange.from ? format(dateRange.from, 'MMMM dd, yyyy') : <span>Pick a date</span>}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={dateRange.from}
                      onSelect={(d) => setDateRange(prev => ({...prev, from: d}))}
                      // @ts-ignore
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>
              <div className="flex flex-col gap-2 flex-1">
                <Label>To Date</Label>
                <Popover>
                  {/* @ts-ignore */}
                  <PopoverTrigger asChild>
                    <Button variant="outline" className="justify-start text-left font-medium bg-white">
                      <CalendarIcon className="mr-2 h-4 w-4 text-emerald-600" />
                      {dateRange.to ? format(dateRange.to, 'MMMM dd, yyyy') : <span>Pick a date</span>}
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-0" align="start">
                    <Calendar
                      mode="single"
                      selected={dateRange.to}
                      onSelect={(d) => setDateRange(prev => ({...prev, to: d}))}
                      // @ts-ignore
                      initialFocus
                    />
                  </PopoverContent>
                </Popover>
              </div>
            </div>

            <Button 
              onClick={handleGenerateSlots} 
              disabled={generating || !dateRange.from || !dateRange.to}
              className="bg-emerald-600 hover:bg-emerald-700 text-white"
            >
              Generate Slots
            </Button>

            {genProgress && (
              <div className="text-sm font-medium text-emerald-600 bg-emerald-50 p-4 rounded-lg border border-emerald-100 flex items-center gap-3">
                <Clock className="w-4 h-4 animate-spin-slow" />
                Generating slots for {genProgress.total} dates... {genProgress.current}/{genProgress.total} done.
              </div>
            )}
          </div>
        </div>

      </div>
    </SidebarLayout>
  );
}
