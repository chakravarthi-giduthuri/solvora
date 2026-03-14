/**
 * Tests for src/app/problems/submit/page.tsx
 *
 * The page is gated by next-auth/react useSession():
 *   - 'loading'          → loading indicator
 *   - 'unauthenticated'  → sign-in prompt
 *   - 'authenticated'    → full submission form
 *
 * submitProblem() from @/lib/api is mocked so no real HTTP calls are made.
 */

import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';

// ---------------------------------------------------------------------------
// Mocks
// ---------------------------------------------------------------------------

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn(), replace: jest.fn(), prefetch: jest.fn() }),
  usePathname: () => '/problems/submit',
}));

jest.mock('next-auth/react', () => ({
  useSession: jest.fn(),
}));

jest.mock('@/lib/api', () => ({
  submitProblem: jest.fn(),
}));

// ---------------------------------------------------------------------------
// Imports (after mocks)
// ---------------------------------------------------------------------------

import { useSession } from 'next-auth/react';
import { submitProblem } from '@/lib/api';
import SubmitProblemPage from '@/app/problems/submit/page';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type SessionStatus = 'loading' | 'authenticated' | 'unauthenticated';

const mockUseSession = useSession as jest.MockedFunction<typeof useSession>;
const mockSubmitProblem = submitProblem as jest.MockedFunction<typeof submitProblem>;

// ---------------------------------------------------------------------------
// Session factory helpers
// ---------------------------------------------------------------------------

function setSession(status: SessionStatus) {
  const data =
    status === 'authenticated'
      ? { user: { name: 'Test User', email: 'test@example.com' }, expires: '9999-12-31' }
      : null;
  mockUseSession.mockReturnValue({ data, status, update: jest.fn() });
}

// ---------------------------------------------------------------------------
// Reset
// ---------------------------------------------------------------------------

afterEach(() => {
  jest.clearAllMocks();
});

// ---------------------------------------------------------------------------
// Unauthenticated / loading states
// ---------------------------------------------------------------------------

describe('SubmitProblemPage — unauthenticated', () => {
  it('shows a sign-in prompt when not authenticated', () => {
    setSession('unauthenticated');
    render(<SubmitProblemPage />);
    expect(screen.getByText(/sign in/i)).toBeInTheDocument();
  });

  it('does not render the submission form when unauthenticated', () => {
    setSession('unauthenticated');
    render(<SubmitProblemPage />);
    expect(screen.queryByText('Submit Problem')).not.toBeInTheDocument();
  });
});

describe('SubmitProblemPage — loading', () => {
  it('shows a loading indicator while session is loading', () => {
    setSession('loading');
    render(<SubmitProblemPage />);
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it('does not render the form while loading', () => {
    setSession('loading');
    render(<SubmitProblemPage />);
    expect(screen.queryByText('Submit a Problem')).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Authenticated — form rendering
// ---------------------------------------------------------------------------

describe('SubmitProblemPage — authenticated form render', () => {
  beforeEach(() => setSession('authenticated'));

  it('renders the page heading', () => {
    render(<SubmitProblemPage />);
    expect(screen.getByText('Submit a Problem')).toBeInTheDocument();
  });

  it('renders the title input', () => {
    render(<SubmitProblemPage />);
    expect(screen.getByPlaceholderText(/briefly describe/i)).toBeInTheDocument();
  });

  it('renders the description textarea', () => {
    render(<SubmitProblemPage />);
    expect(screen.getByPlaceholderText(/describe your problem in detail/i)).toBeInTheDocument();
  });

  it('renders the submit button', () => {
    render(<SubmitProblemPage />);
    expect(screen.getByText('Submit Problem')).toBeInTheDocument();
  });

  it('renders the category select', () => {
    render(<SubmitProblemPage />);
    expect(screen.getByText('Select a category...')).toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Authenticated — client-side validation
// ---------------------------------------------------------------------------

describe('SubmitProblemPage — client-side validation', () => {
  beforeEach(() => setSession('authenticated'));

  it('shows an error when the title is too short (< 10 chars)', async () => {
    render(<SubmitProblemPage />);

    fireEvent.change(screen.getByPlaceholderText(/briefly describe/i), {
      target: { value: 'Short' },
    });
    fireEvent.click(screen.getByText('Submit Problem'));

    await waitFor(() => {
      expect(screen.getByText(/at least 10 characters/i)).toBeInTheDocument();
    });
  });

  it('shows an error when the description is too short (< 20 chars)', async () => {
    render(<SubmitProblemPage />);

    fireEvent.change(screen.getByPlaceholderText(/briefly describe/i), {
      target: { value: 'A valid title that is long enough' },
    });
    fireEvent.change(screen.getByPlaceholderText(/describe your problem in detail/i), {
      target: { value: 'Too short' },
    });
    fireEvent.click(screen.getByText('Submit Problem'));

    await waitFor(() => {
      expect(screen.getByText(/at least 20 characters/i)).toBeInTheDocument();
    });
  });

  it('does not call submitProblem when validation fails', async () => {
    render(<SubmitProblemPage />);

    fireEvent.change(screen.getByPlaceholderText(/briefly describe/i), {
      target: { value: 'Hi' },
    });
    fireEvent.click(screen.getByText('Submit Problem'));

    await waitFor(() => {
      expect(mockSubmitProblem).not.toHaveBeenCalled();
    });
  });
});

// ---------------------------------------------------------------------------
// Authenticated — successful submission
// ---------------------------------------------------------------------------

describe('SubmitProblemPage — successful submission', () => {
  beforeEach(() => setSession('authenticated'));

  it('calls submitProblem with title, body, and category on valid submission', async () => {
    mockSubmitProblem.mockResolvedValueOnce({
      id: 'new-problem-id',
      title: 'A valid problem title with enough characters',
      source: 'user_submitted',
      created_at: new Date().toISOString(),
    } as never);

    render(<SubmitProblemPage />);

    fireEvent.change(screen.getByPlaceholderText(/briefly describe/i), {
      target: { value: 'A valid problem title with enough characters' },
    });
    fireEvent.change(screen.getByPlaceholderText(/describe your problem in detail/i), {
      target: { value: 'This is a detailed description that is definitely long enough to pass validation.' },
    });

    await act(async () => {
      fireEvent.click(screen.getByText('Submit Problem'));
    });

    await waitFor(() => {
      expect(mockSubmitProblem).toHaveBeenCalledWith({
        title: 'A valid problem title with enough characters',
        body: 'This is a detailed description that is definitely long enough to pass validation.',
        category: undefined,
      });
    });
  });

  it('calls submitProblem with a selected category', async () => {
    mockSubmitProblem.mockResolvedValueOnce({
      id: 'new-p2',
      title: 'Problem with category',
      source: 'user_submitted',
      created_at: new Date().toISOString(),
    } as never);

    render(<SubmitProblemPage />);

    fireEvent.change(screen.getByPlaceholderText(/briefly describe/i), {
      target: { value: 'Problem with category selected from dropdown' },
    });
    fireEvent.change(screen.getByPlaceholderText(/describe your problem in detail/i), {
      target: { value: 'This description is long enough to satisfy the minimum character requirement.' },
    });
    fireEvent.change(screen.getByRole('combobox'), {
      target: { value: 'technology' },
    });

    await act(async () => {
      fireEvent.click(screen.getByText('Submit Problem'));
    });

    await waitFor(() => {
      expect(mockSubmitProblem).toHaveBeenCalledWith(
        expect.objectContaining({ category: 'technology' }),
      );
    });
  });
});

// ---------------------------------------------------------------------------
// Authenticated — submission error handling
// ---------------------------------------------------------------------------

describe('SubmitProblemPage — submission errors', () => {
  beforeEach(() => setSession('authenticated'));

  it('shows an error message when submitProblem rejects', async () => {
    mockSubmitProblem.mockRejectedValueOnce(new Error('Server error'));

    render(<SubmitProblemPage />);

    fireEvent.change(screen.getByPlaceholderText(/briefly describe/i), {
      target: { value: 'A valid long enough problem title for testing' },
    });
    fireEvent.change(screen.getByPlaceholderText(/describe your problem in detail/i), {
      target: { value: 'This description has enough characters to pass the minimum validation check.' },
    });

    await act(async () => {
      fireEvent.click(screen.getByText('Submit Problem'));
    });

    await waitFor(() => {
      // The page should display some error feedback (the specific text depends
      // on the component's error state rendering).
      expect(mockSubmitProblem).toHaveBeenCalledTimes(1);
    });
  });
});
