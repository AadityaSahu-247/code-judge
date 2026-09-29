import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ChevronLeft, Play, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import { api, type Problem, type Testcase, type Submission } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

const LANGUAGES = ['python', 'javascript'];

export default function ProblemDetail() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();

  const [problem,    setProblem]    = useState<Problem | null>(null);
  const [testcases,  setTestcases]  = useState<Testcase[]>([]);
  const [code,       setCode]       = useState('');
  const [lang,       setLang]       = useState('python');
  const [loading,    setLoading]    = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [error,      setError]      = useState('');

  useEffect(() => {
    if (!id) return;
    Promise.all([api.problems.get(id), api.problems.testcases(id)])
      .then(([p, tc]) => { setProblem(p); setTestcases(tc); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const submit = async () => {
    if (!user) { navigate('/login'); return; }
    if (!id || !code.trim()) return;
    setSubmitting(true); setSubmission(null);
    try {
      const res = await api.submissions.create({ problem_id: Number(id), source_code: code, language: lang });
      setSubmission(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Submission failed');
    } finally { setSubmitting(false); }
  };

  const statusStyle = (s: string) => {
    if (s === 'accepted' || s === 'Accepted') return { color: '#4ade80', background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.35)' };
    if (s === 'queued' || s === 'grading' || s === 'Pending')  return { color: '#facc15', background: 'rgba(234,179,8,0.15)',  border: '1px solid rgba(234,179,8,0.35)'  };
    return                       { color: '#f87171', background: 'rgba(239,68,68,0.15)',  border: '1px solid rgba(239,68,68,0.35)'  };
  };

  if (loading) return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />
      <div className="relative z-10 flex-1 min-h-screen flex items-center justify-center gap-3 font-mono text-sm text-white/60">
        <Loader2 size={20} className="animate-spin text-white" /><span>LOADING PROBLEM...</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />

      <main className="relative z-10 pt-20 flex flex-col lg:flex-row" style={{ height: '100vh', overflow: 'hidden' }}>
        {/* Left panel */}
        <div className="lg:w-[45%] flex-shrink-0 overflow-y-auto px-6 sm:px-8 py-6 flex flex-col gap-6"
          style={{ borderRight: '1px solid rgba(255,255,255,0.15)', background: 'rgba(10,10,10,0.40)', backdropFilter: 'blur(8px)' }}>
          <Link to="/problems" className="inline-flex items-center gap-1.5 font-mono text-xs text-white/50 hover:text-white transition-colors">
            <ChevronLeft size={14} /> / BACK TO PROBLEMS
          </Link>
          {error && <div className="rounded-2xl p-4 text-xs font-mono text-red-300" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)' }}>{error}</div>}
          {problem && (
            <>
              <div>
                <div className="flex flex-wrap items-center gap-3 mb-3">
                  <h1 className="text-2xl sm:text-3xl font-normal tracking-tight text-white">{problem.title}</h1>
                  <span className="rounded-full px-3 py-0.5 text-[11px] font-mono uppercase tracking-wider"
                    style={{ background: problem.difficulty.toLowerCase()==='easy' ? 'rgba(34,197,94,0.15)' : problem.difficulty.toLowerCase()==='medium' ? 'rgba(234,179,8,0.15)' : 'rgba(239,68,68,0.15)', border: `1px solid ${problem.difficulty.toLowerCase()==='easy' ? 'rgba(34,197,94,0.35)' : problem.difficulty.toLowerCase()==='medium' ? 'rgba(234,179,8,0.35)' : 'rgba(239,68,68,0.35)'}`, color: problem.difficulty.toLowerCase()==='easy' ? '#4ade80' : problem.difficulty.toLowerCase()==='medium' ? '#facc15' : '#f87171' }}>
                    {problem.difficulty}
                  </span>
                </div>
                <p className="text-sm text-white/80 leading-relaxed whitespace-pre-wrap">{problem.statement || problem.description}</p>
              </div>
              {testcases.length > 0 && (
                <div>
                  <p className="inline-block mb-3 font-mono text-[11px] uppercase tracking-[0.18em] text-white px-3 py-1"
                    style={{ background: 'rgba(255,255,255,0.15)', borderLeft: '2px solid #fff' }}>Examples</p>
                  <div className="flex flex-col gap-3">
                    {testcases.slice(0,3).map((tc, i) => (
                      <div key={tc.id} className="rounded-2xl p-4" style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)', backdropFilter: 'blur(8px)' }}>
                        <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-white/50 mb-2">Example {i+1}</p>
                        <p className="text-xs font-mono text-white/85"><span className="text-white/45">Input: </span>{tc.input}</p>
                        <p className="text-xs font-mono text-white/85"><span className="text-white/45">Output: </span>{tc.expected_output}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Right panel: editor */}
        <div className="flex-1 flex flex-col min-h-0" style={{ background: 'rgba(10,10,10,0.50)', backdropFilter: 'blur(8px)' }}>
          <div className="flex items-center justify-between px-6 py-3.5 flex-shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.05)' }}>
            <div className="flex items-center gap-3">
              <label className="font-mono text-[11px] uppercase tracking-[0.15em] text-white/55">Language</label>
              <select value={lang} onChange={e => setLang(e.target.value)}
                className="rounded-xl px-3.5 py-1.5 text-xs font-mono uppercase text-white outline-none cursor-pointer"
                style={{ background: 'rgba(255,255,255,0.10)', border: '1px solid rgba(255,255,255,0.20)', backdropFilter: 'blur(12px)' }}>
                {LANGUAGES.map(l => <option key={l} value={l} className="bg-[#0a0a0a] text-white">{l}</option>)}
              </select>
            </div>
            <button onClick={submit} disabled={submitting || !code.trim()}
              className="flex items-center gap-2 rounded-full px-5 py-2 text-xs sm:text-sm font-medium text-black bg-white hover:bg-white/85 transition-all duration-300 disabled:opacity-40">
              {submitting ? <><Loader2 size={14} className="animate-spin" /> Submitting…</> : <><Play size={14} /> Submit</>}
            </button>
          </div>

          <textarea value={code} onChange={e => setCode(e.target.value)}
            placeholder={`// Write your ${lang} solution here...`} spellCheck={false}
            className="flex-1 resize-none px-6 py-5 text-sm font-mono text-white/90 leading-relaxed outline-none placeholder-white/25"
            style={{ background: 'transparent', tabSize: 2 }}
            onKeyDown={e => {
              if (e.key === 'Tab') {
                e.preventDefault();
                const s = e.currentTarget.selectionStart;
                const nv = code.slice(0,s) + '  ' + code.slice(e.currentTarget.selectionEnd);
                setCode(nv);
                requestAnimationFrame(() => { e.currentTarget.selectionStart = e.currentTarget.selectionEnd = s+2; });
              }
            }} />

          {submission && (
            <div className="flex-shrink-0 px-6 py-4 flex items-center justify-between"
              style={{ borderTop: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.06)', backdropFilter: 'blur(12px)' }}>
              <div className="flex items-center gap-3">
                {submission.status === 'Accepted' ? <CheckCircle2 size={18} className="text-green-400" /> : <XCircle size={18} className="text-red-400" />}
                <span className="rounded-full px-3 py-1 text-xs font-mono uppercase tracking-wider" style={statusStyle(submission.status)}>{submission.status}</span>
              </div>
              <Link to={`/submissions/${submission.id}`} className="text-xs font-mono text-white/60 hover:text-white transition-colors flex items-center gap-1">
                VIEW FULL REPORT <ChevronLeft size={14} className="rotate-180" />
              </Link>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}
