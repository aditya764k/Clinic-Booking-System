import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { SidebarLayout } from '@/components/SidebarLayout';
import { doctorApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { 
  LayoutDashboard, Settings, UserPlus, User
} from 'lucide-react';

const navLinks = [
  { label: 'Dashboard', href: '/doctor/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Add Colleague', href: '/doctor/add-colleague', icon: <UserPlus className="w-5 h-5" /> },
  { label: 'Settings', href: '/doctor/settings', icon: <Settings className="w-5 h-5" /> },
  { label: 'Profile', href: '/doctor/profile', icon: <User className="w-5 h-5" /> },
];

export default function AddColleague() {
  const [isLoading, setIsLoading] = useState(false);
  
  const { register, handleSubmit, reset, formState: { errors } } = useForm({
    defaultValues: {
      fullName: '',
      email: '',
      specialty: '',
      password: ''
    }
  });

  const onSubmit = async (data: any) => {
    setIsLoading(true);
    try {
      await doctorApi.addDoctor({
        full_name: data.fullName,
        email: data.email,
        specialty: data.specialty,
        password: data.password
      });
      toast.success('Doctor successfully added to the clinic!');
      reset();
    } catch (error: any) {
      toast.error(error.response?.data?.detail || error.message || 'Failed to add doctor');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <SidebarLayout role="doctor" links={navLinks}>
      <div className="max-w-2xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Add Colleague</h1>
          <p className="text-slate-500">Register a new doctor into the clinic system.</p>
        </div>

        <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              <div className="space-y-2">
                <Label htmlFor="fullName" className={errors.fullName ? 'text-red-500' : ''}>Full Name</Label>
                <Input
                  id="fullName"
                  placeholder="Dr. John Doe"
                  {...register('fullName', { required: 'Full name is required' })}
                  className={errors.fullName ? 'border-red-500' : ''}
                />
                {errors.fullName && <p className="text-xs text-red-500">{errors.fullName.message}</p>}
              </div>

              <div className="space-y-2">
                <Label htmlFor="specialty" className={errors.specialty ? 'text-red-500' : ''}>Specialty</Label>
                <Input
                  id="specialty"
                  placeholder="e.g. General Physician"
                  {...register('specialty', { required: 'Specialty is required' })}
                  className={errors.specialty ? 'border-red-500' : ''}
                />
                {errors.specialty && <p className="text-xs text-red-500">{errors.specialty.message}</p>}
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="email" className={errors.email ? 'text-red-500' : ''}>Email Address</Label>
              <Input
                id="email"
                type="email"
                placeholder="doctor@trimurticlinic.com"
                {...register('email', { required: 'Email is required' })}
                className={errors.email ? 'border-red-500' : ''}
              />
              {errors.email && <p className="text-xs text-red-500">{errors.email.message}</p>}
            </div>

            <div className="space-y-2">
              <Label htmlFor="password" className={errors.password ? 'text-red-500' : ''}>Temporary Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                {...register('password', { required: 'Password is required', minLength: { value: 8, message: 'Minimum 8 characters' } })}
                className={errors.password ? 'border-red-500' : ''}
              />
              {errors.password && <p className="text-xs text-red-500">{errors.password.message}</p>}
            </div>

            <Button type="submit" disabled={isLoading} className="w-full bg-emerald-600 hover:bg-emerald-700">
              {isLoading ? 'Creating Account...' : 'Add Doctor'}
            </Button>
          </form>
        </div>
      </div>
    </SidebarLayout>
  );
}
