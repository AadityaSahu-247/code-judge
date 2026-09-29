import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Loader2, Eye, EyeOff } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form.email, form.password);
      navigate('/problems');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />

      <div className="relative z-10 min-h-screen flex items-center justify-center px-5 pt-24 pb-12">
        <div className="w-full max-w-md">
          {/* Header */}
          <div className="mb-8 text-center">
            <p
              className="inline-block mb-4 font-mono text-[11px] uppercase tracking-[0.20em] text-white px-4 py-1.5"
              style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)', borderLeft: '2px solid #fff' }}
            >
              Authentication
            </p>
            <h1 className="text-4xl sm:text-5xl font-normal tracking-tight text-white drop-shadow-lg mb-3">
              Welcome back
            </h1>
            <p className="text-sm sm:text-base text-white/75 drop-shadow-md">
              Sign in to continue your practice and track your progress.
            </p>
          </div>

          {/* Glass card */}
          <form
            onSubmit={submit}
            className="rounded-2xl p-6 sm:p-8 flex flex-col gap-5"
            style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}
          >
            {error && (
              <div className="rounded-xl px-4 py-3 text-xs font-mono text-red-300"
                style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)' }}>
                {error}
              </div>
            )}
            <Field label="Email" type="email" value={form.email} onChange={v => setForm(f => ({ ...f, email: v }))} placeholder="you@example.com" />
            <Field label="Password" type="password" value={form.password} onChange={v => setForm(f => ({ ...f, password: v }))} placeholder="••••••••" />
            <button type="submit" disabled={loading}
              className="mt-2 w-full flex items-center justify-center gap-2 rounded-full bg-white text-black text-sm font-medium py-3 hover:bg-white/85 transition-all duration-300 disabled:opacity-50">
              {loading && <Loader2 size={16} className="animate-spin" />}
              {loading ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-white/60">
            Don't have an account?{' '}
            <Link to="/signup" className="text-white font-medium hover:underline">Sign up free</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function Field({ label, type, value, onChange, placeholder }: {
  label: string; type: string; value: string; onChange: (v: string) => void; placeholder?: string;
}) {
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === 'password';
  const inputType = isPassword ? (showPassword ? 'text' : 'password') : type;

  return (
    <div className="flex flex-col gap-2">
      <label className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/60">{label}</label>
      <div className="relative">
        <input
          type={inputType}
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          required
          className="w-full rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 outline-none transition-all duration-200 pr-10"
          style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.18)' }}
          onFocus={e => (e.target.style.borderColor = 'rgba(255,255,255,0.50)')}
          onBlur={e  => (e.target.style.borderColor = 'rgba(255,255,255,0.18)')}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShowPassword(s => !s)}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-white/50 hover:text-white transition-colors cursor-pointer"
          >
            {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
          </button>
        )}
      </div>
    </div>
  );
}
