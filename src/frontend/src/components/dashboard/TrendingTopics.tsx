'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { TrendingUp } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Skeleton } from '@/components/ui/skeleton';
import { Badge } from '@/components/ui/badge';
import { getTrending } from '@/lib/api';
import { useFilterStore } from '@/store/filterStore';
import { formatNumber, cn } from '@/lib/utils';
import type { TrendingTopic } from '@/types';

type Period = '24h' | '7d' | '30d';

// ─── Mini sparkline ───────────────────────────────────────────────────────────

function Sparkline({ data }: { data: number[] }) {
  if (!data || data.length === 0) return null;

  const max = Math.max(...data, 1);
  const bars = data.slice(-7);
  const barMax = Math.max(...bars, 1);

  return (
    <div
      className="flex items-end gap-0.5 h-6 w-12 shrink-0"
      aria-hidden="true"
    >
      {bars.map((val, i) => (
        <div
          key={i}
          className="flex-1 rounded-sm bg-primary/60 transition-all"
          style={{ height: `${Math.round((val / barMax) * 100)}%`, minHeight: '2px' }}
        />
      ))}
    </div>
  );
}

// ─── Skeleton ─────────────────────────────────────────────────────────────────

function TrendingSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 8 }).map((_, i) => (
        <div key={i} className="flex items-center gap-2 py-1.5">
          <Skeleton className="h-4 w-4 rounded-full shrink-0" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-8" />
          <Skeleton className="h-6 w-12" />
        </div>
      ))}
    </div>
  );
}

// ─── Topic row ────────────────────────────────────────────────────────────────

function TopicRow({
  topic,
  rank,
  onClick,
}: {
  topic: TrendingTopic;
  rank: number;
  onClick: () => void;
}) {
  const change = topic.change;
  const changeColor =
    change > 0
      ? 'text-emerald-600 dark:text-emerald-400'
      : change < 0
        ? 'text-red-500'
        : 'text-muted-foreground';

  return (
    <button
      onClick={onClick}
      className={cn(
        'w-full flex items-center gap-2 py-2 px-2 rounded-md text-left',
        'hover:bg-accent transition-colors group',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
      )}
      aria-label={`Filter by ${topic.name}`}
    >
      {/* Rank */}
      <span className="text-xs font-bold text-muted-foreground w-4 text-right shrink-0">
        {rank}
      </span>

      {/* Name */}
      <span className="flex-1 text-sm font-medium truncate group-hover:text-primary transition-colors">
        {topic.name}
      </span>

      {/* Change */}
      <span className={cn('text-xs font-semibold shrink-0 tabular-nums', changeColor)}>
        {change > 0 ? '+' : ''}
        {change}%
      </span>

      {/* Count badge */}
      <Badge variant="secondary" className="shrink-0 text-xs tabular-nums">
        {formatNumber(topic.count)}
      </Badge>

      {/* Sparkline */}
      <Sparkline data={topic.sparklineData} />
    </button>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TrendingTopics() {
  const [period, setPeriod] = useState<Period>('24h');
  const setFilter = useFilterStore((s) => s.setFilter);

  const { data: topics, isLoading } = useQuery({
    queryKey: ['trending', period],
    queryFn: () => getTrending(period),
    staleTime: 5 * 60 * 1000,
  });

  const handleTopicClick = (topic: TrendingTopic) => {
    setFilter('category', topic.category);
    setFilter('search', topic.name);
  };

  return (
    <aside aria-label="Trending topics">
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp className="h-4 w-4 text-primary shrink-0" />
        <h2 className="font-semibold text-sm">Trending</h2>
      </div>

      {/* Period tabs */}
      <Tabs
        value={period}
        onValueChange={(v) => setPeriod(v as Period)}
        className="mb-3"
      >
        <TabsList className="w-full h-8 text-xs">
          <TabsTrigger value="24h" className="flex-1 text-xs">
            24h
          </TabsTrigger>
          <TabsTrigger value="7d" className="flex-1 text-xs">
            7d
          </TabsTrigger>
          <TabsTrigger value="30d" className="flex-1 text-xs">
            30d
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* Topic list */}
      {isLoading ? (
        <TrendingSkeleton />
      ) : !topics || topics.length === 0 ? (
        <p className="text-sm text-muted-foreground text-center py-8">
          No trending topics yet.
        </p>
      ) : (
        <div className="space-y-0.5">
          {topics.slice(0, 10).map((topic, index) => (
            <TopicRow
              key={topic.id}
              topic={topic}
              rank={index + 1}
              onClick={() => handleTopicClick(topic)}
            />
          ))}
        </div>
      )}
    </aside>
  );
}
