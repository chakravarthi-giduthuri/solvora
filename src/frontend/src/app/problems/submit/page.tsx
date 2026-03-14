'use client';

import { useState } from 'react';
import { useSession } from 'next-auth/react';
import { useRouter } from 'next/navigation';
import { submitProblem } from '@/lib/api';

export default function SubmitProblemPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [category, setCategory] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (status === 'loading') return <div className="p-8 text-center">Loading...</div>;
  if (!session) {
    return (
      <div className="p-8 text-center">
        <p className="text-gray-600 dark:text-gray-400">Please sign in to submit a problem.</p>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (title.length < 10) { setError('Title must be at least 10 characters'); return; }
    if (body.length < 20) { setError('Description must be at least 20 characters'); return; }
    setSubmitting(true);
    try {
      const result = await submitProblem(
        { title, body, category: category || undefined },
      );
      router.push(`/problems/${result.id}`);
    } catch (err: unknown) {
      setError((err as Error).message || 'Failed to submit problem');
    }
    setSubmitting(false);
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Submit a Problem</h1>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Share a problem you&apos;re facing and get AI-powered solutions.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        {error && (
          <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Title *
          </label>
          <input
            type="text"
            value={title}
            onChange={e => setTitle(e.target.value)}
            placeholder="Briefly describe your problem..."
            className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
            minLength={10}
            maxLength={512}
            required
          />
          <p className="mt-1 text-xs text-gray-400">{title.length}/512</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Description *
          </label>
          <textarea
            value={body}
            onChange={e => setBody(e.target.value)}
            placeholder="Describe your problem in detail. Include what you've already tried..."
            className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none resize-y"
            rows={8}
            minLength={20}
            required
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
            Category (optional)
          </label>
          <select
            value={category}
            onChange={e => setCategory(e.target.value)}
            className="w-full p-3 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 outline-none"
          >
            <option value="">Select a category...</option>
            <option value="technology">Technology</option>
            <option value="programming">Programming</option>
            <option value="productivity">Productivity</option>
            <option value="career">Career</option>
            <option value="other">Other</option>
          </select>
        </div>

        <button
          type="submit"
          disabled={submitting}
          className="w-full py-3 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white font-medium rounded-lg transition-colors"
        >
          {submitting ? 'Submitting...' : 'Submit Problem'}
        </button>
      </form>
    </div>
  );
}
