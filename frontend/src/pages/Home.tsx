import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '@/contexts/AuthContext';
import { Button } from '@/components/ui/button';
import { 
  Plus, Sparkles, CalendarCheck, ShieldCheck, 
  ChevronDown, ArrowRight, User
} from 'lucide-react';

export default function Home() {
  const { user, isAuthenticated, logout } = useAuth();
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 60);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navClass = `fixed top-0 w-full z-50 transition-all duration-300 ${
    scrolled 
      ? 'bg-white/90 backdrop-blur-md border-b border-slate-200 shadow-sm py-3' 
      : 'bg-transparent py-5'
  }`;

  return (
    <div className="min-h-screen bg-slate-50 flex flex-col font-sans">
      
      {/* NAVBAR */}
      <nav className={navClass}>
        <div className="max-w-7xl mx-auto px-6 flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2 group">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary group-hover:bg-primary group-hover:text-white transition-colors">
              <Plus className="w-5 h-5 stroke-[2.5]" />
            </div>
            <span className="font-semibold text-lg text-slate-900 tracking-tight">Trimurti Clinic</span>
          </Link>
          
          <div className="hidden md:flex items-center gap-6">
            {!isAuthenticated ? (
              <>
                <Link to="/login">
                  <Button variant="outline" className="font-semibold text-primary border-primary hover:bg-blue-50">
                    Login
                  </Button>
                </Link>
                <Link to="/register">
                  <Button className="bg-primary hover:bg-blue-800 text-white font-semibold">
                    Book Appointment
                  </Button>
                </Link>
              </>
            ) : (
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-blue-50 text-primary flex items-center justify-center font-bold text-sm">
                    {user?.full_name?.charAt(0) || <User className="w-4 h-4" />}
                  </div>
                  <span className="text-sm font-medium text-slate-700">{user?.full_name}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-500 capitalize border border-slate-200">
                    {user?.role}
                  </span>
                </div>
                <Link to={`/${user?.role}/dashboard`}>
                  <Button variant="ghost" className="text-primary hover:bg-blue-50">
                    My Dashboard
                  </Button>
                </Link>
                <Button variant="ghost" onClick={logout} className="text-slate-500 hover:text-slate-900 hover:bg-slate-100">
                  Logout
                </Button>
              </div>
            )}
          </div>
        </div>
      </nav>

      {/* HERO SECTION */}
      <section 
        className="relative pt-32 pb-20 lg:pt-48 lg:pb-32 overflow-hidden"
        style={{ background: 'linear-gradient(135deg, #EFF6FF 0%, #F8FAFC 50%, #F0FDF4 100%)' }}
      >
        <div className="max-w-7xl mx-auto px-6 flex flex-col lg:flex-row items-center gap-12">
          
          {/* Hero Content */}
          <div className="flex-1 text-center lg:text-left z-10">
            <h1 className="font-hero text-5xl lg:text-6xl font-bold text-slate-900 mb-6 leading-tight">
              Trimurti Clinic
            </h1>
            <div className="w-16 h-1 bg-primary rounded-full mx-auto lg:mx-0 mb-6"></div>
            <h2 className="text-2xl font-medium text-slate-700 mb-4">
              Modern Healthcare, Seamlessly Scheduled
            </h2>
            <p className="text-lg text-slate-500 mb-8 max-w-lg mx-auto lg:mx-0">
              AI-powered appointments. Instant confirmations. Zero wait time confusion.
            </p>
            
            <div className="flex flex-col sm:flex-row items-center justify-center lg:justify-start gap-4 mb-12">
              <Link to={isAuthenticated ? `/${user?.role}/dashboard` : "/register"}>
                <Button size="lg" className="bg-primary hover:bg-blue-800 text-white w-full sm:w-auto text-base">
                  Book an Appointment <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
              <Link to="/login">
                <Button size="lg" variant="outline" className="text-primary border-primary hover:bg-blue-50 w-full sm:w-auto text-base">
                  Staff Login
                </Button>
              </Link>
            </div>

            {/* Trust Badges Inline */}
            <div className="flex flex-wrap items-center justify-center lg:justify-start gap-6 text-sm font-medium text-slate-600">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-green-600" /> Zero double-bookings
              </div>
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-4 h-4 text-blue-600" /> Secure payments
              </div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-amber-500" /> AI-assisted notes
              </div>
              <div className="flex items-center gap-2">
                <CalendarCheck className="w-4 h-4 text-indigo-500" /> Instant confirmation
              </div>
            </div>
          </div>

          {/* Hero Image */}
          <div className="flex-1 relative animate-float">
            <div className="relative rounded-2xl overflow-hidden shadow-level-2 border border-slate-200 bg-white">
              <img 
                src="https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?w=1200&q=80" 
                alt="Modern Clinic Interior" 
                className="w-full h-auto object-cover max-h-[500px]"
                loading="lazy"
              />
            </div>
            {/* Floating Glass Chip */}
            <div className="absolute -bottom-6 -left-6 lg:-left-12 glass-panel px-6 py-4 rounded-xl flex items-center gap-3">
              <div className="text-amber-500 text-xl">⭐</div>
              <div className="font-semibold text-slate-800">Trusted by 500+ patients</div>
            </div>
          </div>
        </div>

        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 animate-bounce text-primary">
          <ChevronDown className="w-6 h-6" />
        </div>
      </section>

      {/* FEATURES SECTION */}
      <section className="py-24 bg-white relative">
        <div className="max-w-7xl mx-auto px-6">
          <div className="text-center mb-16">
            <span className="text-sm font-bold text-primary uppercase tracking-widest mb-2 block">Why Trimurti Clinic</span>
            <h2 className="text-3xl font-bold text-slate-900">Everything a modern clinic needs</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-level-1 hover:shadow-level-2 hover:-translate-y-1 transition-all duration-200">
              <div className="w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center mb-6">
                <Sparkles className="w-6 h-6 text-primary" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">AI Clinical Notes</h3>
              <p className="text-slate-600 leading-relaxed">
                Doctors dictate shorthand — AI drafts a structured note. Doctor reviews, edits, and confirms. Always in control.
              </p>
            </div>

            <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-level-1 hover:shadow-level-2 hover:-translate-y-1 transition-all duration-200">
              <div className="w-12 h-12 rounded-xl bg-green-50 flex items-center justify-center mb-6">
                <CalendarCheck className="w-6 h-6 text-emerald-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">Smart Scheduling</h3>
              <p className="text-slate-600 leading-relaxed">
                Real-time slot availability. Database-level constraint prevents double-booking. Zero conflicts.
              </p>
            </div>

            <div className="bg-white rounded-2xl p-8 border border-slate-200 shadow-level-1 hover:shadow-level-2 hover:-translate-y-1 transition-all duration-200">
              <div className="w-12 h-12 rounded-xl bg-orange-50 flex items-center justify-center mb-6">
                <ShieldCheck className="w-6 h-6 text-amber-600" />
              </div>
              <h3 className="text-xl font-semibold text-slate-900 mb-3">Secure Payments</h3>
              <p className="text-slate-600 leading-relaxed">
                Razorpay + Cash, both cryptographically accounted. Every rupee traced and invoiced automatically.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* HOW IT WORKS (TIMELINE) */}
      <section className="py-24 bg-slate-50">
        <div className="max-w-4xl mx-auto px-6 text-center">
          <h2 className="text-3xl font-bold text-slate-900 mb-16">How It Works</h2>
          
          <div className="flex flex-col md:flex-row items-center justify-between relative gap-8 md:gap-0">
            {/* Connecting Line (Desktop) */}
            <div className="hidden md:block absolute top-6 left-12 right-12 h-0.5 border-t-2 border-dashed border-slate-300 z-0"></div>
            
            {[
              { num: 1, title: 'Register', desc: 'Create your patient account instantly.' },
              { num: 2, title: 'Browse', desc: 'Find open slots by doctor.' },
              { num: 3, title: 'Book', desc: 'Confirm your time securely.' },
              { num: 4, title: 'Consult', desc: 'Visit, pay, and get your invoice.' }
            ].map((step, idx) => (
              <div key={idx} className="relative z-10 flex flex-col items-center flex-1">
                <div className="w-12 h-12 rounded-full bg-white border-2 border-primary text-primary flex items-center justify-center font-bold text-lg mb-4 shadow-sm">
                  {step.num}
                </div>
                <h4 className="font-semibold text-slate-900 mb-1">{step.title}</h4>
                <p className="text-sm text-slate-500 max-w-[150px]">{step.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* DOCTOR SECTION */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row items-center gap-16">
          <div className="flex-1 relative">
            <img 
              src="https://images.unsplash.com/photo-1612349317150-e413f6a5b16d?w=600&q=80" 
              alt="Our Specialists" 
              className="rounded-2xl shadow-level-2 w-full object-cover"
              loading="lazy"
            />
            {/* Floating stats card */}
            <div className="absolute -right-6 bottom-12 hidden lg:flex flex-col gap-3">
              {["3 Doctors", "500+ Patients", "AI-Powered Notes"].map((stat, i) => (
                <div key={i} className="glass-panel px-5 py-3 rounded-xl font-semibold text-slate-800 shadow-sm whitespace-nowrap">
                  ✓ {stat}
                </div>
              ))}
            </div>
          </div>
          <div className="flex-1">
            <h2 className="text-3xl font-bold text-slate-900 mb-6">Expert Care. Next-Gen Tech.</h2>
            <p className="text-lg text-slate-600 mb-6">
              Our specialists focus on what matters most — you. We've automated the paperwork, scheduling, and billing so that our doctors have more time to spend on providing exceptional care.
            </p>
            <Link to="/register">
              <Button size="lg" className="bg-primary hover:bg-blue-800 text-white">
                Meet Our Team
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* CTA BANNER */}
      <section className="bg-slate-900 text-white py-16 relative overflow-hidden">
        <div className="absolute inset-0 bg-primary/20 backdrop-blur-3xl"></div>
        <div className="max-w-4xl mx-auto px-6 text-center relative z-10">
          <h2 className="text-3xl font-bold mb-6">Ready to book your appointment?</h2>
          <p className="text-slate-300 mb-8 text-lg">Join the thousands of patients who trust Trimurti Clinic.</p>
          <Link to="/register">
            <Button size="lg" className="bg-white text-slate-900 hover:bg-slate-100 font-bold px-8">
              Book Now
            </Button>
          </Link>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="bg-slate-900 text-slate-400 py-12 border-t border-slate-800">
        <div className="max-w-7xl mx-auto px-6 grid grid-cols-1 md:grid-cols-3 gap-8 mb-8">
          <div>
            <h3 className="font-hero text-2xl text-white mb-2">Trimurti Clinic</h3>
            <p className="text-sm">Modern Healthcare, Seamlessly Scheduled.</p>
          </div>
          <div className="flex flex-col gap-2 md:items-center">
            <Link to="/" className="hover:text-white transition-colors w-fit">Home</Link>
            <Link to="/login" className="hover:text-white transition-colors w-fit">Staff Login</Link>
            <Link to="/register" className="hover:text-white transition-colors w-fit">Book Appointment</Link>
            <Link to="#" className="hover:text-white transition-colors w-fit">Privacy Policy</Link>
          </div>
          <div className="md:text-right">
            <p className="text-sm mb-2">Powered by FastAPI & Gemini AI</p>
          </div>
        </div>
        <div className="max-w-7xl mx-auto px-6 pt-8 border-t border-slate-800 text-center text-sm text-slate-500">
          © {new Date().getFullYear()} Trimurti Clinic. All rights reserved.
        </div>
      </footer>

    </div>
  );
}
