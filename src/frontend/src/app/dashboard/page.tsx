import type { Metadata } from 'next';
import Link from 'next/link';
import { FilterSidebar } from '@/components/dashboard/FilterSidebar';
import { ProblemFeed } from '@/components/dashboard/ProblemFeed';
import { TrendingTopics } from '@/components/dashboard/TrendingTopics';
import { NewProblemsBanner } from '@/components/dashboard/NewProblemsBanner';
import { ProblemOfTheDay } from '@/components/dashboard/ProblemOfTheDay';

export const metadata: Metadata = {
  title: 'Dashboard — Solvora',
  description: 'Browse and filter AI-aggregated community problems',
};

export default function DashboardPage() {
  return (
    <div>
      <NewProblemsBanner />
      <div className="container mx-auto px-4 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-[240px_1fr_260px] gap-6">
          {/* Left sidebar: filters */}
          <aside className="hidden lg:block">
            <div className="sticky top-24 max-h-[calc(100vh-6rem)] overflow-y-auto pb-4 pr-1">
              <FilterSidebar />
            </div>
          </aside>

          {/* Main feed */}
          <section>
            <ProblemOfTheDay />
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-xl font-bold">Problems Feed</h1>

              <div className="flex items-center gap-2">
                <Link
                  href="/leaderboard"
                  className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
                >
                  🏆 Leaderboard
                </Link>
                <Link
                  href="/problems/submit"
                  className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-blue-600 hover:bg-blue-700 text-white transition-colors"
                >
                  + Submit
                </Link>
                <details className="lg:hidden">
                  <summary className="cursor-pointer text-sm font-medium text-primary select-none">
                    Filters
                  </summary>
                  <div className="mt-3 border rounded-lg p-4 bg-card">
                    <FilterSidebar />
                  </div>
                </details>
              </div>
            </div>

            <ProblemFeed />
          </section>

          {/* Right sidebar: trending */}
          <aside className="hidden lg:block">
            <div className="sticky top-24 max-h-[calc(100vh-6rem)] overflow-y-auto pb-4">
              <TrendingTopics />
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
