import { useEffect, useState } from 'react';
import { Loader2, BarChart2 } from 'lucide-react';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

interface AnalyticsData {
  pending_reviews: number;
  generated_answers: number;
  approved_answers: number;
  rejected_answers: number;
  total_reviewed: number;
  approval_rate: number;
  reviews_by_action: Record<string, number>;
  top_reviewers: { name?: string; count: number }[];
}

export default function Analytics() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch('/api/analytics/reviews', {
      headers: { Authorization: `Bearer ${localStorage.getItem('cm_token')}` },
    })
      .then(res => res.json())
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const stats = data
    ? [
        ['Pending Reviews', data.pending_reviews],
        ['Generated Answers', data.generated_answers],
        ['Approved Answers', data.approved_answers],
        ['Rejected Answers', data.rejected_answers],
        ['Total Reviewed', data.total_reviewed],
        ['Approval Rate', data.total_reviewed ? `${(data.approval_rate * 100).toFixed(1)}%` : '—'],
      ]
    : [];

  return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />

      <main className="relative z-10 px-5 sm:px-8 md:px-12 pt-28 pb-16 max-w-[1200px] mx-auto w-full">
        <div className="mb-10">
          <p className="inline-block mb-4 font-mono text-[11px] uppercase tracking-[0.20em] text-white px-4 py-1.5"
            style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)', borderLeft: '2px solid #fff' }}>
            System Metrics
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-normal leading-[1.05] tracking-tight text-white drop-shadow-lg">
            Analytics
          </h1>
          <p className="mt-3 text-sm sm:text-base text-white/75 drop-shadow-md">
            Review performance statistics, AI answer approval rates, and teacher activities.
          </p>
        </div>

        {error && <div className="rounded-2xl p-5 text-sm font-mono text-red-300 mb-6" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)', backdropFilter: 'blur(12px)' }}>{error}</div>}

        {loading && (
          <div className="flex items-center justify-center py-24 gap-3 text-white/60 font-mono text-sm">
            <Loader2 size={20} className="animate-spin text-white" /><span>LOADING ANALYTICS...</span>
          </div>
        )}

        {data && (
          <div className="flex flex-col gap-8">
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              {stats.map(([label, val]) => (
                <div key={label as string} className="rounded-2xl p-5 text-center flex flex-col justify-center"
                  style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
                  <span className="text-3xl font-normal text-white drop-shadow">{val}</span>
                  <span className="text-[11px] font-mono text-white/60 uppercase tracking-wider mt-2">{label}</span>
                </div>
              ))}
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <div className="rounded-2xl p-6"
                style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
                <h3 className="text-lg font-medium text-white mb-4 flex items-center gap-2">
                  <BarChart2 size={18} /> Reviews by Action
                </h3>
                {Object.keys(data.reviews_by_action).length === 0 ? (
                  <p className="text-white/40 text-xs font-mono py-8 text-center">No actions recorded yet.</p>
                ) : (
                  <div className="flex flex-col gap-3">
                    {Object.entries(data.reviews_by_action).map(([act, cnt]) => (
                      <div key={act} className="flex justify-between items-center py-2 border-b border-white/10 text-sm">
                        <span className="font-mono text-xs uppercase text-white/70">{act}</span>
                        <span className="font-mono text-sm text-white font-bold">{cnt}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="rounded-2xl p-6"
                style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
                <h3 className="text-lg font-medium text-white mb-4">Top Reviewers</h3>
                {data.top_reviewers.length === 0 ? (
                  <p className="text-white/40 text-xs font-mono py-8 text-center">No reviewer activity yet.</p>
                ) : (
                  <div className="flex flex-col gap-3">
                    {data.top_reviewers.map((r, i) => (
                      <div key={i} className="flex justify-between items-center py-2 border-b border-white/10 text-sm">
                        <span className="text-white font-medium">{r.name || 'Teacher'}</span>
                        <span className="font-mono text-sm text-white/70">{r.count} reviews</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
