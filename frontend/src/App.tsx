import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';

import Landing          from './pages/Landing';
import Login            from './pages/Login';
import Signup           from './pages/Signup';
import Problems         from './pages/Problems';
import ProblemDetail    from './pages/ProblemDetail';
import Submissions      from './pages/Submissions';
import SubmissionDetail from './pages/SubmissionDetail';
import Doubts           from './pages/Doubts';
import Notifications    from './pages/Notifications';
import ReviewQueue      from './pages/ReviewQueue';
import Plagiarism       from './pages/Plagiarism';
import Analytics        from './pages/Analytics';

// Guard: redirect to /login if not authenticated
function Protected({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? <>{children}</> : <Navigate to="/login" replace />;
}

function TeacherOnly({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'teacher' && user.role !== 'admin') return <Navigate to="/problems" replace />;
  return <>{children}</>;
}

function AppRoutes() {
  return (
    <Routes>
      {/* Public routes */}
      <Route path="/"                         element={<Landing />} />
      <Route path="/login"                    element={<Login />} />
      <Route path="/signup"                   element={<Signup />} />

      {/* Protected routes */}
      <Route path="/problems"                 element={<Protected><Problems /></Protected>} />
      <Route path="/problems/:id"             element={<Protected><ProblemDetail /></Protected>} />
      <Route path="/doubts"                   element={<Protected><Doubts /></Protected>} />
      <Route path="/submissions"              element={<Protected><Submissions /></Protected>} />
      <Route path="/submissions/:id"          element={<Protected><SubmissionDetail /></Protected>} />
      <Route path="/notifications"          element={<Protected><Notifications /></Protected>} />

      {/* Teacher-only routes */}
      <Route path="/reviews"                  element={<TeacherOnly><ReviewQueue /></TeacherOnly>} />

      <Route path="/plagiarism"               element={<TeacherOnly><Plagiarism /></TeacherOnly>} />
      <Route path="/analytics"                element={<TeacherOnly><Analytics /></TeacherOnly>} />

      {/* Fallback */}
      <Route path="*"                         element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
