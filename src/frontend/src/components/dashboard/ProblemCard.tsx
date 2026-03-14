'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Star, ArrowUp, MessageSquare, ExternalLink } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/store/authStore';
import { addBookmark, removeBookmark, trackProblemClick } from '@/lib/api';
import { useToast } from '@/components/ui/toast';
import { TagList } from '@/components/dashboard/TagList';
import {
  formatRelativeTime,
  formatNumber,
  SENTIMENT_COLORS,
  SENTIMENT_LABELS,
  cn,
} from '@/lib/utils';
import type { Problem } from '@/types';

// ─── Platform icons ───────────────────────────────────────────────────────────

function RedditIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      className={cn('fill-current', className)}
      aria-label="Reddit"
      role="img"
    >
      <circle cx="10" cy="10" r="10" className="text-[#FF4500]" />
      <path
        d="M16.67 10a1.46 1.46 0 0 0-2.47-1 7.12 7.12 0 0 0-3.85-1.23l.65-3.08 2.13.45a1 1 0 1 0 1-.98 1 1 0 0 0-.96.68l-2.38-.5a.16.16 0 0 0-.19.12l-.73 3.44a7.14 7.14 0 0 0-3.89 1.23 1.46 1.46 0 1 0-1.61 2.39 2.87 2.87 0 0 0 0 .44c0 2.24 2.61 4.06 5.83 4.06s5.83-1.82 5.83-4.06a2.87 2.87 0 0 0 0-.44 1.46 1.46 0 0 0 .64-1.52zM7.27 11a1 1 0 1 1 1 1 1 1 0 0 1-1-1zm5.58 2.65a3.58 3.58 0 0 1-2.85.86 3.58 3.58 0 0 1-2.85-.86.18.18 0 1 1 .26-.25 3.24 3.24 0 0 0 2.59.73 3.24 3.24 0 0 0 2.59-.73.18.18 0 0 1 .26.25zm-.16-1.65a1 1 0 1 1 1-1 1 1 0 0 1-1 1z"
        fill="white"
      />
    </svg>
  );
}

function HackerNewsIcon({ className }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 20 20"
      className={cn('fill-current', className)}
      aria-label="Hacker News"
      role="img"
    >
      <rect width="20" height="20" rx="2" className="text-[#FF6600]" />
      <text
        x="50%"
        y="50%"
        dominantBaseline="central"
        textAnchor="middle"
        fontSize="13"
        fontWeight="bold"
        fill="white"
        fontFamily="Arial, sans-serif"
      >
        Y
      </text>
    </svg>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface ProblemCardProps {
  problem: Problem;
  onBookmarkChange?: (problemId: string, bookmarked: boolean) => void;
}

export function ProblemCard({ problem, onBookmarkChange }: ProblemCardProps) {
  const { isAuthenticated } = useAuthStore();
  const { toast } = useToast();
  const [isBookmarked, setIsBookmarked] = useState(
    problem.isBookmarked ?? false,
  );
  const [bookmarkLoading, setBookmarkLoading] = useState(false);

  const handleBookmark = async (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    if (!isAuthenticated) {
      toast({
        title: 'Login required',
        description: 'Please log in to bookmark problems.',
        variant: 'destructive',
      });
      return;
    }

    const optimistic = !isBookmarked;
    setIsBookmarked(optimistic);
    setBookmarkLoading(true);

    try {
      if (optimistic) {
        await addBookmark(problem.id);
      } else {
        await removeBookmark(problem.id);
      }
      onBookmarkChange?.(problem.id, optimistic);
    } catch {
      setIsBookmarked(!optimistic); // Revert
      toast({
        title: 'Error',
        description: 'Could not update bookmark. Try again.',
        variant: 'destructive',
      });
    } finally {
      setBookmarkLoading(false);
    }
  };

  return (
    <Card className="card-hover group overflow-hidden">
      <Link href={`/problems/${problem.id}`} className="block focus:outline-none" onClick={() => trackProblemClick(problem.id)}>
        <CardContent className="p-4">
          {/* Header row */}
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="flex items-center gap-2 flex-wrap min-w-0">
              {/* Platform icon */}
              <span className="shrink-0">
                {problem.platform === 'reddit' ? (
                  <RedditIcon className="h-5 w-5" />
                ) : (
                  <HackerNewsIcon className="h-5 w-5" />
                )}
              </span>

              {/* Category badge */}
              {problem.category && (
                <Badge variant="outline" className="text-xs shrink-0">
                  {typeof problem.category === 'object' ? problem.category?.name : problem.category}
                </Badge>
              )}

              {/* Sentiment badge */}
              {problem.sentiment && (
                <span
                  className={cn(
                    'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold shrink-0',
                    SENTIMENT_COLORS[problem.sentiment] ?? 'bg-gray-100 text-gray-700',
                  )}
                >
                  {SENTIMENT_LABELS[problem.sentiment] ?? problem.sentiment}
                </span>
              )}
            </div>

            {/* Bookmark button */}
            <button
              onClick={handleBookmark}
              disabled={bookmarkLoading}
              aria-label={isBookmarked ? 'Remove bookmark' : 'Add bookmark'}
              className={cn(
                'shrink-0 p-1 rounded-md transition-colors',
                isBookmarked
                  ? 'text-amber-500 hover:text-amber-600'
                  : 'text-muted-foreground hover:text-amber-500',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              )}
            >
              <Star
                className="h-4 w-4"
                fill={isBookmarked ? 'currentColor' : 'none'}
              />
            </button>
          </div>

          {/* Title */}
          <h2 className="font-semibold text-sm leading-snug line-clamp-2 mb-1.5 text-foreground group-hover:text-primary transition-colors">
            {problem.title}
          </h2>

          {/* Tags */}
          <div className="mb-1.5" onClick={(e) => e.preventDefault()}>
            <TagList problemId={problem.id} />
          </div>

          {/* Body preview */}
          <p className="text-xs text-muted-foreground line-clamp-3 mb-3">
            {problem.body}
          </p>

          {/* Footer */}
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-3">
              {/* Upvotes */}
              <span className="flex items-center gap-1">
                <ArrowUp className="h-3.5 w-3.5" aria-hidden="true" />
                {formatNumber(problem.upvotes)}
              </span>

              {/* Comments */}
              <span className="flex items-center gap-1">
                <MessageSquare className="h-3.5 w-3.5" aria-hidden="true" />
                {formatNumber(problem.commentCount)}
              </span>

              {/* AI solution indicator */}
              {problem.hasSolution && (
                <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-medium">
                  <span
                    className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"
                    aria-hidden="true"
                  />
                  AI solved
                </span>
              )}
            </div>

            <div className="flex items-center gap-2">
              {/* Timestamp */}
              <time
                dateTime={problem.createdAt}
                title={new Date(problem.createdAt).toLocaleString()}
              >
                {formatRelativeTime(problem.createdAt)}
              </time>

              {/* External link */}
              <a
                href={problem.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                aria-label="View original source"
                className="hover:text-primary transition-colors"
              >
                <ExternalLink className="h-3.5 w-3.5" />
              </a>
            </div>
          </div>
        </CardContent>
      </Link>
    </Card>
  );
}
