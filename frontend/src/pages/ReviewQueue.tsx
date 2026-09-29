import { useEffect, useState } from 'react';
import { Loader2, CheckCircle, Edit, XCircle, UserCheck } from 'lucide-react';
import { api, type ReviewAnswer } from '../services/api';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

export default function ReviewQueue() {
  const [answers, setAnswers] = useState<ReviewAnswer[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionId, setActionId] = useState<number | null>(null);
  const [action, setAction] = useState<'approve' | 'edit' | 'reject' | ''>('');
  const [note, setNote] = useState('');
  const [editedContent, setEditedContent] = useState('');

  const load = () => {
    api.reviews.answers()
      .then(setAnswers)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const startAction = (a: ReviewAnswer, kind: 'approve' | 'edit' | 'reject') => {
    setActionId(a.id);
    setAction(kind);
    setNote('');
    setEditedContent(a.draft_content || '');
  };

  const cancelAction = () => {
    setActionId(null);
    setAction('');
  };

  const submitAction = async () => {
    if (!actionId) return;
    setError('');
    try {
      if (action === 'approve') {
        await api.reviews.approve(actionId, note);
      } else if (action === 'edit') {
        await api.reviews.edit(actionId, editedContent, note);
      } else if (action === 'reject') {
        await api.reviews.reject(actionId, note);
      }
      cancelAction();
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Action failed');
    }
  };

  const claim = async (id: number) => {
    try {
      await api.reviews.claim(id);
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Claim failed');
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
            Teacher Desk
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-normal leading-[1.05] tracking-tight text-white drop-shadow-lg">
            Review Queue
          </h1>
          <p className="mt-3 text-sm sm:text-base text-white/75 drop-shadow-md">
            AI-generated answers awaiting teacher verification before being released to students.
          </p>
        </div>

        {error && <div className="rounded-2xl p-5 text-sm font-mono text-red-300 mb-6" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)', backdropFilter: 'blur(12px)' }}>{error}</div>}

        {loading && (
          <div className="flex items-center justify-center py-24 gap-3 text-white/60 font-mono text-sm">
            <Loader2 size={20} className="animate-spin text-white" /><span>LOADING REVIEW QUEUE...</span>
          </div>
        )}

        {!loading && answers.length === 0 && !error && (
          <div className="text-center py-20">
            <CheckCircle size={48} className="mx-auto mb-4 text-green-400/40" />
            <p className="text-white/50 text-sm font-mono">Review queue is empty. All drafts are up to date!</p>
          </div>
        )}

        {!loading && answers.length > 0 && (
          <div className="flex flex-col gap-6">
            {answers.map(a => (
              <div key={a.id} className="rounded-2xl p-6 flex flex-col gap-4"
                style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <h3 className="text-lg font-medium text-white">{a.doubt_title}</h3>
                  <span className="rounded-full px-3 py-0.5 text-[10px] font-mono uppercase tracking-wider bg-yellow-500/20 text-yellow-300 border border-yellow-500/40">
                    {a.status}
                  </span>
                </div>

                <p className="text-xs font-mono text-white/50">
                  Student: {a.student_name || 'Anonymous'} · Model: {a.model_version || 'standard'}
                  {a.claimed_by_name ? ` · Claimed by ${a.claimed_by_name}` : ' · Unclaimed'}
                </p>

                {a.moderation_flagged && (
                  <div className="rounded-xl px-4 py-2.5 text-xs font-mono text-red-300 bg-red-500/20 border border-red-500/40">
                    Moderation Flagged: {a.moderation_reason || 'Safety filter triggered'}
                  </div>
                )}

                <div className="rounded-xl p-4 bg-black/40 border border-white/15 max-h-72 overflow-y-auto">
                  <pre className="text-xs font-mono text-white/85 whitespace-pre-wrap leading-relaxed">
                    {a.draft_content || '(Empty draft)'}
                  </pre>
                </div>

                {actionId !== a.id && (
                  <div className="flex flex-wrap items-center gap-3 pt-2">
                    {!a.claimed_by_name && (
                      <button onClick={() => claim(a.id)} className="flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium bg-white/10 hover:bg-white/20 border border-white/20 text-white transition-all">
                        <UserCheck size={14} /> Claim
                      </button>
                    )}
                    <button onClick={() => startAction(a, 'approve')} className="flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium bg-green-500/20 hover:bg-green-500/30 border border-green-500/40 text-green-300 transition-all">
                      <CheckCircle size={14} /> Approve
                    </button>
                    <button onClick={() => startAction(a, 'edit')} className="flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/40 text-blue-300 transition-all">
                      <Edit size={14} /> Edit & Approve
                    </button>
                    <button onClick={() => startAction(a, 'reject')} className="flex items-center gap-1.5 rounded-full px-4 py-2 text-xs font-medium bg-red-500/20 hover:bg-red-500/30 border border-red-500/40 text-red-300 transition-all">
                      <XCircle size={14} /> Reject
                    </button>
                  </div>
                )}

                {actionId === a.id && (
                  <div className="rounded-xl p-5 bg-white/5 border border-white/20 flex flex-col gap-4 mt-2">
                    <h4 className="text-sm font-medium text-white capitalize">{action} Answer</h4>
                    {action === 'edit' && (
                      <textarea
                        value={editedContent}
                        onChange={e => setEditedContent(e.target.value)}
                        rows={6}
                        className="rounded-xl p-3 text-xs font-mono bg-black/50 border border-white/20 text-white outline-none"
                      />
                    )}
                    <input
                      type="text"
                      value={note}
                      onChange={e => setNote(e.target.value)}
                      placeholder="Note / Feedback reason (optional for approve/edit)..."
                      className="rounded-xl p-3 text-xs font-mono bg-black/50 border border-white/20 text-white outline-none"
                    />
                    <div className="flex gap-3 justify-end">
                      <button onClick={cancelAction} className="rounded-full px-4 py-1.5 text-xs text-white/60 hover:text-white">Cancel</button>
                      <button onClick={submitAction} className="rounded-full px-5 py-1.5 text-xs font-medium bg-white text-black hover:bg-white/85">Confirm</button>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
