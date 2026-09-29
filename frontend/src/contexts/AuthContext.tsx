import { createContext, useContext, useEffect, useState } from 'react';
import { api, type AuthUser } from '../services/api';

interface AuthCtx {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (username: string, email: string, password: string) => Promise<void>;
  logout: () => void;
}

const Ctx = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(localStorage.getItem('cm_token'));
  const [loading, setLoading] = useState(true);

  // Restore session on mount
  useEffect(() => {
    if (!token) { setLoading(false); return; }
    api.auth.me()
      .then(setUser)
      .catch(() => { localStorage.removeItem('cm_token'); setToken(null); })
      .finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const res = await api.auth.login({ email, password });
    setToken(res.access_token);
    if (res.user) {
      setUser(res.user);
    } else {
      const me = await api.auth.me();
      setUser(me);
    }
  };

  const signup = async (username: string, email: string, password: string) => {
    await api.auth.signup({ full_name: username, email, password });
  };

  const logout = () => {
    localStorage.removeItem('cm_token');
    setToken(null);
    setUser(null);
  };

  return <Ctx.Provider value={{ user, token, loading, login, signup, logout }}>{children}</Ctx.Provider>;
}

export function useAuth() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useAuth must be inside AuthProvider');
  return ctx;
}
