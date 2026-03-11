'use client';

import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ThumbsUp, ThumbsDown, Sparkles, Loader2, Bot } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { getSolutions, generateSolutions, submitVote } from '@/lib/api';
import { useToast } from '@/components/ui/toast';
import { renderMarkdown, cn, formatNumber } from '@/lib/utils';
import type { AIProvider, Solution } from '@/types';

const PROVIDERS: { value: AIProvider; label: string; color: string }[] = [
  { value: 'gemini', label: 'Gemini', color: 'text-blue-500' },
  { value: 'openai', label: 'OpenAI', color: 'text-emerald-500' },
  { value: 'claude', label: 'Claude', color: 'text-amber-500' },
];

// ─── Provider icon ────────────────────────────────────────────────────────────

function ProviderIcon({
  provider,
  className,
}: {
  provider: AIProvider;
  className?: string;
}) {
  if (provider === 'gemini') {
    return (
      <svg viewBox="0 0 24 24" className={cn('fill-current', className)} aria-label="Gemini">
        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" fill="none" />
      </svg>
    );
  }
  if (provider === 'openai') {
    return (
      <svg viewBox="0 0 24 24" className={cn('fill-current', className)} aria-label="OpenAI">
        <path d="M22.2819 9.8211a5.9847 5.9847 0 0 0-.5157-4.9108 6.0462 6.0462 0 0 0-6.5098-2.9A6.0651 6.0651 0 0 0 4.9807 4.1818a5.9847 5.9847 0 0 0-3.9977 2.9 6.0462 6.0462 0 0 0 .7427 7.0966 5.98 5.98 0 0 0 .511 4.9107 6.051 6.051 0 0 0 6.5146 2.9001A5.9847 5.9847 0 0 0 13.2599 24a6.0557 6.0557 0 0 0 5.7718-4.2058 5.9894 5.9894 0 0 0 3.9977-2.9001 6.0557 6.0557 0 0 0-.7475-7.0729zm-9.022 12.6081a4.4755 4.4755 0 0 1-2.8764-1.0408l.1419-.0804 4.7783-2.7582a.7948.7948 0 0 0 .3927-.6813v-6.7369l2.02 1.1686a.071.071 0 0 1 .038.052v5.5826a4.504 4.504 0 0 1-4.4945 4.4944zm-9.6607-4.1254a4.4708 4.4708 0 0 1-.5346-3.0137l.142.0852 4.783 2.7582a.7712.7712 0 0 0 .7806 0l5.8428-3.3685v2.3324a.0804.0804 0 0 1-.0332.0615L9.74 19.9502a4.4992 4.4992 0 0 1-6.1408-1.6464zM2.3408 7.8956a4.485 4.485 0 0 1 2.3655-1.9728V11.6a.7664.7664 0 0 0 .3879.6765l5.8144 3.3543-2.0201 1.1685a.0757.0757 0 0 1-.071 0l-4.8303-2.7865A4.504 4.504 0 0 1 2.3408 7.872zm16.5963 3.8558L13.1038 8.364 15.1192 7.2a.0757.0757 0 0 1 .071 0l4.8303 2.7913a4.4944 4.4944 0 0 1-.6765 8.1042v-5.6772a.79.79 0 0 0-.407-.667zm2.0107-3.0231l-.142-.0852-4.7735-2.7818a.7759.7759 0 0 0-.7854 0L9.409 9.2297V6.8974a.0662.0662 0 0 1 .0284-.0615l4.8303-2.7866a4.4992 4.4992 0 0 1 6.6802 4.66zM8.3065 12.863l-2.02-1.1638a.0804.0804 0 0 1-.038-.0567V6.0742a4.4992 4.4992 0 0 1 7.3757-3.4537l-.142.0805L8.704 5.459a.7948.7948 0 0 0-.3927.6813zm1.0976-2.3654l2.602-1.4998 2.6069 1.4998v2.9994l-2.5974 1.4997-2.6067-1.4997Z" />
      </svg>
    );
  }
  // Claude
  return <Bot className={className} />;
}

// ─── Vote button ──────────────────────────────────────────────────────────────

function VoteButton({
  type,
  count,
  active,
  onClick,
}: {
  type: 'up' | 'down';
  count: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      aria-label={type === 'up' ? 'Upvote' : 'Downvote'}
      aria-pressed={active}
      className={cn(
        'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        type === 'up'
          ? active
            ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
            : 'hover:bg-emerald-50 dark:hover:bg-emerald-900/20 text-muted-foreground hover:text-emerald-600'
          : active
            ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            : 'hover:bg-red-50 dark:hover:bg-red-900/20 text-muted-foreground hover:text-red-600',
      )}
    >
      {type === 'up' ? (
        <ThumbsUp className="h-4 w-4" fill={active ? 'currentColor' : 'none'} />
      ) : (
        <ThumbsDown className="h-4 w-4" fill={active ? 'currentColor' : 'none'} />
      )}
      <span className="tabular-nums">{formatNumber(count)}</span>
    </button>
  );
}

// ─── Solution content ─────────────────────────────────────────────────────────

function SolutionContent({
  solution,
  problemId,
}: {
  solution: Solution;
  problemId: string;
}) {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Optimistic vote state
  const [optimisticUpvotes, setOptimisticUpvotes] = useState(solution.upvotes);
  const [optimisticDownvotes, setOptimisticDownvotes] = useState(solution.downvotes);
  const [currentVote, setCurrentVote] = useState<1 | -1 | null>(
    solution.userVote ?? null,
  );

  const voteMutation = useMutation({
    mutationFn: (voteType: 1 | -1) => submitVote(solution.id, voteType),
    onMutate: async (voteType) => {
      // Optimistic update
      const prevVote = currentVote;
      const newVote = prevVote === voteType ? null : voteType;

      let upDelta = 0;
      let downDelta = 0;

      if (prevVote === 1) upDelta--;
      if (prevVote === -1) downDelta--;
      if (newVote === 1) upDelta++;
      if (newVote === -1) downDelta++;

      setCurrentVote(newVote as 1 | -1 | null);
      setOptimisticUpvotes((n) => n + upDelta);
      setOptimisticDownvotes((n) => n + downDelta);

      return { prevVote };
    },
    onError: (_err, _voteType, context) => {
      // Revert
      setCurrentVote(context?.prevVote ?? null);
      setOptimisticUpvotes(solution.upvotes);
      setOptimisticDownvotes(solution.downvotes);
      toast({ title: 'Vote failed', variant: 'destructive' });
    },
    onSettled: () => {
      void queryClient.invalidateQueries({
        queryKey: ['solutions', problemId],
      });
    },
  });

  return (
    <div className="space-y-4">
      {/* Solution text */}
      <div
        className="prose prose-sm dark:prose-invert max-w-none text-sm leading-relaxed"
        dangerouslySetInnerHTML={{ __html: renderMarkdown(solution.content) }}
      />

      {/* Meta + votes */}
      <div className="flex items-center justify-between pt-3 border-t">
        <p className="text-xs text-muted-foreground">
          Generated{' '}
          {new Date(solution.generatedAt).toLocaleDateString()}
          {solution.modelVersion && ` · ${solution.modelVersion}`}
        </p>

        <div className="flex items-center gap-2">
          <VoteButton
            type="up"
            count={optimisticUpvotes}
            active={currentVote === 1}
            onClick={() => voteMutation.mutate(1)}
          />
          <VoteButton
            type="down"
            count={optimisticDownvotes}
            active={currentVote === -1}
            onClick={() => voteMutation.mutate(-1)}
          />
        </div>
      </div>
    </div>
  );
}

// ─── Empty tab content ────────────────────────────────────────────────────────

function EmptyProviderTab({
  provider,
  problemId,
  onGenerated,
}: {
  provider: AIProvider;
  problemId: string;
  onGenerated: () => void;
}) {
  const { toast } = useToast();

  const generateMutation = useMutation({
    mutationFn: () => generateSolutions(problemId, [provider]),
    onSuccess: (data) => {
      const generated = (data as { generated?: string[] })?.generated ?? [];
      if (generated.length > 0) {
        toast({ title: 'Solution ready', description: `${provider} solution generated.` });
      } else {
        toast({ title: 'Generation failed', description: `${provider} could not generate a solution.`, variant: 'destructive' });
      }
      onGenerated();
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        'Could not generate a solution. Check that API keys are configured in the backend .env file.';
      toast({
        title: 'Generation failed',
        description: msg,
        variant: 'destructive',
      });
    },
  });

  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <Sparkles className="h-10 w-10 text-muted-foreground/40 mb-3" />
      <p className="text-sm font-medium mb-1">No solution yet</p>
      <p className="text-xs text-muted-foreground mb-4">
        Click below to generate a solution using{' '}
        {PROVIDERS.find((p) => p.value === provider)?.label}.
      </p>
      <Button
        size="sm"
        onClick={() => generateMutation.mutate()}
        disabled={generateMutation.isPending}
      >
        {generateMutation.isPending ? (
          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
        ) : (
          <Sparkles className="mr-2 h-4 w-4" />
        )}
        Generate Solution
      </Button>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface SolutionTabsProps {
  problemId: string;
}

export function SolutionTabs({ problemId }: SolutionTabsProps) {
  const queryClient = useQueryClient();

  const { data: solutions, isLoading } = useQuery({
    queryKey: ['solutions', problemId],
    queryFn: () => getSolutions(problemId),
  });

  const getSolutionForProvider = (provider: AIProvider): Solution | undefined =>
    solutions?.find((s) => s.provider === provider);

  const handleGenerated = () => {
    void queryClient.invalidateQueries({
      queryKey: ['solutions', problemId],
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-3">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
    );
  }

  return (
    <Tabs defaultValue="gemini">
      <TabsList className="mb-4">
        {PROVIDERS.map(({ value, label, color }) => {
          const hasSolution = !!getSolutionForProvider(value);
          return (
            <TabsTrigger
              key={value}
              value={value}
              className="flex items-center gap-1.5"
            >
              <ProviderIcon
                provider={value}
                className={cn('h-4 w-4', hasSolution ? color : 'text-muted-foreground/40')}
              />
              {label}
              {hasSolution && (
                <span
                  className="h-1.5 w-1.5 rounded-full bg-emerald-500"
                  aria-label="Solution available"
                />
              )}
            </TabsTrigger>
          );
        })}
      </TabsList>

      {PROVIDERS.map(({ value }) => {
        const solution = getSolutionForProvider(value);
        return (
          <TabsContent key={value} value={value}>
            {solution ? (
              <SolutionContent solution={solution} problemId={problemId} />
            ) : (
              <EmptyProviderTab
                provider={value}
                problemId={problemId}
                onGenerated={handleGenerated}
              />
            )}
          </TabsContent>
        );
      })}
    </Tabs>
  );
}
