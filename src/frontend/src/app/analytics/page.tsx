'use client';

import { useQuery } from '@tanstack/react-query';
import { Navbar } from '@/components/layout/Navbar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  BarChart2,
  TrendingUp,
  TrendingDown,
  MousePointerClick,
  CheckCircle2,
  Layers,
} from 'lucide-react';
import { getDashboardAnalytics } from '@/lib/api';
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import type { DashboardAnalytics, TopClickedProblem, CategoryDistribution } from '@/types';

const CHART_COLORS = [
  '#6366f1', '#8b5cf6', '#ec4899', '#3b82f6',
  '#22c55e', '#f97316', '#14b8a6', '#f43f5e',
];

// ─── Trend indicator ──────────────────────────────────────────────────────────

function Trend({ change }: { change: number }) {
  if (change === 0) return <span className="text-sm text-muted-foreground">—</span>;
  const up = change > 0;
  return (
    <span className={`inline-flex items-center gap-0.5 text-sm font-semibold ${up ? 'text-emerald-500' : 'text-destructive'}`}>
      {up ? <TrendingUp className="h-3.5 w-3.5" /> : <TrendingDown className="h-3.5 w-3.5" />}
      {Math.abs(change)}%
    </span>
  );
}

// ─── KPI card ────────────────────────────────────────────────────────────────

function KpiCard({
  label,
  value,
  change,
  icon,
}: {
  label: string;
  value: string;
  change: number;
  icon: React.ReactNode;
}) {
  return (
    <Card>
      <CardContent className="pt-5 pb-4">
        <div className="flex items-center justify-between mb-3">
          <p className="text-sm text-muted-foreground font-medium">{label}</p>
          <div className="p-2 rounded-md bg-muted">{icon}</div>
        </div>
        <p className="text-3xl font-bold tabular-nums">{value}</p>
        <div className="flex items-center gap-2 mt-2">
          <Trend change={change} />
          <span className="text-xs text-muted-foreground">from last week</span>
        </div>
      </CardContent>
    </Card>
  );
}

// ─── Top clicked problems ─────────────────────────────────────────────────────

function TopClickedList({ problems }: { problems: TopClickedProblem[] }) {
  const max = problems[0]?.clicks ?? 1;
  return (
    <div className="space-y-4">
      {problems.map((p, i) => (
        <div key={p.id} className="flex items-center gap-3">
          <span className="text-xs font-bold text-muted-foreground w-4 text-right shrink-0">{i + 1}</span>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between mb-1">
              <p className="text-sm font-medium truncate pr-2">{p.title}</p>
              <div className="flex items-center gap-2 shrink-0">
                <span className="text-sm font-bold tabular-nums">{p.clicks.toLocaleString()}</span>
                <Trend change={p.clicksChange} />
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-muted rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all"
                  style={{ width: `${(p.clicks / max) * 100}%` }}
                />
              </div>
              <span className="text-xs text-muted-foreground shrink-0">{p.category}</span>
              {p.hasSolution && (
                <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Category donut chart ─────────────────────────────────────────────────────

function CategoryDonut({ data }: { data: CategoryDistribution[] }) {
  const top = data.slice(0, 8);
  return (
    <div className="flex flex-col lg:flex-row gap-6 items-center">
      <div className="w-full lg:w-48 h-48 shrink-0">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={top}
              dataKey="percentage"
              nameKey="name"
              cx="50%"
              cy="50%"
              innerRadius="55%"
              outerRadius="80%"
              paddingAngle={2}
            >
              {top.map((_, i) => (
                <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />
              ))}
            </Pie>
            <Tooltip
              formatter={(v: number) => [`${v}%`, 'Share']}
              contentStyle={{ borderRadius: 8, fontSize: 12, border: '1px solid hsl(var(--border))', backgroundColor: 'hsl(var(--card))', color: 'hsl(var(--card-foreground))' }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 gap-2">
        {top.map((item, i) => (
          <div key={item.category} className="flex items-center gap-2">
            <div className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
            <div className="flex-1 min-w-0 flex items-center justify-between">
              <span className="text-sm truncate">{item.name}</span>
              <span className="text-sm font-semibold tabular-nums ml-2">{item.percentage}%</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Solution success rate chart ──────────────────────────────────────────────

function SolutionRateChart({ data }: { data: CategoryDistribution[] }) {
  const top = data.slice(0, 8).map((d) => ({ name: d.name, rate: d.solutionRate }));
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={top} layout="vertical" margin={{ left: 0, right: 30, top: 5, bottom: 5 }}>
        <CartesianGrid strokeDasharray="3 3" horizontal={false} className="stroke-border" />
        <XAxis type="number" domain={[0, 100]} tickFormatter={(v) => `${v}%`} tick={{ fontSize: 11 }} className="fill-muted-foreground" />
        <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 11 }} className="fill-muted-foreground" />
        <Tooltip
          formatter={(v: number) => [`${v}%`, 'Solution Rate']}
          contentStyle={{ borderRadius: 8, fontSize: 12, border: '1px solid hsl(var(--border))', backgroundColor: 'hsl(var(--card))', color: 'hsl(var(--card-foreground))' }}
        />
        <Bar dataKey="rate" radius={[0, 4, 4, 0]}>
          {top.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function DashboardSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}><CardContent className="pt-5 h-28 animate-pulse bg-muted rounded-lg" /></Card>
        ))}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card><CardContent className="h-72 animate-pulse bg-muted rounded-lg mt-4" /></Card>
        <Card><CardContent className="h-72 animate-pulse bg-muted rounded-lg mt-4" /></Card>
      </div>
      <Card><CardContent className="h-80 animate-pulse bg-muted rounded-lg mt-4" /></Card>
    </div>
  );
}

// ─── Main dashboard ───────────────────────────────────────────────────────────

function Dashboard({ data }: { data: DashboardAnalytics }) {
  const { kpis, topClickedProblems, categoryDistribution } = data;

  return (
    <div className="space-y-6">
      {/* KPI cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Total Problems" value={kpis.totalProblems.toLocaleString()} change={kpis.totalProblemsChange} icon={<Layers className="h-5 w-5 text-primary" />} />
        <KpiCard label="Total Clicks" value={kpis.totalClicks.toLocaleString()} change={kpis.totalClicksChange} icon={<MousePointerClick className="h-5 w-5 text-primary" />} />
        <KpiCard label="Solution Rate" value={`${kpis.solutionRate}%`} change={kpis.solutionRateChange} icon={<CheckCircle2 className="h-5 w-5 text-emerald-500" />} />
        <KpiCard label="AI Solutions" value={kpis.totalSolutions.toLocaleString()} change={kpis.totalSolutionsChange} icon={<BarChart2 className="h-5 w-5 text-primary" />} />
      </div>

      {/* Top clicked + Category donut */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <MousePointerClick className="h-4 w-4 text-primary" />
              Most Clicked Problems
            </CardTitle>
          </CardHeader>
          <CardContent>
            {topClickedProblems.length > 0 ? (
              <TopClickedList problems={topClickedProblems} />
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                No clicks tracked yet. Clicks appear here as users browse problems.
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" />
              Category Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <CategoryDonut data={categoryDistribution} />
          </CardContent>
        </Card>
      </div>

      {/* Category breakdown table */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Category Breakdown
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 pr-4 font-semibold text-muted-foreground">Category</th>
                  <th className="text-right py-3 px-4 font-semibold text-muted-foreground">Problems</th>
                  <th className="text-right py-3 px-4 font-semibold text-muted-foreground">Share</th>
                  <th className="text-right py-3 px-4 font-semibold text-muted-foreground">Solutions</th>
                  <th className="text-right py-3 px-4 font-semibold text-muted-foreground">Success Rate</th>
                  <th className="text-right py-3 pl-4 font-semibold text-muted-foreground">Trend</th>
                </tr>
              </thead>
              <tbody>
                {categoryDistribution.map((item, i) => (
                  <tr key={item.category} className="border-b last:border-0 hover:bg-muted/50 transition-colors">
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2">
                        <div className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                        <span className="font-medium">{item.name}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 text-right tabular-nums">{item.count.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right tabular-nums text-muted-foreground">{item.percentage}%</td>
                    <td className="py-3 px-4 text-right tabular-nums">{item.solutionCount.toLocaleString()}</td>
                    <td className="py-3 px-4 text-right tabular-nums">
                      <span className={`font-semibold ${item.solutionRate > 20 ? 'text-emerald-500' : item.solutionRate > 10 ? 'text-amber-500' : 'text-destructive'}`}>
                        {item.solutionRate}%
                      </span>
                    </td>
                    <td className="py-3 pl-4 text-right"><Trend change={item.change} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Solution rate chart */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
            Solution Success Rate by Category
          </CardTitle>
        </CardHeader>
        <CardContent>
          <SolutionRateChart data={categoryDistribution} />
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function AnalyticsPage() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard-analytics'],
    queryFn: getDashboardAnalytics,
    staleTime: 5 * 60 * 1000,
  });

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <div className="container mx-auto px-4 py-6">
          <div className="flex items-center gap-2 mb-6">
            <BarChart2 className="h-6 w-6 text-primary" />
            <h1 className="text-2xl font-bold">Analytics</h1>
          </div>
          {isLoading && <DashboardSkeleton />}
          {isError && (
            <div className="py-12 text-center text-muted-foreground">
              Failed to load analytics. Please try again later.
            </div>
          )}
          {data && <Dashboard data={data} />}
        </div>
      </main>
    </div>
  );
}
