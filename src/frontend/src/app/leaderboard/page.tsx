'use client';

import { useState, useEffect } from 'react';
import { getLeaderboard } from '@/lib/api';
import Link from 'next/link';
import { BackButton } from '@/components/ui/BackButton';

type LeaderboardType = 'problems' | 'solutions' | 'categories';
type Period = '24h' | '7d' | '30d';

export default function LeaderboardPage() {
  const [type, setType] = useState<LeaderboardType>('problems');
  const [period, setPeriod] = useState<Period>('7d');
  const [data, setData] = useState<{ items?: { id?: string; problem_id?: string; category?: string; rank: number; title?: string; provider?: string; score?: number; count?: number }[] } | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getLeaderboard(type, period)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [type, period]);

  return (
    <div className="max-w-3xl mx-auto p-6">
      <BackButton />
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Leaderboard</h1>
        <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">Top content by engagement</p>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          {(['problems', 'solutions', 'categories'] as LeaderboardType[]).map(t => (
            <button
              key={t}
              onClick={() => setType(t)}
              className={`px-3 py-1.5 text-sm rounded-md capitalize transition-colors ${
                type === t
                  ? 'bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-white font-medium'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1">
          {(['24h', '7d', '30d'] as Period[]).map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                period === p
                  ? 'bg-white dark:bg-gray-700 shadow text-gray-900 dark:text-white font-medium'
                  : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200'
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="space-y-3">
          {[...Array(10)].map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 dark:bg-gray-800 rounded-lg animate-pulse" />
          ))}
        </div>
      ) : !data?.items?.length ? (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400">
          No data available for this period.
        </div>
      ) : (
        <div className="space-y-2">
          {data.items.map((item, idx) => (
            <div
              key={item.id || item.category || idx}
              className="flex items-center gap-4 p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl hover:border-blue-300 dark:hover:border-blue-600 transition-colors"
            >
              <span className={`w-8 h-8 flex items-center justify-center rounded-full text-sm font-bold ${
                idx === 0 ? 'bg-yellow-100 text-yellow-600' :
                idx === 1 ? 'bg-gray-100 text-gray-600' :
                idx === 2 ? 'bg-orange-100 text-orange-600' :
                'bg-gray-50 text-gray-500'
              } dark:bg-opacity-20`}>
                {item.rank}
              </span>
              <div className="flex-1 min-w-0">
                {type === 'categories' ? (
                  <p className="font-medium text-gray-900 dark:text-white capitalize">{item.category}</p>
                ) : item.id ? (
                  <Link href={type === 'problems' ? `/problems/${item.id}` : `/problems/${item.problem_id}`}>
                    <p className="font-medium text-gray-900 dark:text-white truncate hover:text-blue-600 dark:hover:text-blue-400">
                      {item.title || `${item.provider} solution`}
                    </p>
                  </Link>
                ) : null}
                {item.category && type !== 'categories' && (
                  <p className="text-xs text-gray-500 dark:text-gray-400">{item.category}</p>
                )}
              </div>
              <div className="text-right flex-shrink-0">
                <span className="text-sm font-semibold text-blue-600 dark:text-blue-400">
                  {type === 'categories' ? item.count : item.score}
                </span>
                <p className="text-xs text-gray-400">{type === 'categories' ? 'problems' : 'score'}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
