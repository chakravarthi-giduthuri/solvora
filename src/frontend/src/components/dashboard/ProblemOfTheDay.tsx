'use client';

import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import apiClient from '@/lib/api';
import { PLATFORM_LABELS } from '@/lib/utils';
import type { Problem } from '@/types';

async function fetchPotd(): Promise<Problem | null> {
  const res = await apiClient.get<{ potd: Problem | null }>('/problems/potd');
  return res.data?.potd ?? null;
}

export function ProblemOfTheDay() {
  const { data: potd } = useQuery<Problem | null>({
    queryKey: ['potd'],
    queryFn: fetchPotd,
    staleTime: 60 * 60 * 1000,
  });

  if (!potd) return null;

  const categoryLabel =
    potd.category && typeof potd.category === 'object'
      ? potd.category.name
      : (potd.category as string | null) ?? null;

  return (
    <div className="rounded-xl border border-amber-400/50 bg-amber-50/5 dark:bg-amber-950/10 p-4 mb-4">
      <div className="flex items-center gap-2 mb-2">
        <Badge className="bg-amber-500 text-white border-transparent text-xs px-2 py-0.5">
          Problem of the Day
        </Badge>
      </div>

      <Link
        href={`/problems/${potd.id}`}
        className="block group"
      >
        <h3 className="font-semibold text-sm leading-snug group-hover:text-primary transition-colors mb-1">
          {potd.title}
        </h3>
      </Link>

      {potd.summary && (
        <p className="text-xs text-muted-foreground line-clamp-2 mb-2">
          {potd.summary}
        </p>
      )}

      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-xs">
          {PLATFORM_LABELS[potd.platform] ?? potd.platform}
        </Badge>
        {categoryLabel && (
          <Badge variant="outline" className="text-xs">
            {categoryLabel}
          </Badge>
        )}
      </div>
    </div>
  );
}
