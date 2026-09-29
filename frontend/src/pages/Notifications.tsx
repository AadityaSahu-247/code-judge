import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Bell, Loader2 } from 'lucide-react';
import AppNavbar from '../components/AppNavbar';
import { BackgroundImage } from '../components/BackgroundImage';

interface NotificationItem {
  id: number;
  user_id: number;
  type: string;
  message: string;
  related_doubt_id?: number;
  read: boolean;
  created_at: string;
}

export default function Notifications() {
  const [notifs, setNotifs] = useState<NotificationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = () => {
    fetch('/api/notifications', {
      headers: { Authorization: `Bearer ${localStorage.getItem('cm_token')}` },
    })
      .then(async res => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: res.statusText }));
          throw new Error(err?.detail ?? `HTTP ${res.status}`);
        }
        return res.json();
      })
      .then(data => setNotifs(Array.isArray(data) ? data : []))
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const markRead = async (n: NotificationItem) => {
    if (n.read) return;
    try {
      await fetch(`/api/notifications/${n.id}/read`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${localStorage.getItem('cm_token')}` },
      });
      load();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Error marking notification read');
    }
  };

  const unread = notifs.filter(n => !n.read).length;

  return (
    <div className="min-h-screen text-white relative" style={{ background: '#0a0a0a' }}>
      <BackgroundImage />
      <AppNavbar />

      <main className="relative z-10 px-5 sm:px-8 md:px-12 pt-28 pb-16 max-w-[1100px] mx-auto w-full">
        <div className="mb-10">
          <p className="inline-block mb-4 font-mono text-[11px] uppercase tracking-[0.20em] text-white px-4 py-1.5"
            style={{ background: 'rgba(255,255,255,0.15)', backdropFilter: 'blur(12px)', borderLeft: '2px solid #fff' }}>
            Alerts & Updates
          </p>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-normal leading-[1.05] tracking-tight text-white drop-shadow-lg">
            Notifications
          </h1>
          <p className="mt-3 text-sm sm:text-base text-white/75 drop-shadow-md">
            {unread} unread notification{unread === 1 ? '' : 's'}
          </p>
        </div>

        {error && <div className="rounded-2xl p-5 text-sm font-mono text-red-300 mb-6" style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.30)', backdropFilter: 'blur(12px)' }}>{error}</div>}

        {loading && (
          <div className="flex items-center justify-center py-24 gap-3 text-white/60 font-mono text-sm">
            <Loader2 size={20} className="animate-spin text-white" /><span>LOADING NOTIFICATIONS...</span>
          </div>
        )}

        {!loading && notifs.length === 0 && !error && (
          <div className="text-center py-20">
            <Bell size={48} className="mx-auto mb-4 text-white/20" />
            <p className="text-white/40 text-sm font-mono">No notifications yet.</p>
          </div>
        )}

        {!loading && notifs.length > 0 && (
          <div className="flex flex-col gap-3">
            {notifs.map(n => (
              <div
                key={n.id}
                onClick={() => markRead(n)}
                className="rounded-2xl p-5 cursor-pointer transition-all duration-200 flex items-center justify-between gap-4"
                style={{
                  background: n.read ? 'rgba(255,255,255,0.06)' : 'rgba(255,255,255,0.12)',
                  border: n.read ? '1px solid rgba(255,255,255,0.12)' : '1px solid rgba(255,255,255,0.30)',
                  backdropFilter: 'blur(12px)',
                }}
              >
                <div className="flex flex-col gap-1 min-w-0">
                  {n.related_doubt_id ? (
                    <Link to={`/doubts`} className="text-sm font-medium text-white hover:underline truncate">
                      {n.message}
                    </Link>
                  ) : (
                    <span className="text-sm font-medium text-white truncate">{n.message}</span>
                  )}
                  <span className="text-xs font-mono text-white/50">{new Date(n.created_at).toLocaleString()}</span>
                </div>
                {!n.read && (
                  <span className="rounded-full px-3 py-0.5 text-[10px] font-mono uppercase tracking-wider bg-yellow-500/20 text-yellow-300 border border-yellow-500/40 flex-shrink-0">
                    New
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
