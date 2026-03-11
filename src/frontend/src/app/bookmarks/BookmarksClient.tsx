'use client';

import { useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Bookmark, Lock, Loader2 } from 'lucide-react';
import Link from 'next/link';
import { ProblemCard } from '@/components/dashboard/ProblemCard';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { getBookmarks } from '@/lib/api';
import { useAuthStore } from '@/store/authStore';

function BookmarkSkeleton() {
  return (
    <div className="rounded-lg border bg-card p-4 space-y-3">
      <div className="flex items-center gap-2">
        <Skeleton className="h-5 w-5 rounded-full" />
        <Skeleton className="h-5 w-20 rounded-full" />
      </div>
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-3/4" />
      <Skeleton className="h-3 w-full" />
      <Skeleton className="h-3 w-2/3" />
    </div>
  );
}

export function BookmarksClient() {
  const { isAuthenticated } = useAuthStore();
  const queryClient = useQueryClient();

  const { data: bookmarks, isLoading } = useQuery({
    queryKey: ['bookmarks'],
    queryFn: getBookmarks,
    enabled: isAuthenticated,
  });

  // If not authenticated, show gate
  if (!isAuthenticated) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="p-4 rounded-full bg-muted mb-4">
          <Lock className="h-8 w-8 text-muted-foreground" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Sign in to view bookmarks</h2>
        <p className="text-muted-foreground mb-6 max-w-xs">
          Create an account or log in to bookmark problems and access them anytime.
        </p>
        <Button asChild>
          <Link href="/auth/login">Login</Link>
        </Button>
      </div>
    );
  }

  const handleBookmarkChange = (problemId: string, bookmarked: boolean) => {
    if (!bookmarked) {
      // Remove from cache optimistically
      queryClient.setQueryData<typeof bookmarks>(['bookmarks'], (old) =>
        old?.filter((p) => p.id !== problemId),
      );
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="flex items-center gap-2 mb-6">
        <Bookmark className="h-6 w-6 text-primary" />
        <h1 className="text-2xl font-bold">Bookmarks</h1>
        {bookmarks && (
          <span className="ml-2 text-sm text-muted-foreground">
            ({bookmarks.length} saved)
          </span>
        )}
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="max-w-2xl space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <BookmarkSkeleton key={i} />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && bookmarks && bookmarks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <Bookmark className="h-16 w-16 text-muted-foreground/30 mb-4" />
          <h2 className="text-lg font-semibold mb-1">No bookmarks yet</h2>
          <p className="text-sm text-muted-foreground mb-6">
            Star problems from the feed to save them here.
          </p>
          <Button asChild variant="outline">
            <Link href="/dashboard">Browse Problems</Link>
          </Button>
        </div>
      )}

      {/* Bookmarks grid */}
      {!isLoading && bookmarks && bookmarks.length > 0 && (
        <div className="max-w-2xl space-y-3">
          {bookmarks.map((problem) => (
            <ProblemCard
              key={problem.id}
              problem={{ ...problem, isBookmarked: true }}
              onBookmarkChange={handleBookmarkChange}
            />
          ))}
        </div>
      )}
    </div>
  );
}
