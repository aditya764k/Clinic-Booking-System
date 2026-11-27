import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { SidebarLayout } from '@/components/SidebarLayout';
import { profileApi } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { PasswordInput } from '@/components/ui/password-input';
import { Label } from '@/components/ui/label';
import { toast } from 'sonner';
import { PageLoader } from '@/components/LoadingSpinner';
import { ErrorMessage } from '@/components/ErrorMessage';
import { 
  LayoutDashboard, Settings, UserPlus, User
} from 'lucide-react';

const navLinks = [
  { label: 'Dashboard', href: '/doctor/dashboard', icon: <LayoutDashboard className="w-5 h-5" /> },
  { label: 'Add Colleague', href: '/doctor/add-colleague', icon: <UserPlus className="w-5 h-5" /> },
  { label: 'Settings', href: '/doctor/settings', icon: <Settings className="w-5 h-5" /> },
  { label: 'Profile', href: '/doctor/profile', icon: <User className="w-5 h-5" /> },
];

export default function DoctorProfile() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hasPassword, setHasPassword] = useState(true);
  
  const [savingProfile, setSavingProfile] = useState(false);
  const [savingPassword, setSavingPassword] = useState(false);

  const { register: registerProfile, handleSubmit: handleSubmitProfile, reset: resetProfile, formState: { errors: profileErrors } } = useForm();
  const { register: registerPassword, handleSubmit: handleSubmitPassword, reset: resetPassword, formState: { errors: passwordErrors }, watch } = useForm();

  const newPassword = watch("new_password");

  useEffect(() => {
    const fetchProfile = async () => {
      try {
        setLoading(true);
        const data = await profileApi.getMyProfile();
        setHasPassword(data.has_password);
        resetProfile({
          full_name: data.full_name || '',
          specialization: data.specialization || ''
        });
      } catch (err: any) {
        setError(err.message || 'Failed to load profile');
      } finally {
        setLoading(false);
      }
    };
    fetchProfile();
  }, [resetProfile]);

  const onUpdateProfile = async (data: any) => {
    setSavingProfile(true);
    try {
      await profileApi.updateMyProfile({
        full_name: data.full_name,
        specialization: data.specialization
      });
      toast.success('Profile updated successfully');
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || 'Failed to update profile');
    } finally {
      setSavingProfile(false);
    }
  };

  const onUpdatePassword = async (data: any) => {
    setSavingPassword(true);
    try {
      await profileApi.updatePassword({
        current_password: data.current_password,
        new_password: data.new_password
      });
      toast.success('Password updated successfully');
      resetPassword();
    } catch (err: any) {
      toast.error(err.response?.data?.detail || err.message || 'Failed to update password');
    } finally {
      setSavingPassword(false);
    }
  };

  return (
    <SidebarLayout role="doctor" links={navLinks}>
      <div className="max-w-3xl mx-auto space-y-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My Profile</h1>
          <p className="text-slate-500">Manage your professional information and security settings.</p>
        </div>

        {loading ? (
          <PageLoader />
        ) : error ? (
          <ErrorMessage error={error} onRetry={() => window.location.reload()} />
        ) : (
          <div className="space-y-6">
            
            {/* Personal Information */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Professional Information</h2>
              <form onSubmit={handleSubmitProfile(onUpdateProfile)} className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor="full_name">Full Name</Label>
                    <Input
                      id="full_name"
                      {...registerProfile('full_name', { required: 'Full name is required' })}
                      className={profileErrors.full_name ? 'border-red-500' : ''}
                    />
                    {profileErrors.full_name && <p className="text-xs text-red-500">{profileErrors.full_name.message as string}</p>}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="specialization">Specialization</Label>
                    <Input
                      id="specialization"
                      {...registerProfile('specialization')}
                    />
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <Button type="submit" disabled={savingProfile}>
                    {savingProfile ? 'Saving...' : 'Save Changes'}
                  </Button>
                </div>
              </form>
            </div>

            {/* Security */}
            {hasPassword && (
              <div className="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
                <h2 className="text-lg font-semibold text-slate-900 mb-4">Security</h2>
              <form onSubmit={handleSubmitPassword(onUpdatePassword)} className="space-y-4">
                <div className="space-y-2 max-w-md">
                  <Label htmlFor="current_password">Current Password</Label>
                  <PasswordInput
                    id="current_password"
                    {...registerPassword('current_password', { required: 'Current password is required' })}
                  />
                  {passwordErrors.current_password && <p className="text-xs text-red-500">{passwordErrors.current_password.message as string}</p>}
                </div>

                <div className="space-y-2 max-w-md">
                  <Label htmlFor="new_password">New Password</Label>
                  <PasswordInput
                    id="new_password"
                    {...registerPassword('new_password', { required: 'New password is required', minLength: { value: 8, message: 'Minimum 8 characters' } })}
                  />
                  {passwordErrors.new_password && <p className="text-xs text-red-500">{passwordErrors.new_password.message as string}</p>}
                </div>

                <div className="space-y-2 max-w-md">
                  <Label htmlFor="confirm_password">Confirm New Password</Label>
                  <PasswordInput
                    id="confirm_password"
                    {...registerPassword('confirm_password', { 
                      required: 'Please confirm your password',
                      validate: value => value === newPassword || 'Passwords do not match'
                    })}
                  />
                  {passwordErrors.confirm_password && <p className="text-xs text-red-500">{passwordErrors.confirm_password.message as string}</p>}
                </div>

                <div className="flex justify-start pt-2">
                  <Button type="submit" variant="outline" className="border-primary text-primary hover:bg-primary/5" disabled={savingPassword}>
                    {savingPassword ? 'Updating Password...' : 'Change Password'}
                  </Button>
                </div>
              </form>
            </div>
            )}

          </div>
        )}
      </div>
    </SidebarLayout>
  );
}
