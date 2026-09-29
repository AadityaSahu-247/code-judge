import { useEffect, useState } from 'react';
import { Plus, Loader2, ChevronDown, ChevronUp, Trash2, MessageCircleQuestion, CheckCircle2, Clock, Sparkles } from 'lucide-react';
import { api, type Doubt, type AiAnswer } from '../services/api';
import { useAuth } from '../contexts/AuthContext';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

const BADGE: Record<string, { bg: string; border: string; text: string }> = {
  open:     { bg: 'rgba(234,179,8,0.15)',  border: 'rgba(234,179,8,0.35)',  text: '#facc15' },
  answered: { bg: 'rgba(34,197,94,0.15)', border: 'rgba(34,197,94,0.35)',  text: '#4ade80' },
};

function DoubtAnswerView({ doubtId }: { doubtId: number }) {
  const [answer, setAnswer] = useState<AiAnswer | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    api.doubts.getAnswer(doubtId)
      .then(ans => {
        if (!cancelled) setAnswer(ans);
      })
      .catch(err => {
        if (!cancelled) setError(err.message || 'Could not fetch answer');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [doubtId]);

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs font-mono text-white/50 pt-3">
        <Loader2 size={14} className="animate-spin text-white/70" />
        <span>Fetching answer...</span>
      </div>
    );
  }

  if (error || !answer) {
    return (
      <div className="rounded-xl p-4 bg-white/5 border border-white/10 text-xs font-mono text-white/50 pt-3">
        Answer is currently being prepared.
      </div>
    );
  }

  const isApproved = answer.status === 'approved';

  if (!isApproved && !answer.draft_content) {
    return (
      <div className="rounded-xl p-4 bg-yellow-500/10 border border-yellow-500/30 flex items-center gap-3 text-xs font-mono text-yellow-300">
        <Clock size={16} className="flex-shrink-0 text-yellow-400" />
        <span>An answer has been generated and is currently under teacher review. It will be published here once verified!</span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-3 pt-2">
      <div className="flex items-center gap-2">
        {isApproved ? (
          <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-mono tracking-wider uppercase bg-green-500/20 text-green-300 border border-green-500/40">
            <CheckCircle2 size={13} /> Verified Teacher Answer
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-[11px] font-mono tracking-wider uppercase bg-yellow-500/20 text-yellow-300 border border-yellow-500/40">
            <Sparkles size={13} /> Draft Answer (Pending Review)
          </span>
        )}
      </div>

      <div className="rounded-xl p-5 bg-black/40 border border-white/15 overflow-x-auto text-sm leading-relaxed text-white/90 whitespace-pre-wrap font-sans">
        {answer.draft_content}
      </div>
    </div>
  );
}

export default function Doubts() {
  const { user } = useAuth();
  const [doubts,     setDoubts]     = useState<Doubt[]>([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState('');
  const [open,       setOpen]       = useState<string | null>(null);
  const [creating,   setCreating]   = useState(false);
  const [formOpen,   setFormOpen]   = useState(false);
  const [form,       setForm]       = useState({ title: '', body: '' });

  useEffect(() => {
    api.doubts.list().then(setDoubts).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, []);

  const create = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      const d = await api.doubts.create({ title: form.title, description: form.body });
      setDoubts(prev => [d, ...prev]);
      setForm({ title: '', body: '' });
      setFormOpen(false);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to create doubt');
    } finally { setCreating(false); }
  };

  const remove = async (id: number) => {
    try {
      await api.doubts.delete(id);
      setDoubts(prev => prev.filter(d => d.id !== id));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to delete doubt');
    }
  };

  return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />

      <main className="relative z-10 px-5 sm:px-8 md:px-12 pt-28 pb-16 max-w-[1100px] mx-auto w-full">
        {/* Header */}
        <div className="mb-10 flex items-start justify-between gap-6 flex-wrap">
          <div>
            <p className="inline-block mb-4 font-mono text-[11px] uppercase tracking-[0.20em] text-white px-4 py-1.5"
              style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)', borderLeft: '2px solid #fff' }}>
              Ask Anything
            </p>
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-normal leading-[1.05] tracking-tight text-white drop-shadow-lg">Doubt Board</h1>
            <p className="mt-3 text-sm sm:text-base text-white/75 drop-shadow-md max-w-xl">Post a question, get answered by teachers and AI mentors.</p>
          </div>
          {user && (
            <button onClick={() => setFormOpen(v => !v)}
              className="flex items-center gap-2 rounded-full px-5 py-2.5 text-sm font-medium text-black bg-white hover:bg-white/85 transition-all duration-300 mt-8">
              <Plus size={16} /> New Doubt
            </button>
          )}
        </div>

        {error && <div className="rounded-2xl p-5 text-sm font-mono text-red-300 mb-6" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)', backdropFilter: 'blur(12px)' }}>{error}</div>}

        {/* Create form */}
        {formOpen && (
          <form onSubmit={create} className="rounded-2xl p-6 mb-8 flex flex-col gap-5"
            style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
            <p className="inline-block font-mono text-[11px] uppercase tracking-[0.20em] text-white px-3 py-1"
              style={{ background: 'rgba(255,255,255,0.15)', borderLeft: '2px solid #fff', width: 'fit-content' }}>New Doubt</p>
            <div className="flex flex-col gap-2">
              <label className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/60">Title</label>
              <input type="text" value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} placeholder="What's your question about?" required
                className="rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 outline-none transition-all"
                style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.18)' }}
                onFocus={e => (e.target.style.borderColor = 'rgba(255,255,255,0.50)')}
                onBlur={e  => (e.target.style.borderColor = 'rgba(255,255,255,0.18)')} />
            </div>
            <div className="flex flex-col gap-2">
              <label className="font-mono text-[11px] uppercase tracking-[0.18em] text-white/60">Description</label>
              <textarea value={form.body} onChange={e => setForm(f => ({ ...f, body: e.target.value }))} rows={4} placeholder="Describe your doubt in detail..." required
                className="rounded-xl px-4 py-3 text-sm text-white placeholder-white/30 outline-none resize-none transition-all"
                style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.18)' }}
                onFocus={e => (e.target.style.borderColor = 'rgba(255,255,255,0.50)')}
                onBlur={e  => (e.target.style.borderColor = 'rgba(255,255,255,0.18)')} />
            </div>
            <div className="flex gap-3 justify-end">
              <button type="button" onClick={() => setFormOpen(false)}
                className="rounded-full px-5 py-2 text-sm text-white/70 transition-all hover:text-white"
                style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)' }}>Cancel</button>
              <button type="submit" disabled={creating}
                className="flex items-center gap-2 rounded-full px-6 py-2 text-sm font-medium text-black bg-white hover:bg-white/85 transition-all disabled:opacity-50">
                {creating && <Loader2 size={14} className="animate-spin" />} Post
              </button>
            </div>
          </form>
        )}

        {loading && <div className="flex items-center justify-center py-24 gap-3 text-white/60 font-mono text-sm"><Loader2 size={20} className="animate-spin text-white" /><span>LOADING DOUBTS...</span></div>}

        {!loading && doubts.length === 0 && !error && (
          <div className="text-center py-20">
            <MessageCircleQuestion size={48} className="mx-auto mb-4 text-white/20" />
            <p className="text-white/40 text-sm font-mono">No doubts yet. Be the first to post!</p>
          </div>
        )}

        {!loading && doubts.length > 0 && (
          <div className="flex flex-col gap-4">
            {doubts.map(d => {
              const statusKey = d.status || 'open';
              const bc = BADGE[statusKey] ?? BADGE.open;
              const isOpen = open === d.id.toString();
              return (
                <div key={d.id} className="rounded-2xl overflow-hidden transition-all duration-300"
                  style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
                  <button className="w-full flex items-start gap-4 px-6 py-5 text-left" onClick={() => setOpen(isOpen ? null : d.id.toString())}>
                    <div className="flex-1 min-w-0">
                      <div className="flex flex-wrap items-center gap-3 mb-1.5">
                        <span className="text-base sm:text-lg font-medium text-white truncate">{d.title}</span>
                        <span className="rounded-full px-3 py-0.5 text-[10px] font-mono uppercase tracking-wider flex-shrink-0"
                          style={{ background: bc.bg, border: `1px solid ${bc.border}`, color: bc.text }}>{statusKey}</span>
                      </div>
                      <p className="text-xs font-mono text-white/50">
                        {d.student_name ? `by ${d.student_name} · ` : ''}{d.created_at ? new Date(d.created_at).toLocaleDateString() : ''}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 flex-shrink-0 mt-0.5">
                      {user && (user.id === d.student_id || user.role === 'teacher' || user.role === 'admin') && (
                        <span onClick={e => { e.stopPropagation(); remove(d.id); }}
                          className="rounded-full p-1.5 text-white/40 hover:text-red-400 transition-colors cursor-pointer"
                          style={{ background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.12)' }}>
                          <Trash2 size={14} />
                        </span>
                      )}
                      {isOpen ? <ChevronUp size={18} className="text-white/60" /> : <ChevronDown size={18} className="text-white/60" />}
                    </div>
                  </button>
                  {isOpen && (
                    <div className="px-6 pb-6 flex flex-col gap-5" style={{ borderTop: '1px solid rgba(255,255,255,0.12)' }}>
                      <p className="pt-4 text-sm text-white/80 leading-relaxed whitespace-pre-wrap">{d.description || (d as unknown as { body: string }).body}</p>
                      <DoubtAnswerView doubtId={d.id} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </main>
    </div>
  );
}

