// ─────────────────────────────────────────────────────────────────
// API service — all backend calls connected to FastAPI backend
// Base URL via VITE_API_URL env var, defaults to empty string for Vite proxy
// ─────────────────────────────────────────────────────────────────
const BASE = import.meta.env.VITE_API_URL ?? '';

function token() {
  return localStorage.getItem('cm_token');
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  auth = true
): Promise<T> {
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (auth && token()) headers['Authorization'] = `Bearer ${token()}`;

  const res = await fetch(`${BASE}${path}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err?.detail ?? `HTTP ${res.status}`);
  }

  if (res.status === 204) return null as T;
  return res.json() as Promise<T>;
}

// ── Auth ─────────────────────────────────────────────────────────
export interface AuthUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type?: string;
  user?: AuthUser;
}

export const api = {
  auth: {
    signup: (data: { full_name: string; email: string; password: string }) =>
      request<AuthUser>('POST', '/api/auth/signup', {
        email: data.email,
        password: data.password,
        full_name: data.full_name,
        role: 'student',
      }, false),

    login: async (data: { email: string; password: string }): Promise<AuthResponse> => {
      const form = new URLSearchParams();
      form.append('username', data.email);
      form.append('password', data.password);

      const res = await fetch(`${BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err?.detail ?? `HTTP ${res.status}`);
      }

      const tokenData = (await res.json()) as { access_token: string; token_type: string };
      localStorage.setItem('cm_token', tokenData.access_token);
      
      // Fetch user profile using token
      const meRes = await fetch(`${BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${tokenData.access_token}` },
      });
      const user = meRes.ok ? ((await meRes.json()) as AuthUser) : { id: 1, email: data.email, full_name: data.email.split('@')[0], role: 'student' };

      return { access_token: tokenData.access_token, user };
    },

    me: () => request<AuthUser>('GET', '/api/auth/me'),
  },

  // ── Problems ──────────────────────────────────────────────────
  problems: {
    list: () => request<Problem[]>('GET', '/api/problems'),
    get: (id: string | number) => request<Problem>('GET', `/api/problems/${id}`),
    testcases: (id: string | number) => request<Testcase[]>('GET', `/api/problems/${id}/testcases`),
  },

  // ── Submissions ───────────────────────────────────────────────
  submissions: {
    create: (data: { problem_id: number; source_code: string; language: string }) =>
      request<Submission>('POST', '/api/submissions', data),
    list: () => request<Submission[]>('GET', '/api/submissions'),
    get: (id: string | number) => request<Submission>('GET', `/api/submissions/${id}`),
    results: (id: string | number) => request<SubmissionResult[]>('GET', `/api/submissions/${id}/results`),
    aiFeedback: (id: string | number) => request<AiFeedback>('GET', `/api/submissions/${id}/feedback`),
  },

  // ── Doubts ────────────────────────────────────────────────────
  doubts: {
    list: (query?: string, problemId?: number) => {
      const params = new URLSearchParams();
      if (query) params.set('q', query);
      if (problemId) params.set('problem_id', problemId.toString());
      const qs = params.toString();
      return request<Doubt[]>('GET', `/api/doubts${qs ? `?${qs}` : ''}`);
    },
    get: (id: string | number) => request<Doubt>('GET', `/api/doubts/${id}`),
    getAnswer: (id: string | number) => request<AiAnswer>('GET', `/api/doubts/${id}/answer`),
    create: (data: { title: string; description: string; code_snippet?: string; related_problem_id?: number }) =>
      request<Doubt>('POST', '/api/doubts', data),
    update: (id: string | number, data: Partial<{ title: string; description: string; code_snippet?: string; status: string }>) =>
      request<Doubt>('PATCH', `/api/doubts/${id}`, data),
    delete: (id: string | number) => request<void>('DELETE', `/api/doubts/${id}`),
    similar: (id: string | number) => request<SimilarDoubt[]>('GET', `/api/doubts/similar?doubt_id=${id}`),
  },

  // ── Review Queue ──────────────────────────────────────────────
  reviews: {
    answers: () => request<ReviewAnswer[]>('GET', '/api/reviews/answers'),
    approve: (id: string | number, note?: string) => request<void>('POST', `/api/reviews/${id}/approve`, { note: note || null }),
    edit: (id: string | number, edited_content: string, note?: string) => request<void>('POST', `/api/reviews/${id}/edit`, { edited_content, note: note || null }),
    reject: (id: string | number, note: string) => request<void>('POST', `/api/reviews/${id}/reject`, { note }),
    claim: (id: string | number) => request<void>('POST', `/api/reviews/${id}/claim`),
  },
};

// ── Types ─────────────────────────────────────────────────────────
export interface Problem {
  id: number;
  title: string;
  statement: string;
  description?: string;
  difficulty: 'Easy' | 'Medium' | 'Hard' | 'easy' | 'medium' | 'hard';
  time_limit_seconds?: number;
  memory_limit_mb?: number;
  created_at?: string;
  tags?: string[];
}

export interface Testcase {
  id: number;
  problem_id: number;
  input: string;
  expected_output: string;
  is_hidden: boolean;
}

export interface SubmissionResult {
  id: number;
  test_case_id: number;
  passed: boolean;
  verdict: string;
  actual_output?: string;
  exec_time_ms?: number;
  memory_kb?: number;
}

export interface Submission {
  id: number;
  student_id: number;
  problem_id: number;
  language: string;
  source_code: string;
  status: 'queued' | 'grading' | 'graded' | 'error' | string;
  verdict?: string;
  score?: number;
  submitted_at: string;
  created_at?: string;
  results?: SubmissionResult[];
}

export interface AiFeedback {
  id: number;
  submission_id: number;
  status: 'pending' | 'success' | 'failed' | string;
  readability?: string;
  complexity?: string;
  best_practices?: string;
  optimization?: string;
  raw_model_response?: string;
}

export interface Doubt {
  id: number;
  student_id: number;
  student_name?: string;
  title: string;
  description: string;
  code_snippet?: string;
  related_problem_id?: number;
  status: 'open' | 'answered' | 'resolved' | string;
  created_at: string;
}

export interface AiAnswer {
  id: number;
  doubt_id: number;
  status: 'pending_review' | 'approved' | 'rejected' | string;
  draft_content?: string;
  moderation_flagged: boolean;
  moderation_reason?: string;
  model_version?: string;
  generated_at?: string;
}

export interface SimilarDoubt {
  id: number;
  title: string;
  description: string;
  similarity: number;
}

export interface ReviewAnswer {
  id: number;
  doubt_id: number;
  doubt_title: string;
  student_name?: string;
  status: string;
  draft_content?: string;
  moderation_flagged: boolean;
  moderation_reason?: string;
  model_version?: string;
  generated_at?: string;
  claimed_by_id?: number;
  claimed_by_name?: string;
}
