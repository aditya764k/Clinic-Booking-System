import type { ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { LogOut } from 'lucide-react';

interface SidebarLayoutProps {
  children: ReactNode;
  role: 'patient' | 'doctor' | 'receptionist';
  links: { label: string; href: string; icon: ReactNode }[];
}

const roleColors = {
  patient: 'bg-sky-500',
  doctor: 'bg-emerald-600',
  receptionist: 'bg-violet-600',
};

const activeColors = {
  patient: 'bg-sky-50 text-sky-600 border-l-sky-500',
  doctor: 'bg-emerald-50 text-emerald-700 border-l-emerald-600',
  receptionist: 'bg-violet-50 text-violet-700 border-l-violet-600',
};

export function SidebarLayout({ children, role, links }: SidebarLayoutProps) {
  const { pathname } = useLocation();
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate('/');
  };

  const topBarColor = roleColors[role];
  const activeClass = activeColors[role];

  return (
    <div className="flex min-h-screen bg-slate-50 flex-col md:flex-row relative pb-16 md:pb-0">
      {/* Top Accent Bar */}
      <div className={`fixed top-0 left-0 right-0 h-1 z-50 ${topBarColor}`}></div>

      {/* Sidebar (Desktop) */}
      <aside className="hidden md:flex flex-col w-64 bg-white border-r border-slate-200 fixed top-1 bottom-0 z-40">
        <div className="p-6">
          <Link to="/" className="text-xl font-hero font-bold text-slate-900 block">
            Trimurti Clinic
          </Link>
          <p className="text-xs text-slate-500 capitalize mt-1 border-t border-slate-100 pt-1">
            {role} Portal
          </p>
        </div>
        
        <nav className="flex-1 px-4 space-y-1 overflow-y-auto">
          {links.map((link) => {
            const isActive = pathname === link.href || pathname.startsWith(link.href + '/');
            return (
              <Link
                key={link.href}
                to={link.href}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-colors border-l-[3px] ${
                  isActive
                    ? activeClass
                    : 'border-l-transparent text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                {link.icon}
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-slate-100">
          <div className="flex items-center gap-3 px-4 py-3 mb-2">
            <div className="w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-600 font-bold text-xs uppercase">
              {(user?.full_name || 'U').charAt(0)}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-slate-900 truncate">{user?.full_name || 'User'}</p>
              <p className="text-xs text-slate-500 truncate">{user?.email}</p>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="flex w-full items-center gap-3 px-4 py-2 rounded-lg text-sm font-medium text-slate-500 hover:bg-slate-100 hover:text-slate-900 transition-colors"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </div>
      </aside>

      {/* Bottom Tab Bar (Mobile) */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-slate-200 flex justify-around p-2 z-50 safe-area-pb">
        {links.map((link) => {
          const isActive = pathname === link.href || pathname.startsWith(link.href + '/');
          return (
            <Link
              key={link.href}
              to={link.href}
              className={`flex flex-col items-center p-2 rounded-lg min-w-[64px] ${
                isActive ? 'text-primary' : 'text-slate-500'
              }`}
            >
              {link.icon}
              <span className="text-[10px] font-medium mt-1">{link.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Main Content */}
      <main className="flex-1 md:ml-64 pt-6 px-4 md:px-8 pb-12">
        {/* Mobile Header */}
        <div className="md:hidden flex items-center justify-between bg-white p-4 rounded-xl border border-slate-200 mb-6 shadow-sm">
          <div>
            <h1 className="font-hero font-bold text-slate-900">Trimurti Clinic</h1>
            <p className="text-xs text-slate-500 capitalize">{role} Portal</p>
          </div>
          <button onClick={handleLogout} className="p-2 text-slate-400 hover:text-slate-600 bg-slate-50 rounded-lg">
            <LogOut className="w-5 h-5" />
          </button>
        </div>
        
        {children}
      </main>
    </div>
  );
}
