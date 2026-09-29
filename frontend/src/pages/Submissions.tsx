import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronRight, Loader2 } from 'lucide-react';
import { api, type Submission } from '../services/api';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

const SC: Record<string, { bg: string; border: string; text: string }> = {
  Accepted:            { bg: 'rgba(34,197,94,0.15)',  border: 'rgba(34,197,94,0.35)',  text: '#4ade80' },
  accepted:            { bg: 'rgba(34,197,94,0.15)',  border: 'rgba(34,197,94,0.35)',  text: '#4ade80' },
  Pending:             { bg: 'rgba(234,179,8,0.15)',   border: 'rgba(234,179,8,0.35)',  text: '#facc15' },
  queued:              { bg: 'rgba(234,179,8,0.15)',   border: 'rgba(234,179,8,0.35)',  text: '#facc15' },
  grading:             { bg: 'rgba(234,179,8,0.15)',   border: 'rgba(234,179,8,0.35)',  text: '#facc15' },
  'Wrong Answer':      { bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.35)',  text: '#f87171' },
  wrong_answer:        { bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.35)',  text: '#f87171' },
  time_limit_exceeded: { bg: 'rgba(251,146,60,0.15)', border: 'rgba(251,146,60,0.35)', text: '#fb923c' },
  TLE:                 { bg: 'rgba(251,146,60,0.15)',  border: 'rgba(251,146,60,0.35)', text: '#fb923c' },
  Error:               { bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.35)',  text: '#f87171' },
  runtime_error:       { bg: 'rgba(239,68,68,0.15)',   border: 'rgba(239,68,68,0.35)',  text: '#f87171' },
};

export default function Submissions() {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [error,   setError]   = useState('');

  useEffect(() => {
    api.submissions.list().then(setSubmissions).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, []);

  return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />

      <main className="relative z-10 px-5 sm:px-8 md:px-12 pt-28 pb-16 max-w-[1200px] mx-auto w-full">
        <div className="mb-10">
          <p className="inline-block mb-4 font-mono text-[11px] uppercase tracking-[0.20em] text-white px-4 py-1.5"
            style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)', borderLeft: '2px solid #fff' }}>
            History & Logs
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-normal leading-[1.05] tracking-tight text-white drop-shadow-lg">Submissions</h1>
          <p className="mt-3 text-sm sm:text-base text-white/75 drop-shadow-md max-w-xl">Review past execution logs, test results, and AI suggestions.</p>
        </div>

        {loading && <div className="flex items-center justify-center py-24 gap-3 text-white/60 font-mono text-sm"><Loader2 size={20} className="animate-spin text-white" /><span>LOADING SUBMISSIONS...</span></div>}
        {error   && <div className="rounded-2xl p-5 text-sm font-mono text-red-300 mb-6" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)', backdropFilter: 'blur(12px)' }}>{error}</div>}

        {!loading && !error && (
          <div className="rounded-2xl px-5 sm:px-6 py-3"
            style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
            <div className="grid grid-cols-[2fr_1fr_1fr_1fr_auto] gap-4 px-2 py-3 mb-2 font-mono text-[10px] uppercase tracking-[0.15em] text-white/50"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.12)' }}>
              {['Problem','Language','Status','Date',''].map(h => <span key={h}>{h}</span>)}
            </div>
            {submissions.length === 0 && (
              <p className="text-center py-16 text-white/40 text-sm font-mono">No submissions yet. <Link to="/problems" className="text-white underline">Try a problem</Link></p>
            )}
            {submissions.map((s, i, arr) => {
              const statusVal = s.verdict || s.status;
              const c = SC[statusVal] ?? SC.Error;
              return (
                <Link key={s.id} to={`/submissions/${s.id}`}
                  className="group grid grid-cols-[2fr_1fr_1fr_1fr_auto] gap-4 items-center py-4 px-2 transition-all duration-200"
                  style={i < arr.length-1 ? { borderBottom: '1px solid rgba(255,255,255,0.10)' } : {}}>
                  <span className="text-sm sm:text-base font-medium text-white truncate">Problem #{s.problem_id}</span>
                  <span className="font-mono text-xs text-white/65 uppercase">{s.language}</span>
                  <span className="rounded-full px-3 py-0.5 text-[11px] font-mono tracking-wider uppercase w-fit"
                    style={{ background: c.bg, border: `1px solid ${c.border}`, color: c.text }}>{statusVal}</span>
                  <span className="text-xs text-white/50 font-mono">{s.submitted_at ? new Date(s.submitted_at).toLocaleDateString() : (s.created_at ? new Date(s.created_at).toLocaleDateString() : '—')}</span>
                  <ChevronRight size={18} className="text-white/35 group-hover:text-white group-hover:translate-x-0.5 transition-all duration-300" />
                </Link>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}
