import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, ChevronRight, Loader2 } from 'lucide-react';
import { api, type Problem } from '../services/api';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

const DIFF_BG:     Record<string, string> = { Easy: 'rgba(34,197,94,0.15)',  Medium: 'rgba(234,179,8,0.15)',  Hard: 'rgba(239,68,68,0.15)'  };
const DIFF_BORDER: Record<string, string> = { Easy: 'rgba(34,197,94,0.35)',  Medium: 'rgba(234,179,8,0.35)',  Hard: 'rgba(239,68,68,0.35)'  };
const DIFF_TEXT:   Record<string, string> = { Easy: '#4ade80',               Medium: '#facc15',               Hard: '#f87171'               };

export default function Problems() {
  const [problems, setProblems] = useState<Problem[]>([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState('');
  const [search,   setSearch]   = useState('');
  const [filter,   setFilter]   = useState<'All' | 'Easy' | 'Medium' | 'Hard'>('All');

  useEffect(() => {
    api.problems.list().then(setProblems).catch(e => setError(e.message)).finally(() => setLoading(false));
  }, []);

  const displayed = problems.filter(p =>
    p.title.toLowerCase().includes(search.toLowerCase()) &&
    (filter === 'All' || p.difficulty.toLowerCase() === filter.toLowerCase())
  );

  return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />

      <main className="relative z-10 px-5 sm:px-8 md:px-12 pt-28 pb-16 max-w-[1200px] mx-auto w-full">
        {/* Header */}
        <div className="mb-10">
          <p className="inline-block mb-4 font-mono text-[11px] uppercase tracking-[0.20em] text-white px-4 py-1.5"
            style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)', borderLeft: '2px solid #fff' }}>
            Practice Arena
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-normal leading-[1.05] tracking-tight text-white drop-shadow-lg">
            Problem Bank
          </h1>
          <p className="mt-3 text-sm sm:text-base text-white/75 drop-shadow-md max-w-xl">
            Select a problem to test your algorithms against hidden sandboxed test cases with AI mentor feedback.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-8">
          <div className="relative flex-1">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-white/40" />
            <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search problems..."
              className="w-full pl-11 pr-4 py-3 rounded-xl text-sm text-white placeholder-white/30 outline-none transition-all duration-200"
              style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.18)', backdropFilter: 'blur(12px)' }}
              onFocus={e => (e.target.style.borderColor = 'rgba(255,255,255,0.50)')}
              onBlur={e  => (e.target.style.borderColor = 'rgba(255,255,255,0.18)')} />
          </div>
          <div className="flex gap-2 flex-wrap">
            {(['All', 'Easy', 'Medium', 'Hard'] as const).map(d => (
              <button key={d} onClick={() => setFilter(d)}
                className="px-4 py-2.5 rounded-full text-xs font-mono uppercase tracking-[0.15em] transition-all duration-200"
                style={{ background: filter === d ? '#ffffff' : 'rgba(255,255,255,0.10)', color: filter === d ? '#000' : '#fff', border: filter === d ? '1px solid #fff' : '1px solid rgba(255,255,255,0.18)', backdropFilter: 'blur(12px)' }}>
                {d}
              </button>
            ))}
          </div>
        </div>

        {loading && <div className="flex items-center justify-center py-24 gap-3 text-white/60 font-mono text-sm"><Loader2 size={20} className="animate-spin text-white" /><span>LOADING PROBLEMS...</span></div>}
        {error   && <div className="rounded-2xl p-5 text-sm font-mono text-red-300 mb-6" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)', backdropFilter: 'blur(12px)' }}>{error}</div>}

        {!loading && (
          <div className="rounded-2xl px-5 sm:px-6 py-2"
            style={{ background: 'rgba(255,255,255,0.10)', backdropFilter: 'blur(16px)', WebkitBackdropFilter: 'blur(16px)', border: '1px solid rgba(255,255,255,0.18)' }}>
            {displayed.length === 0 && !error && (
              <p className="text-center py-16 text-white/40 text-sm font-mono">No problems match your query.</p>
            )}
            {displayed.map((p, i, arr) => (
              <Link key={p.id} to={`/problems/${p.id}`}
                className="group flex items-center justify-between gap-4 py-5 transition-all duration-200"
                style={i < arr.length - 1 ? { borderBottom: '1px solid rgba(255,255,255,0.12)' } : {}}>
                <div className="flex items-center gap-5 min-w-0">
                  <span className="font-mono text-[11px] tracking-[0.15em] text-white/50 flex-shrink-0 w-7">{(i+1).toString().padStart(2,'0')}</span>
                  <span className="text-base sm:text-lg font-medium text-white truncate">{p.title}</span>
                  {p.tags?.slice(0,2).map(tag => (
                    <span key={tag} className="hidden sm:inline-block rounded-md px-2.5 py-1 text-[10px] font-mono text-white/60 uppercase tracking-wider"
                      style={{ background: 'rgba(255,255,255,0.08)', border: '1px solid rgba(255,255,255,0.15)' }}>{tag}</span>
                  ))}
                </div>
                <div className="flex items-center gap-4 flex-shrink-0">
                  <span className="rounded-full px-3.5 py-1 text-[11px] font-mono tracking-wider uppercase"
                    style={{ background: DIFF_BG[p.difficulty], border: `1px solid ${DIFF_BORDER[p.difficulty]}`, color: DIFF_TEXT[p.difficulty] }}>
                    {p.difficulty}
                  </span>
                  <ChevronRight size={18} className="text-white/40 group-hover:text-white group-hover:translate-x-0.5 transition-all duration-300" />
                </div>
              </Link>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
