import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ChevronLeft, Loader2, Bot, CheckCircle2, XCircle } from 'lucide-react';
import { api, type Submission, type SubmissionResult, type AiFeedback } from '../services/api';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

export default function SubmissionDetail() {
  const { id } = useParams<{ id: string }>();
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [results,    setResults]    = useState<SubmissionResult[]>([]);
  const [feedback,   setFeedback]   = useState<AiFeedback | null>(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState('');

  useEffect(() => {
    if (!id) return;
    Promise.all([
      api.submissions.get(id),
      api.submissions.results(id).catch(() => []),
      api.submissions.aiFeedback(id).catch(() => null),
    ]).then(([s, r, f]) => { setSubmission(s); setResults((Array.isArray(r) ? r : (r as any).results || []) as any); setFeedback(f); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const sStatus = submission?.verdict || submission?.status;
  const statusStyle = (sStatus === 'accepted' || sStatus === 'Accepted')
    ? { color: '#4ade80', background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.35)' }
    : (sStatus === 'queued' || sStatus === 'grading' || sStatus === 'Pending')
    ? { color: '#facc15', background: 'rgba(234,179,8,0.15)',  border: '1px solid rgba(234,179,8,0.35)'  }
    : { color: '#f87171', background: 'rgba(239,68,68,0.15)',  border: '1px solid rgba(239,68,68,0.35)'  };

  if (loading) return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />
      <div className="relative z-10 min-h-screen flex items-center justify-center gap-3 font-mono text-sm text-white/60">
        <Loader2 size={20} className="animate-spin text-white" /><span>LOADING SUBMISSION...</span>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />

      <main className="relative z-10 px-5 sm:px-8 md:px-12 pt-28 pb-16 max-w-[1100px] mx-auto w-full flex flex-col gap-6">
        <Link to="/submissions" className="inline-flex items-center gap-1.5 font-mono text-xs text-white/50 hover:text-white transition-colors">
          <ChevronLeft size={14} /> / BACK TO SUBMISSIONS
        </Link>

        {error && <div className="rounded-2xl p-4 text-xs font-mono text-red-300" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)' }}>{error}</div>}

        {submission && (
          <>
            {/* Header card */}
            <div className="rounded-2xl p-6" style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="inline-block mb-2 font-mono text-[11px] uppercase tracking-[0.20em] text-white px-3 py-1"
                    style={{ background: 'rgba(255,255,255,0.15)', borderLeft: '2px solid #fff' }}>Submission Report</p>
                  <h1 className="text-2xl sm:text-3xl font-normal tracking-tight text-white">Problem #{submission.problem_id}</h1>
                </div>
                <span className="rounded-full px-4 py-1.5 text-sm font-mono uppercase tracking-wider" style={statusStyle}>{sStatus}</span>
              </div>
              <div className="mt-5 flex flex-wrap gap-4 font-mono text-xs text-white/55">
                <span>Language: <strong className="text-white">{submission.language}</strong></span>
                {(submission.submitted_at || (submission as any).created_at) && <span>Submitted: <strong className="text-white">{new Date(submission.submitted_at || (submission as any).created_at).toLocaleString()}</strong></span>}
              </div>
            </div>

            {/* Code */}
            <div className="rounded-2xl overflow-hidden" style={{ background: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
              <div className="px-5 py-3 flex items-center justify-between" style={{ borderBottom: '1px solid rgba(255,255,255,0.15)', background: 'rgba(255,255,255,0.05)' }}>
                <p className="font-mono text-[11px] uppercase tracking-[0.15em] text-white/60">Source Code</p>
                <span className="rounded-full px-3 py-0.5 text-[10px] font-mono uppercase text-white/60"
                  style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)' }}>{submission.language}</span>
              </div>
              <pre className="px-6 py-5 overflow-x-auto text-xs sm:text-sm font-mono text-white/85 leading-relaxed whitespace-pre">{submission.source_code || (submission as any).code}</pre>
            </div>

            {/* Test cases */}
            {results.length > 0 && (
              <div>
                <p className="inline-block mb-4 font-mono text-[11px] uppercase tracking-[0.20em] text-white px-4 py-1.5"
                  style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)', borderLeft: '2px solid #fff' }}>
                  Test Cases — {results.filter(r => r.passed).length}/{results.length} passed
                </p>
                <div className="grid sm:grid-cols-2 gap-4">
                  {results.map((r: any, i) => (
                    <div key={r.id ?? i} className="rounded-2xl p-4" style={{ background: r.passed ? 'rgba(34,197,94,0.08)' : 'rgba(239,68,68,0.08)', border: r.passed ? '1px solid rgba(34,197,94,0.25)' : '1px solid rgba(239,68,68,0.25)', backdropFilter: 'blur(12px)' }}>
                      <div className="flex items-center gap-2 mb-3">
                        {r.passed ? <CheckCircle2 size={16} className="text-green-400" /> : <XCircle size={16} className="text-red-400" />}
                        <span className="font-mono text-[11px] uppercase tracking-[0.15em] text-white/70">Case {i+1} — {r.verdict}</span>
                      </div>
                      <div className="flex flex-col gap-1.5 font-mono text-[11px] text-white/70">
                        {r.exec_time_ms !== undefined && <p><span className="text-white/45">Execution Time: </span>{r.exec_time_ms} ms</p>}
                        {r.memory_kb !== undefined && <p><span className="text-white/45">Memory: </span>{r.memory_kb} KB</p>}
                        <p><span className={r.passed ? 'text-green-400' : 'text-red-400'}>Output: </span>{r.actual_output || r.actual || '—'}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Feedback */}
            {feedback && (
              <div className="rounded-2xl p-6" style={{ background: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
                <div className="flex items-center gap-3 mb-4">
                  <Bot size={20} className="text-white/70" />
                  <p className="font-mono text-[11px] uppercase tracking-[0.20em] text-white">AI Mentor Feedback</p>
                </div>
                {feedback.readability && (
                  <div className="mb-3">
                    <h4 className="text-xs font-mono uppercase text-white/60 mb-1">Readability</h4>
                    <p className="text-sm text-white/85 leading-relaxed">{feedback.readability}</p>
                  </div>
                )}
                {feedback.complexity && (
                  <div className="mb-3">
                    <h4 className="text-xs font-mono uppercase text-white/60 mb-1">Complexity</h4>
                    <p className="text-sm text-white/85 leading-relaxed">{feedback.complexity}</p>
                  </div>
                )}
                {feedback.best_practices && (
                  <div className="mb-3">
                    <h4 className="text-xs font-mono uppercase text-white/60 mb-1">Best Practices</h4>
                    <p className="text-sm text-white/85 leading-relaxed">{feedback.best_practices}</p>
                  </div>
                )}
                {feedback.optimization && (
                  <div className="mb-3">
                    <h4 className="text-xs font-mono uppercase text-white/60 mb-1">Optimization</h4>
                    <p className="text-sm text-white/85 leading-relaxed">{feedback.optimization}</p>
                  </div>
                )}
                {!(feedback.readability || feedback.complexity || feedback.best_practices || feedback.optimization) && (
                  <p className="text-sm text-white/85 leading-relaxed whitespace-pre-wrap">{(feedback as any).feedback || 'AI Feedback pending or unavailable.'}</p>
                )}
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
