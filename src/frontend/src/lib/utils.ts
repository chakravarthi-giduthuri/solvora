import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { formatDistanceToNow, parseISO } from 'date-fns';
import type { Sentiment, Platform } from '@/types';

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatRelativeTime(dateString: string): string {
  try {
    return formatDistanceToNow(parseISO(dateString), { addSuffix: true });
  } catch {
    return dateString;
  }
}

export function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength).trimEnd()}…`;
}

export const SENTIMENT_LABELS: Record<Sentiment, string> = {
  urgent: 'Urgent',
  frustrated: 'Frustrated',
  curious: 'Curious',
  neutral: 'Neutral',
};

export const SENTIMENT_COLORS: Record<Sentiment, string> = {
  urgent: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  frustrated:
    'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  curious: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  neutral: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
};

export const SENTIMENT_HEX: Record<Sentiment, string> = {
  urgent: '#EF4444',
  frustrated: '#F97316',
  curious: '#3B82F6',
  neutral: '#6B7280',
};

export const PLATFORM_LABELS: Record<Platform, string> = {
  reddit: 'Reddit',
  hackernews: 'Hacker News',
};

export const CATEGORY_COLORS: string[] = [
  'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
  'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
];

export function getCategoryColor(index: number): string {
  return CATEGORY_COLORS[index % CATEGORY_COLORS.length];
}

// Markdown-to-HTML with XSS protection:
// 1. Escapes all HTML special chars (including quotes) before injecting any tags
// 2. Link URLs are validated via URL constructor and must be http/https only
// 3. Attribute injection is prevented by escaping " before regex substitutions
export function renderMarkdown(text: string): string {
  const escaped = text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  return escaped
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/`(.+?)`/g, '<code class="bg-muted px-1 rounded text-sm">$1</code>')
    .replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)&"'<>]+)\)/g,
      (_, linkText, url) => {
        try {
          const parsed = new URL(url);
          if (parsed.protocol !== 'https:' && parsed.protocol !== 'http:') return linkText;
          return `<a href="${parsed.href}" class="text-primary underline" target="_blank" rel="noopener noreferrer">${linkText}</a>`;
        } catch {
          return linkText; // Invalid URL — render as plain text
        }
      },
    )
    .replace(/\n/g, '<br />');
}
