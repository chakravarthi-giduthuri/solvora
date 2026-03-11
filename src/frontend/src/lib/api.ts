import axios, { AxiosError, AxiosInstance } from 'axios';
import type {
  PaginatedProblems,
  ProblemDetail,
  TrendingTopic,
  Solution,
  AnalyticsSummary,
  DashboardAnalytics,
  Category,
  AuthResponse,
  UserResponse,
  Problem,
  ProblemsParams,
} from '@/types';

// ─── Axios Instance ────────────────────────────────────────────────────────────

const apiClient: AxiosInstance = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 15000,
});

// ─── Request Interceptor ──────────────────────────────────────────────────────

apiClient.interceptors.request.use(
  (config) => {
    // Token is injected by the setApiToken helper below
    // This keeps the interceptor free of direct Zustand imports
    // to avoid SSR hydration issues
    const token = getStoredToken();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error),
);

// ─── Response Interceptor ─────────────────────────────────────────────────────

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Clear stored token and redirect to login (browser only)
      if (typeof window !== 'undefined') {
        sessionStorage.removeItem('auth-storage');
        window.location.href = '/auth/login';
      }
    }
    return Promise.reject(error);
  },
);

// ─── Token Helper ─────────────────────────────────────────────────────────────

function getStoredToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    const raw = sessionStorage.getItem('auth-storage');
    if (!raw) return null;
    const parsed = JSON.parse(raw) as { state?: { token?: string } };
    return parsed?.state?.token ?? null;
  } catch {
    return null;
  }
}

export function setApiToken(token: string | null): void {
  if (token) {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete apiClient.defaults.headers.common['Authorization'];
  }
}

// ─── Problems ─────────────────────────────────────────────────────────────────

export async function getProblems(
  params: ProblemsParams = {},
): Promise<PaginatedProblems> {
  const cleanParams: Record<string, unknown> = {};

  if (params.platform) cleanParams.platform = params.platform;
  if (params.category) cleanParams.category = params.category;
  if (params.sentiment) cleanParams.sentiment = params.sentiment;
  if (params.date_from) cleanParams.date_from = params.date_from;
  if (params.date_to) cleanParams.date_to = params.date_to;
  if (params.has_solution !== undefined && params.has_solution !== null) {
    cleanParams.has_solution = params.has_solution;
  }
  if (params.search) cleanParams.search = params.search;
  if (params.page) cleanParams.page = params.page;
  if (params.per_page) cleanParams.per_page = params.per_page;
  if (params.sort_by) cleanParams.sort_by = params.sort_by;

  const response = await apiClient.get<PaginatedProblems>('/problems', {
    params: cleanParams,
  });
  return response.data;
}

export async function getProblem(id: string): Promise<ProblemDetail> {
  const response = await apiClient.get<ProblemDetail>(`/problems/${id}`);
  return response.data;
}

// ─── Trending ─────────────────────────────────────────────────────────────────

export async function getTrending(
  period: '24h' | '7d' | '30d' = '24h',
): Promise<TrendingTopic[]> {
  const response = await apiClient.get<TrendingTopic[]>('/trending', {
    params: { period },
  });
  return response.data;
}

// ─── Solutions ────────────────────────────────────────────────────────────────

export async function getSolutions(problemId: string): Promise<Solution[]> {
  const response = await apiClient.get<Solution[]>(
    `/problems/${problemId}/solutions`,
  );
  return response.data;
}

export async function generateSolutions(
  problemId: string,
  providers: string[],
): Promise<{ task_id: string }> {
  const response = await apiClient.post<{ task_id: string }>(
    `/problems/${problemId}/solutions/generate`,
    { providers },
  );
  return response.data;
}

export async function submitVote(
  solutionId: string,
  voteType: 1 | -1,
): Promise<void> {
  await apiClient.post(`/solutions/${solutionId}/vote`, { vote: voteType });
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export async function getAnalytics(): Promise<AnalyticsSummary> {
  const response = await apiClient.get<AnalyticsSummary>('/analytics/summary');
  return response.data;
}

// ─── Categories ───────────────────────────────────────────────────────────────

export async function getCategories(): Promise<Category[]> {
  const response = await apiClient.get<Category[]>('/categories');
  return response.data;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export async function login(
  email: string,
  password: string,
): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/auth/login', {
    email,
    password,
  });
  return response.data;
}

export async function signup(
  email: string,
  password: string,
  name: string,
): Promise<UserResponse> {
  const response = await apiClient.post<UserResponse>('/auth/signup', {
    email,
    password,
    name,
  });
  return response.data;
}

// ─── Bookmarks ────────────────────────────────────────────────────────────────

export async function addBookmark(problemId: string): Promise<void> {
  await apiClient.post('/bookmarks/', { problem_id: problemId });
}

export async function removeBookmark(problemId: string): Promise<void> {
  await apiClient.delete(`/bookmarks/${problemId}`);
}

export async function getBookmarks(): Promise<Problem[]> {
  const response = await apiClient.get<Problem[]>('/bookmarks');
  return response.data;
}

export async function trackProblemClick(problemId: string): Promise<void> {
  try {
    await apiClient.post(`/problems/${problemId}/click`);
  } catch {
    // Silently ignore click tracking failures
  }
}

export async function getDashboardAnalytics(): Promise<DashboardAnalytics> {
  const response = await apiClient.get<DashboardAnalytics>('/analytics/dashboard');
  return response.data;
}

export default apiClient;
