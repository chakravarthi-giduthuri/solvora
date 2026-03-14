/**
 * Tests for src/app/leaderboard/page.tsx
 *
 * The page uses getLeaderboard() from @/lib/api, which we mock entirely.
 * next/navigation and next/link are also mocked to avoid Next.js-specific
 * runtime dependencies in the jsdom test environment.
 */

import React from 'react';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// ---------------------------------------------------------------------------
// Mock next/navigation (useRouter, usePathname)
// ---------------------------------------------------------------------------
jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), prefetch: jest.fn(), replace: jest.fn() }),
  usePathname: () => '/leaderboard',
  useSearchParams: () => new URLSearchParams(),
}));

// ---------------------------------------------------------------------------
// Mock next/link
// ---------------------------------------------------------------------------
jest.mock('next/link', () => {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  return function MockLink({ href, children }: { href: string; children: React.ReactNode }) {
    return <a href={href}>{children}</a>;
  };
});

// ---------------------------------------------------------------------------
// Mock @/lib/api — only getLeaderboard is used by this page
// ---------------------------------------------------------------------------
jest.mock('@/lib/api', () => ({
  getLeaderboard: jest.fn(),
}));

import { getLeaderboard } from '@/lib/api';
import LeaderboardPage from '@/app/leaderboard/page';

// ---------------------------------------------------------------------------
// Typed mock helpers
// ---------------------------------------------------------------------------

const mockGetLeaderboard = getLeaderboard as jest.MockedFunction<typeof getLeaderboard>;

const makeItems = (count: number) =>
  Array.from({ length: count }, (_, i) => ({
    rank: i + 1,
    id: `problem-${i + 1}`,
    title: `Problem title number ${i + 1}`,
    category: 'technology',
    score: 100 - i * 5,
  }));

// ---------------------------------------------------------------------------
// Setup / teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  mockGetLeaderboard.mockResolvedValue({
    items: makeItems(3),
    type: 'problems',
    period: '7d',
    generated_at: new Date().toISOString(),
  });
});

afterEach(() => {
  jest.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Heading / static content
// ---------------------------------------------------------------------------

describe('LeaderboardPage — static structure', () => {
  it('renders the Leaderboard heading', () => {
    render(<LeaderboardPage />);
    expect(screen.getByText('Leaderboard')).toBeInTheDocument();
  });

  it('renders all three type tabs', () => {
    render(<LeaderboardPage />);
    expect(screen.getByText('problems')).toBeInTheDocument();
    expect(screen.getByText('solutions')).toBeInTheDocument();
    expect(screen.getByText('categories')).toBeInTheDocument();
  });

  it('renders all three period tabs', () => {
    render(<LeaderboardPage />);
    expect(screen.getByText('24h')).toBeInTheDocument();
    expect(screen.getByText('7d')).toBeInTheDocument();
    expect(screen.getByText('30d')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Data loading
// ---------------------------------------------------------------------------

describe('LeaderboardPage — data loading', () => {
  it('calls getLeaderboard with default type=problems and period=7d on mount', async () => {
    render(<LeaderboardPage />);
    await waitFor(() => expect(mockGetLeaderboard).toHaveBeenCalledWith('problems', '7d'));
  });

  it('displays leaderboard items after loading completes', async () => {
    render(<LeaderboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Problem title number 1')).toBeInTheDocument();
    });
  });

  it('displays all returned items', async () => {
    render(<LeaderboardPage />);
    await waitFor(() => {
      expect(screen.getByText('Problem title number 1')).toBeInTheDocument();
      expect(screen.getByText('Problem title number 2')).toBeInTheDocument();
      expect(screen.getByText('Problem title number 3')).toBeInTheDocument();
    });
  });

  it('shows an empty-state message when items list is empty', async () => {
    mockGetLeaderboard.mockResolvedValueOnce({
      items: [],
      type: 'problems',
      period: '7d',
      generated_at: new Date().toISOString(),
    });
    render(<LeaderboardPage />);
    await waitFor(() => {
      expect(screen.getByText(/no data available/i)).toBeInTheDocument();
    });
  });
});

// ---------------------------------------------------------------------------
// Period tab interactions
// ---------------------------------------------------------------------------

describe('LeaderboardPage — period tab switching', () => {
  it('calls getLeaderboard with period=30d when the 30d tab is clicked', async () => {
    render(<LeaderboardPage />);
    // Wait for initial load
    await waitFor(() => expect(mockGetLeaderboard).toHaveBeenCalledTimes(1));

    mockGetLeaderboard.mockResolvedValueOnce({
      items: makeItems(1),
      type: 'problems',
      period: '30d',
      generated_at: new Date().toISOString(),
    });

    await act(async () => {
      fireEvent.click(screen.getByText('30d'));
    });

    await waitFor(() => {
      expect(mockGetLeaderboard).toHaveBeenCalledWith('problems', '30d');
    });
  });

  it('calls getLeaderboard with period=24h when the 24h tab is clicked', async () => {
    render(<LeaderboardPage />);
    await waitFor(() => expect(mockGetLeaderboard).toHaveBeenCalledTimes(1));

    mockGetLeaderboard.mockResolvedValueOnce({
      items: makeItems(2),
      type: 'problems',
      period: '24h',
      generated_at: new Date().toISOString(),
    });

    await act(async () => {
      fireEvent.click(screen.getByText('24h'));
    });

    await waitFor(() => {
      expect(mockGetLeaderboard).toHaveBeenCalledWith('problems', '24h');
    });
  });
});

// ---------------------------------------------------------------------------
// Type tab interactions
// ---------------------------------------------------------------------------

describe('LeaderboardPage — type tab switching', () => {
  it('calls getLeaderboard with type=solutions when the solutions tab is clicked', async () => {
    render(<LeaderboardPage />);
    await waitFor(() => expect(mockGetLeaderboard).toHaveBeenCalledTimes(1));

    mockGetLeaderboard.mockResolvedValueOnce({
      items: [{ rank: 1, id: 'sol-1', provider: 'gemini', score: 50 }],
      type: 'solutions',
      period: '7d',
      generated_at: new Date().toISOString(),
    });

    await act(async () => {
      fireEvent.click(screen.getByText('solutions'));
    });

    await waitFor(() => {
      expect(mockGetLeaderboard).toHaveBeenCalledWith('solutions', '7d');
    });
  });

  it('calls getLeaderboard with type=categories when the categories tab is clicked', async () => {
    render(<LeaderboardPage />);
    await waitFor(() => expect(mockGetLeaderboard).toHaveBeenCalledTimes(1));

    mockGetLeaderboard.mockResolvedValueOnce({
      items: [{ rank: 1, category: 'technology', count: 20 }],
      type: 'categories',
      period: '7d',
      generated_at: new Date().toISOString(),
    });

    await act(async () => {
      fireEvent.click(screen.getByText('categories'));
    });

    await waitFor(() => {
      expect(mockGetLeaderboard).toHaveBeenCalledWith('categories', '7d');
    });
  });
});

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------

describe('LeaderboardPage — error handling', () => {
  it('does not crash when getLeaderboard rejects', async () => {
    mockGetLeaderboard.mockRejectedValueOnce(new Error('Network error'));

    expect(() => render(<LeaderboardPage />)).not.toThrow();
    // After the error the empty state or loading state should be shown without crashing
    await waitFor(() => {
      // Page should still be in the document (no crash)
      expect(screen.getByText('Leaderboard')).toBeInTheDocument();
    });
  });
});
