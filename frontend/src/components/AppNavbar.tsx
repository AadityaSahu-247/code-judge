import { Link, NavLink, useNavigate } from 'react-router-dom';
import { Hexagon, LogOut, User } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

export default function AppNavbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const isTeacher = user?.role === 'teacher' || user?.role === 'admin';

  return (
    <nav
      className="fixed top-0 left-0 w-full z-50 px-5 sm:px-8 md:px-12 transition-all duration-300"
      style={{
        background: 'rgba(10,10,10,0.85)',
        backdropFilter: 'blur(16px)',
        WebkitBackdropFilter: 'blur(16px)',
        borderBottom: '1px solid rgba(255,255,255,0.15)',
      }}
    >
      <div className="max-w-[1440px] mx-auto flex items-center justify-between h-20">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2 text-white group">
          <Hexagon size={24} strokeWidth={1.5} className="text-white" />
          <span className="text-lg sm:text-xl font-medium tracking-tight lowercase text-white">
            codementor
          </span>
        </Link>

        {/* Center links — conditional based on role */}
        {user ? (
          <div className="hidden md:flex items-center gap-6 lg:gap-8">
            <NavLink
              to="/problems"
              className={({ isActive }) =>
                `text-sm transition-colors duration-300 ${
                  isActive ? 'text-white font-medium' : 'text-white/85 hover:text-white'
                }`
              }
            >
              Problems
            </NavLink>
            <NavLink
              to="/submissions"
              className={({ isActive }) =>
                `text-sm transition-colors duration-300 ${
                  isActive ? 'text-white font-medium' : 'text-white/85 hover:text-white'
                }`
              }
            >
              My Submissions
            </NavLink>
            <NavLink
              to="/doubts"
              className={({ isActive }) =>
                `text-sm transition-colors duration-300 ${
                  isActive ? 'text-white font-medium' : 'text-white/85 hover:text-white'
                }`
              }
            >
              Doubts
            </NavLink>
            <NavLink
              to="/notifications"
              className={({ isActive }) =>
                `text-sm transition-colors duration-300 ${
                  isActive ? 'text-white font-medium' : 'text-white/85 hover:text-white'
                }`
              }
            >
              Notifications
            </NavLink>

            {isTeacher && (
              <>
                <NavLink
                  to="/reviews"
                  className={({ isActive }) =>
                    `text-sm transition-colors duration-300 ${
                      isActive ? 'text-white font-medium' : 'text-white/85 hover:text-white'
                    }`
                  }
                >
                  Review queue
                </NavLink>
                <NavLink
                  to="/plagiarism"
                  className={({ isActive }) =>
                    `text-sm transition-colors duration-300 ${
                      isActive ? 'text-white font-medium' : 'text-white/85 hover:text-white'
                    }`
                  }
                >
                  Plagiarism
                </NavLink>
                <NavLink
                  to="/analytics"
                  className={({ isActive }) =>
                    `text-sm transition-colors duration-300 ${
                      isActive ? 'text-white font-medium' : 'text-white/85 hover:text-white'
                    }`
                  }
                >
                  Analytics
                </NavLink>
              </>
            )}
          </div>
        ) : (
          <div className="hidden md:flex items-center gap-8 lg:gap-10">
            <a href="#teachers" className="text-sm text-white/85 hover:text-white transition-colors duration-300">
              For Teachers
            </a>
            <a href="#contact" className="text-sm text-white/85 hover:text-white transition-colors duration-300">
              Contact
            </a>
          </div>
        )}

        {/* Right — auth controls */}
        <div className="flex items-center gap-4">
          {user ? (
            <>
              <div
                className="hidden sm:flex items-center gap-2 px-3.5 py-1.5 rounded-full"
                style={{
                  background: 'rgba(255,255,255,0.10)',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                  border: '1px solid rgba(255,255,255,0.15)',
                }}
              >
                <User size={14} className="text-white/70" />
                <span className="text-xs text-white/90 font-mono tracking-wide">
                  {user.full_name || user.email.split('@')[0]}
                  {isTeacher && <span className="ml-1.5 text-[10px] text-yellow-300 font-mono uppercase tracking-wider">(Teacher)</span>}
                </span>
              </div>
              <button
                onClick={handleLogout}
                className="flex items-center gap-1.5 px-4 py-2 rounded-full text-xs text-white/80 hover:text-white transition-all duration-300 cursor-pointer"
                style={{
                  background: 'rgba(255,255,255,0.10)',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                  border: '1px solid rgba(255,255,255,0.15)',
                }}
              >
                <LogOut size={14} />
                <span className="hidden sm:inline">Logout</span>
              </button>
            </>
          ) : (
            <>
              <Link
                to="/login"
                className="text-sm text-white/85 hover:text-white transition-colors duration-300 px-3 py-2"
              >
                Login
              </Link>
              <Link
                to="/signup"
                className="rounded-md px-4 py-2 text-xs sm:px-5 sm:text-sm text-white hover:bg-white/25 transition-all duration-300"
                style={{
                  background: 'rgba(255,255,255,0.15)',
                  backdropFilter: 'blur(12px)',
                  WebkitBackdropFilter: 'blur(12px)',
                  border: '1px solid rgba(255,255,255,0.20)',
                }}
              >
                Start Practicing Free
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
