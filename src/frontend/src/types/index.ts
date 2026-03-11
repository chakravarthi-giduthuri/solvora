export type Platform = 'reddit' | 'hackernews';

export type Sentiment = 'urgent' | 'frustrated' | 'curious' | 'neutral';

export type AIProvider = 'gemini' | 'openai' | 'claude';

// ─── Core Entities ────────────────────────────────────────────────────────────

export interface Category {
  id: string;
  name: string;
  slug: string;
  color?: string;
  problemCount?: number;
}

export interface User {
  id: string;
  email: string;
  name: string;
  avatarUrl?: string;
  createdAt: string;
}

export interface UserResponse {
  id: string;
  email: string;
  name: string;
  avatarUrl?: string;
  createdAt: string;
}

export interface Problem {
  id: string;
  title: string;
  body: string;
  platform: Platform;
  sourceUrl: string;
  source_id?: string;
  author?: string;
  authorAvatarUrl?: string;
  category: Category | string | null;
  sentiment: Sentiment | null;
  upvotes: number;
  commentCount: number;
  hasSolution: boolean;
  solutionCount: number;
  isBookmarked?: boolean;
  createdAt: string;
  scrapedAt: string;
  subreddit?: string | null;
  summary?: string | null;
}

export interface ProblemDetail extends Problem {
  solutions: Solution[];
  relatedProblems?: Problem[];
  tags?: string[];
}

export interface Solution {
  id: string;
  problemId: string;
  provider: AIProvider | string;
  content: string;
  upvotes: number;
  downvotes: number;
  userVote?: 1 | -1 | null;
  generatedAt: string;
  modelVersion?: string | null;
}

export interface TrendingTopic {
  id: string;
  name: string;
  category: string;
  count: number;
  change: number;
  sparklineData: number[];
}

// ─── Analytics ────────────────────────────────────────────────────────────────

export interface CategoryCount {
  category: string;
  count: number;
  percentage: number;
}

export interface VolumeDataPoint {
  date: string;
  reddit: number;
  hackernews: number;
  total: number;
}

export interface SentimentDistribution {
  urgent: number;
  frustrated: number;
  curious: number;
  neutral: number;
}

export interface ActivityHeatmapCell {
  day: number;
  hour: number;
  count: number;
}

export interface AnalyticsSummary {
  totalProblems: number;
  totalSolutions: number;
  solvedRate: number;
  avgSolutionsPerProblem: number;
  problemsByCategory: CategoryCount[];
  volumeOverTime: VolumeDataPoint[];
  sentimentDistribution: SentimentDistribution;
  activityHeatmap: ActivityHeatmapCell[];
  topCategories: CategoryCount[];
  platformBreakdown: {
    reddit: number;
    hackernews: number;
  };
}

// ─── Dashboard Analytics ──────────────────────────────────────────────────────

export interface DashboardKPI {
  totalProblems: number;
  totalProblemsChange: number;
  totalClicks: number;
  totalClicksChange: number;
  solutionRate: number;
  solutionRateChange: number;
  totalSolutions: number;
  totalSolutionsChange: number;
}

export interface TopClickedProblem {
  id: string;
  title: string;
  category: string;
  clicks: number;
  clicksChange: number;
  hasSolution: boolean;
}

export interface CategoryDistribution {
  category: string;
  name: string;
  count: number;
  percentage: number;
  solutionCount: number;
  solutionRate: number;
  change: number;
}

export interface DashboardAnalytics {
  kpis: DashboardKPI;
  topClickedProblems: TopClickedProblem[];
  categoryDistribution: CategoryDistribution[];
}

// ─── Pagination & Params ──────────────────────────────────────────────────────

export interface PaginatedProblems {
  items: Problem[];
  total: number;
  page: number;
  perPage: number;
  totalPages: number;
  hasNext: boolean;
  hasPrev: boolean;
}

export interface ProblemsParams {
  platform?: Platform | '';
  category?: string;
  sentiment?: Sentiment | '';
  date_from?: string;
  date_to?: string;
  has_solution?: boolean;
  search?: string;
  page?: number;
  per_page?: number;
  sort_by?: 'recent' | 'upvotes' | 'comments';
}

// ─── Filter Presets ───────────────────────────────────────────────────────────

export interface DateRange {
  from?: string;
  to?: string;
}

export interface FilterPreset {
  id: string;
  name: string;
  platform: Platform | '';
  category: string;
  sentiment: Sentiment | '';
  dateRange: DateRange;
  hasSolution: boolean | null;
  search: string;
  createdAt: string;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

// ─── API Errors ───────────────────────────────────────────────────────────────

export interface ApiError {
  message: string;
  code?: string;
  statusCode?: number;
}
