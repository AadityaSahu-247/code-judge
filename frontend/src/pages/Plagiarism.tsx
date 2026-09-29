import { useEffect, useState } from 'react';
import { Loader2, Search, AlertTriangle } from 'lucide-react';
import { api, type Problem } from '../services/api';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

interface PlagiarismPair {
  submission_a_id: number;
  submission_b_id: number;
  student_a_name?: string;
  student_b_name?: string;
  verdict_a?: string;
  verdict_b?: string;
  score_a?: number;
  score_b?: number;
  similarity: number;
}

interface PlagiarismReport {
  problem_id: number;
  threshold: number;
  pairs: PlagiarismPair[];
}

export default function Plagiarism() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [problemId, setProblemId] = useState('');
  const [threshold, setThreshold] = useState('0.6');
  const [report, setReport] = useState<PlagiarismReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    api.problems.list().then(setProblems).catch(e => setError(e.message));
  }, []);

  const runScan = async () => {
    if (!problemId) { setError('Select a problem first'); return; }
    setError('');
    setLoading(true);
    setReport(null);
    try {
      const res = await fetch(`/api/problems/${problemId}/plagiarism?threshold=${encodeURIComponent(threshold)}`, {
        headers: { Authorization: `Bearer ${localStorage.getItem('cm_token')}` },
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || 'Scan failed');
      }
      setReport(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Plagiarism check failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />

      <main className="relative z-10 px-5 sm:px-8 md:px-12 pt-28 pb-16 max-w-[1200px] mx-auto w-full">
        <div className="mb-10">
          <p className="inline-block mb-4 font-mono text-[11px] uppercase tracking-[0.20em] text-white px-4 py-1.5"
            style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)', borderLeft: '2px solid #fff' }}>
            Academic Integrity
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-normal leading-[1.05] tracking-tight text-white drop-shadow-lg">
            Plagiarism Detection
          </h1>
          <p className="mt-3 text-sm sm:text-base text-white/75 drop-shadow-md">
            Scan student code submissions for token-sequence similarity and potential copying.
          </p>
        </div>

        {error && <div className="rounded-2xl p-5 text-sm font-mono text-red-300 mb-6" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)', backdropFilter: 'blur(12px)' }}>{error}</div>}

        <div className="rounded-2xl p-6 mb-8 flex flex-wrap items-center gap-4"
          style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
          <select
            value={problemId}
            onChange={e => setProblemId(e.target.value)}
            className="rounded-xl px-4 py-3 text-sm bg-black/50 border border-white/20 text-white outline-none flex-1 min-w-[200px]"
          >
            <option value="">Select a Problem...</option>
            {problems.map(p => (
              <option key={p.id} value={p.id} className="bg-black text-white">#{p.id} — {p.title}</option>
            ))}
          </select>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-white/60 uppercase">Threshold:</span>
            <input
              type="number"
              step="0.05"
              min="0"
              max="1"
              value={threshold}
              onChange={e => setThreshold(e.target.value)}
              className="rounded-xl px-3 py-3 text-sm font-mono w-24 bg-black/50 border border-white/20 text-white outline-none"
            />
          </div>

          <button
            onClick={runScan}
            disabled={loading}
            className="flex items-center gap-2 rounded-full px-6 py-3 text-sm font-medium bg-white text-black hover:bg-white/85 transition-all disabled:opacity-50"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Search size={16} />}
            {loading ? 'Scanning…' : 'Run Scan'}
          </button>
        </div>

        {report && (
          <div className="rounded-2xl p-6"
            style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-medium text-white">Scan Results</h3>
              <span className="rounded-full px-3 py-1 text-xs font-mono bg-white/10 border border-white/20 text-white">
                Threshold: {(report.threshold * 100).toFixed(0)}%
              </span>
            </div>

            {report.pairs.length === 0 ? (
              <p className="text-center py-12 text-white/40 text-sm font-mono">No matching duplicate pairs found above threshold.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b border-white/15 text-xs font-mono text-white/50 uppercase">
                      <th className="py-3 px-4">Similarity</th>
                      <th className="py-3 px-4">Student A</th>
                      <th className="py-3 px-4">Student B</th>
                      <th className="py-3 px-4">Verdicts</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.pairs.map((p, i) => (
                      <tr key={i} className="border-b border-white/10 hover:bg-white/5 transition-colors text-sm">
                        <td className="py-4 px-4 font-mono font-bold text-red-400">
                          <span className="inline-flex items-center gap-1">
                            <AlertTriangle size={14} /> {(p.similarity * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="py-4 px-4 text-white">
                          {p.student_a_name || 'Student A'} <span className="text-xs text-white/50 font-mono">(#{p.submission_a_id})</span>
                        </td>
                        <td className="py-4 px-4 text-white">
                          {p.student_b_name || 'Student B'} <span className="text-xs text-white/50 font-mono">(#{p.submission_b_id})</span>
                        </td>
                        <td className="py-4 px-4 font-mono text-xs text-white/70">
                          {p.verdict_a || '—'} / {p.verdict_b || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
