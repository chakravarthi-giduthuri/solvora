'use client';

import { useCallback, useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { AlertCircle, ArrowUp, ChevronFirst, ChevronLast, Inbox, RefreshCw } from 'lucide-react';
import { ProblemCard } from './ProblemCard';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { getProblems } from '@/lib/api';
import { useFilterStore } from '@/store/filterStore';
import type { ProblemsParams } from '@/types';

// ─── Skeleton loader ──────────────────────────────────────────────────────────

function ProblemCardSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-5 rounded-full" />
        <Skeleton className="h-5 w-20 rounded-full" />
        <Skeleton className="h-5 w-16 rounded-full" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-2/3" />
      <div className="flex justify-between">
        <div className="flex gap-3">
          <Skeleton className="h-3 w-10" />
          <Skeleton className="h-3 w-10" />
        </div>
        <Skeleton className="h-3 w-20" />
      </div>
    </div>
  );
}

// ─── Empty & error states ─────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <Inbox className="h-16 w-16 text-muted-foreground/30 mb-4" />
      <h3 className="font-semibold text-lg mb-1">No problems found</h3>
      <p className="text-sm text-muted-foreground max-w-xs">
        Try adjusting your filters or search query to see more results.
      </p>
    </div>
  );
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <AlertCircle className="h-16 w-16 text-destructive/50 mb-4" />
      <h3 className="font-semibold text-lg mb-1">Failed to load problems</h3>
      <p className="text-sm text-muted-foreground mb-4">
        There was an error fetching data from the server.
      </p>
      <Button onClick={onRetry} variant="outline" size="sm">
        <RefreshCw className="mr-2 h-4 w-4" />
        Try again
      </Button>
    </div>
  );
}

// ─── Back-to-top button ───────────────────────────────────────────────────────

function BackToTopButton() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    const onScroll = () => setVisible(window.scrollY > 400);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  if (!visible) return null;

  return (
    <button
      onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
      className="fixed bottom-6 right-6 z-50 flex h-10 w-10 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg hover:bg-primary/90 transition-colors"
      aria-label="Back to top"
    >
      <ArrowUp className="h-5 w-5" />
    </button>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function ProblemFeed() {
  const {
    platform,
    category,
    sentiment,
    dateRange,
    hasSolution,
    search,
    page,
    sortBy,
    setFilter,
  } = useFilterStore();

  const params: ProblemsParams = {
    platform: platform || undefined,
    category: category || undefined,
    sentiment: sentiment || undefined,
    date_from: dateRange.from,
    date_to: dateRange.to,
    has_solution: hasSolution ?? undefined,
    search: search || undefined,
    page,
    per_page: 20,
    sort_by: sortBy,
  };

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['problems', params],
    queryFn: () => getProblems(params),
  });

  // Scroll to top whenever the page changes so the user sees the new content
  const scrollToTop = useCallback(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }, []);

  const goToPage = useCallback(
    (p: number) => {
      setFilter('page', p);
      scrollToTop();
    },
    [setFilter, scrollToTop],
  );

  if (isLoading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading problems">
        {Array.from({ length: 6 }).map((_, i) => (
          <ProblemCardSkeleton key={i} />
        ))}
      </div>
    );
  }

  if (isError) {
    return <ErrorState onRetry={() => void refetch()} />;
  }

  if (!data || data.items.length === 0) {
    return <EmptyState />;
  }

  const totalPages = data.totalPages ?? 1;

  return (
    <>
      <section aria-label="Problem feed">
        {/* Results summary */}
        <p className="text-xs text-muted-foreground mb-3">
          Showing{' '}
          <span className="font-medium text-foreground">
            {(page - 1) * 20 + 1}–{Math.min(page * 20, data.total)}
          </span>{' '}
          of <span className="font-medium text-foreground">{data.total}</span>{' '}
          problems
        </p>

        {/* Problem list */}
        <div className="space-y-3">
          {data.items.map((problem) => (
            <ProblemCard key={problem.id} problem={problem} />
          ))}
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between mt-6 pt-4 border-t gap-2">
          {/* Left: First + Previous */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => goToPage(1)}
              aria-label="First page"
              className="hidden sm:flex"
            >
              <ChevronFirst className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={!data.hasPrev}
              onClick={() => goToPage(page - 1)}
            >
              Previous
            </Button>
          </div>

          {/* Center: page indicator */}
          <span className="text-sm text-muted-foreground whitespace-nowrap">
            Page <span className="font-medium text-foreground">{data.page}</span>{' '}
            of{' '}
            <span className="font-medium text-foreground">{totalPages}</span>
          </span>

          {/* Right: Next + Last */}
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={!data.hasNext}
              onClick={() => goToPage(page + 1)}
            >
              Next
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => goToPage(totalPages)}
              aria-label="Last page"
              className="hidden sm:flex"
            >
              <ChevronLast className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </section>

      {/* Floating back-to-top button */}
      <BackToTopButton />
    </>
  );
}
