import type { Metadata } from 'next';
import Link from 'next/link';
import {
  ArrowLeft,
  ExternalLink,
  ArrowUp,
  MessageSquare,
  Calendar,
} from 'lucide-react';
import { Navbar } from '@/components/layout/Navbar';
import { SolutionTabs } from '@/components/problems/SolutionTabs';
import { ProblemCard } from '@/components/dashboard/ProblemCard';
import { PrintButton } from '@/components/problems/PrintButton';
import { ShareButtons } from '@/components/problems/ShareButtons';
import ExportMenu from '@/components/problems/ExportMenu';
import { TagList } from '@/components/dashboard/TagList';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import { getProblem } from '@/lib/api';
import {
  SENTIMENT_COLORS,
  SENTIMENT_LABELS,
  PLATFORM_LABELS,
  formatRelativeTime,
  formatNumber,
  cn,
} from '@/lib/utils';

interface ProblemPageProps {
  params: { id: string };
}

export async function generateMetadata({
  params,
}: ProblemPageProps): Promise<Metadata> {
  try {
    const res = await fetch(
      `${process.env.NEXT_PUBLIC_API_URL}/problems/${params.id}`,
      { next: { revalidate: 300 } },
    );
    if (!res.ok) return { title: 'Problem | Solvora' };
    const problem = await res.json();
    const desc: string = problem.summary || (problem.body ?? '').slice(0, 160);
    return {
      title: `${problem.title} | Solvora`,
      description: desc,
      openGraph: {
        title: problem.title,
        description: desc,
        url: `${process.env.NEXTAUTH_URL}/problems/${params.id}`,
        siteName: 'Solvora',
        type: 'article',
      },
      twitter: {
        card: 'summary_large_image',
        title: problem.title,
        description: desc,
      },
    };
  } catch {
    return { title: 'Problem | Solvora' };
  }
}

export default async function ProblemPage({ params }: ProblemPageProps) {
  let problem;
  try {
    problem = await getProblem(params.id);
  } catch {
    return (
      <div className="min-h-screen flex flex-col">
        <Navbar />
        <main className="flex-1 container mx-auto px-4 py-12 text-center">
          <h1 className="text-2xl font-bold mb-2">Problem not found</h1>
          <p className="text-muted-foreground mb-6">
            This problem may have been removed or does not exist.
          </p>
          <Button asChild>
            <Link href="/dashboard">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Dashboard
            </Link>
          </Button>
        </main>
      </div>
    );
  }

  const categoryLabel =
    typeof problem.category === 'object' && problem.category !== null
      ? problem.category.name
      : (problem.category as string | null) ?? null;

  const sentimentColor = problem.sentiment
    ? (SENTIMENT_COLORS[problem.sentiment] ?? 'bg-gray-100 text-gray-700')
    : null;

  const sentimentLabel = problem.sentiment
    ? (SENTIMENT_LABELS[problem.sentiment] ?? problem.sentiment)
    : null;

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-1">
        <div className="container mx-auto px-4 py-6">
          {/* Back button */}
          <div className="mb-4">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/dashboard">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Dashboard
              </Link>
            </Button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-[1fr_300px] gap-6">
            {/* Main content */}
            <div className="space-y-6">
              {/* Problem header */}
              <Card>
                <CardHeader className="pb-3">
                  {/* Meta badges */}
                  <div className="flex flex-wrap items-center gap-2 mb-3">
                    <Badge variant="outline">
                      {PLATFORM_LABELS[problem.platform] ?? problem.platform}
                    </Badge>
                    {categoryLabel && (
                      <Badge variant="outline">{categoryLabel}</Badge>
                    )}
                    {sentimentColor && sentimentLabel && (
                      <span
                        className={cn(
                          'inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold',
                          sentimentColor,
                        )}
                      >
                        {sentimentLabel}
                      </span>
                    )}
                    {problem.hasSolution && (
                      <span className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400 font-semibold">
                        <span className="h-2 w-2 rounded-full bg-emerald-500" />
                        AI Solved
                      </span>
                    )}
                  </div>

                  <CardTitle className="text-xl leading-snug">
                    {problem.title}
                  </CardTitle>

                  {/* Share + Export buttons */}
                  <div className="flex items-center gap-2 flex-wrap">
                    <ShareButtons
                      title={problem.title}
                      url=""
                      problemId={problem.id}
                    />
                    <ExportMenu problemId={problem.id} />
                  </div>

                  {/* Stats row */}
                  <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground mt-2">
                    <span className="flex items-center gap-1">
                      <ArrowUp className="h-4 w-4" />
                      {formatNumber(problem.upvotes)} upvotes
                    </span>
                    <span className="flex items-center gap-1">
                      <MessageSquare className="h-4 w-4" />
                      {formatNumber(problem.commentCount)} comments
                    </span>
                    {problem.createdAt && (
                      <span className="flex items-center gap-1">
                        <Calendar className="h-4 w-4" />
                        <time dateTime={problem.createdAt}>
                          {formatRelativeTime(problem.createdAt)}
                        </time>
                      </span>
                    )}
                    {problem.author && (
                      <span>by {problem.author}</span>
                    )}
                  </div>
                </CardHeader>

                <Separator />

                <CardContent className="pt-4">
                  {/* Full problem body */}
                  <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-line text-sm leading-relaxed">
                    {problem.body}
                  </div>

                  {/* Tags */}
                  {problem.tags && problem.tags.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 mt-4 pt-4 border-t">
                      {problem.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                    </div>
                  )}

                  {/* Dynamic tags with edit support */}
                  <div className="mt-3">
                    <TagList problemId={problem.id} editable />
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3 mt-4 pt-4 border-t">
                    {problem.sourceUrl && (
                      <Button variant="outline" size="sm" asChild>
                        <a
                          href={problem.sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <ExternalLink className="mr-2 h-4 w-4" />
                          View Source
                        </a>
                      </Button>
                    )}
                    <PrintButton />
                  </div>
                </CardContent>
              </Card>

              {/* AI Solutions */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg">AI Solutions</CardTitle>
                </CardHeader>
                <CardContent>
                  <SolutionTabs problemId={problem.id} />
                </CardContent>
              </Card>
            </div>

            {/* Sidebar: related problems */}
            {problem.relatedProblems && problem.relatedProblems.length > 0 && (
              <aside>
                <h2 className="font-semibold text-sm mb-3 text-muted-foreground uppercase tracking-wider">
                  Related Problems
                </h2>
                <div className="space-y-3">
                  {problem.relatedProblems.slice(0, 5).map((related) => (
                    <ProblemCard key={related.id} problem={related} />
                  ))}
                </div>
              </aside>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
