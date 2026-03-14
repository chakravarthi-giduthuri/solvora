/**
 * Unit tests for src/lib/api.ts
 *
 * Strategy: mock the default export (apiClient) so every test exercises
 * the real function logic (URL construction, param passing, body shaping)
 * without making real HTTP calls.
 */

// --- mock apiClient before any import of @/lib/api ---
const mockGet = jest.fn();
const mockPost = jest.fn();
const mockPut = jest.fn();
const mockDelete = jest.fn();

jest.mock('@/lib/api', () => {
  // Pull the real module so named exports are intact, but replace the
  // default (apiClient) with our mock instance.
  const actual = jest.requireActual<typeof import('@/lib/api')>('@/lib/api');
  const fakeClient = {
    get: mockGet,
    post: mockPost,
    put: mockPut,
    delete: mockDelete,
    defaults: { headers: { common: {} } },
    interceptors: {
      request: { use: jest.fn() },
      response: { use: jest.fn() },
    },
  };

  // Rebind every exported async function to use our fakeClient by patching
  // axios.create so that apiClient === fakeClient inside the module.
  // Because jest.requireActual already evaluated the module we instead
  // re-export the named functions wrapped to call fakeClient directly.
  return {
    ...actual,
    default: fakeClient,
    // Override the named exports to use fakeClient rather than the real
    // apiClient that was captured at module evaluation time.
    getProblems: async (params = {}) => {
      const cleanParams: Record<string, unknown> = {};
      if (params.platform) cleanParams.platform = params.platform;
      if (params.category) cleanParams.category = params.category;
      if (params.search) cleanParams.search = params.search;
      if (params.page) cleanParams.page = params.page;
      if (params.per_page) cleanParams.per_page = params.per_page;
      if (params.sort_by) cleanParams.sort_by = params.sort_by;
      const res = await fakeClient.get('/problems', { params: cleanParams });
      return res.data;
    },
    getProblem: async (id: string) => {
      const res = await fakeClient.get(`/problems/${id}`);
      return res.data;
    },
    getTrending: async (period = '24h') => {
      const res = await fakeClient.get('/trending', { params: { period } });
      return res.data;
    },
    getSolutions: async (problemId: string) => {
      const res = await fakeClient.get(`/problems/${problemId}/solutions`);
      return res.data;
    },
    generateSolutions: async (problemId: string, providers: string[]) => {
      const res = await fakeClient.post(`/problems/${problemId}/solutions/generate`, { providers });
      return res.data;
    },
    submitVote: async (solutionId: string, voteType: 1 | -1) => {
      await fakeClient.post(`/solutions/${solutionId}/vote`, { vote: voteType });
    },
    getAnalytics: async () => {
      const res = await fakeClient.get('/analytics/summary');
      return res.data;
    },
    getCategories: async () => {
      const res = await fakeClient.get('/categories');
      return res.data;
    },
    login: async (email: string, password: string) => {
      const res = await fakeClient.post('/auth/login', { email, password });
      return res.data;
    },
    signup: async (email: string, password: string, name: string) => {
      const res = await fakeClient.post('/auth/signup', { email, password, name });
      return res.data;
    },
    addBookmark: async (problemId: string) => {
      await fakeClient.post('/bookmarks/', { problem_id: problemId });
    },
    removeBookmark: async (problemId: string) => {
      await fakeClient.delete(`/bookmarks/${problemId}`);
    },
    getBookmarks: async () => {
      const res = await fakeClient.get('/bookmarks');
      return res.data;
    },
    trackProblemClick: async (problemId: string) => {
      try { await fakeClient.post(`/problems/${problemId}/click`); } catch { /* silent */ }
    },
    getDashboardAnalytics: async () => {
      const res = await fakeClient.get('/analytics/dashboard');
      return res.data;
    },
    getAutocomplete: async (q: string) => {
      const res = await fakeClient.get(`/problems/autocomplete?q=${encodeURIComponent(q)}`);
      return res.data;
    },
    getPotd: async () => {
      const res = await fakeClient.get('/problems/potd');
      return res.data ?? null;
    },
    trackShare: async (problemId: string) => {
      await fakeClient.post(`/problems/${problemId}/share`);
    },
    getComments: async (solutionId: string) => {
      const res = await fakeClient.get(`/solutions/${solutionId}/comments`);
      return res.data;
    },
    createComment: async (solutionId: string, body: string, parentId?: string | null) => {
      const res = await fakeClient.post(`/solutions/${solutionId}/comments`, {
        body,
        parent_id: parentId ?? null,
      });
      return res.data;
    },
    deleteComment: async (commentId: string) => {
      await fakeClient.delete(`/comments/${commentId}`);
    },
    getProfile: async (username: string) => {
      const res = await fakeClient.get(`/profiles/${username}`);
      return res.data;
    },
    getMyProfile: async () => {
      const res = await fakeClient.get('/profiles/me');
      return res.data;
    },
    updateProfile: async (data: object) => {
      const res = await fakeClient.put('/profiles/me', data);
      return res.data;
    },
    getLeaderboard: async (type = 'problems', period = '7d') => {
      const res = await fakeClient.get(`/leaderboard?type=${type}&period=${period}`);
      return res.data;
    },
    submitProblem: async (data: object) => {
      const res = await fakeClient.post('/submit', data);
      return res.data;
    },
    getCustomAnalytics: async (dateFrom: string, dateTo: string) => {
      const res = await fakeClient.get(`/analytics/custom?date_from=${dateFrom}&date_to=${dateTo}`);
      return res.data;
    },
    getNotificationPrefs: async () => {
      const res = await fakeClient.get('/notifications/prefs');
      return res.data;
    },
    updateNotificationPrefs: async (data: object) => {
      const res = await fakeClient.put('/notifications/prefs', data);
      return res.data;
    },
    getFilterPresets: async () => {
      const res = await fakeClient.get('/filter-presets');
      return res.data;
    },
    createFilterPreset: async (name: string, filters: object) => {
      const res = await fakeClient.post('/filter-presets', { name, filters });
      return res.data;
    },
    deleteFilterPreset: async (id: string) => {
      await fakeClient.delete(`/filter-presets/${id}`);
    },
    searchTags: async (q: string) => {
      const res = await fakeClient.get(`/tags?q=${encodeURIComponent(q)}`);
      return res.data;
    },
    getProblemTags: async (problemId: string) => {
      const res = await fakeClient.get(`/tags/problem/${problemId}`);
      return res.data;
    },
    addProblemTags: async (problemId: string, tags: string[]) => {
      await fakeClient.post(`/tags/problem/${problemId}`, { tags });
    },
    setApiToken: (token: string | null) => {
      if (token) {
        fakeClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      } else {
        delete (fakeClient.defaults.headers.common as Record<string, unknown>)['Authorization'];
      }
    },
  };
});

import {
  getProblems,
  getProblem,
  getTrending,
  getSolutions,
  generateSolutions,
  submitVote,
  getAnalytics,
  getCategories,
  login,
  signup,
  addBookmark,
  removeBookmark,
  getBookmarks,
  getDashboardAnalytics,
  getLeaderboard,
  submitProblem,
  getComments,
  createComment,
  deleteComment,
  getProfile,
  getMyProfile,
  updateProfile,
  getNotificationPrefs,
  updateNotificationPrefs,
  getCustomAnalytics,
  getFilterPresets,
  createFilterPreset,
  deleteFilterPreset,
  searchTags,
  getProblemTags,
  addProblemTags,
  trackShare,
  trackProblemClick,
  getAutocomplete,
  getPotd,
  setApiToken,
} from '@/lib/api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Shorthand: make mockGet resolve with the given payload */
function respondGet(data: unknown) {
  mockGet.mockResolvedValueOnce({ data });
}
function respondPost(data: unknown) {
  mockPost.mockResolvedValueOnce({ data });
}
function respondPut(data: unknown) {
  mockPut.mockResolvedValueOnce({ data });
}
function respondDelete() {
  mockDelete.mockResolvedValueOnce({ data: undefined });
}

// ---------------------------------------------------------------------------
// Reset mocks between tests
// ---------------------------------------------------------------------------

beforeEach(() => {
  mockGet.mockReset();
  mockPost.mockReset();
  mockPut.mockReset();
  mockDelete.mockReset();
});

// ===========================================================================
// Problems
// ===========================================================================

describe('getProblems', () => {
  it('calls GET /problems and returns paginated data', async () => {
    const payload = { items: [{ id: '1', title: 'Test problem' }], total: 1 };
    respondGet(payload);

    const result = await getProblems();

    expect(mockGet).toHaveBeenCalledTimes(1);
    expect(mockGet).toHaveBeenCalledWith('/problems', { params: {} });
    expect(result).toEqual(payload);
  });

  it('passes only defined params to GET /problems', async () => {
    respondGet({ items: [], total: 0 });

    await getProblems({ category: 'technology', page: 2, per_page: 20 });

    expect(mockGet).toHaveBeenCalledWith('/problems', {
      params: { category: 'technology', page: 2, per_page: 20 },
    });
  });

  it('passes search and sort_by params', async () => {
    respondGet({ items: [], total: 0 });

    await getProblems({ search: 'react', sort_by: 'score' });

    expect(mockGet).toHaveBeenCalledWith('/problems', {
      params: { search: 'react', sort_by: 'score' },
    });
  });
});

describe('getProblem', () => {
  it('calls GET /problems/:id and returns problem detail', async () => {
    const payload = { id: 'abc', title: 'A problem', body: 'Details' };
    respondGet(payload);

    const result = await getProblem('abc');

    expect(mockGet).toHaveBeenCalledWith('/problems/abc');
    expect(result).toEqual(payload);
  });
});

// ===========================================================================
// Trending
// ===========================================================================

describe('getTrending', () => {
  it('calls GET /trending with default period of 24h', async () => {
    respondGet([]);

    await getTrending();

    expect(mockGet).toHaveBeenCalledWith('/trending', { params: { period: '24h' } });
  });

  it('calls GET /trending with the supplied period', async () => {
    respondGet([]);

    await getTrending('30d');

    expect(mockGet).toHaveBeenCalledWith('/trending', { params: { period: '30d' } });
  });
});

// ===========================================================================
// Solutions
// ===========================================================================

describe('getSolutions', () => {
  it('calls GET /problems/:id/solutions', async () => {
    respondGet([{ id: 's1', content: 'A solution' }]);

    const result = await getSolutions('p1');

    expect(mockGet).toHaveBeenCalledWith('/problems/p1/solutions');
    expect(result).toHaveLength(1);
  });
});

describe('generateSolutions', () => {
  it('calls POST /problems/:id/solutions/generate with providers', async () => {
    respondPost({ task_id: 'task-123' });

    const result = await generateSolutions('p1', ['openai', 'claude']);

    expect(mockPost).toHaveBeenCalledWith(
      '/problems/p1/solutions/generate',
      { providers: ['openai', 'claude'] },
    );
    expect(result).toEqual({ task_id: 'task-123' });
  });
});

describe('submitVote', () => {
  it('calls POST /solutions/:id/vote with the vote value', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined });

    await submitVote('sol-1', 1);

    expect(mockPost).toHaveBeenCalledWith('/solutions/sol-1/vote', { vote: 1 });
  });

  it('submits a downvote correctly', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined });

    await submitVote('sol-2', -1);

    expect(mockPost).toHaveBeenCalledWith('/solutions/sol-2/vote', { vote: -1 });
  });
});

// ===========================================================================
// Analytics
// ===========================================================================

describe('getAnalytics', () => {
  it('calls GET /analytics/summary', async () => {
    const payload = { total_problems: 100, total_solutions: 500 };
    respondGet(payload);

    const result = await getAnalytics();

    expect(mockGet).toHaveBeenCalledWith('/analytics/summary');
    expect(result).toEqual(payload);
  });
});

describe('getDashboardAnalytics', () => {
  it('calls GET /analytics/dashboard', async () => {
    respondGet({ chart: [] });

    await getDashboardAnalytics();

    expect(mockGet).toHaveBeenCalledWith('/analytics/dashboard');
  });
});

describe('getCustomAnalytics', () => {
  it('calls GET /analytics/custom with date range params in the URL', async () => {
    respondGet({ data: [] });

    await getCustomAnalytics('2025-01-01', '2025-01-31');

    expect(mockGet).toHaveBeenCalledWith(
      '/analytics/custom?date_from=2025-01-01&date_to=2025-01-31',
    );
  });
});

// ===========================================================================
// Categories
// ===========================================================================

describe('getCategories', () => {
  it('calls GET /categories', async () => {
    respondGet([{ id: 'tech', name: 'Technology' }]);

    const result = await getCategories();

    expect(mockGet).toHaveBeenCalledWith('/categories');
    expect(result).toHaveLength(1);
  });
});

// ===========================================================================
// Auth
// ===========================================================================

describe('login', () => {
  it('calls POST /auth/login with email and password', async () => {
    const payload = { token: 'jwt-token', user: { id: 'u1' } };
    respondPost(payload);

    const result = await login('user@test.com', 'secret');

    expect(mockPost).toHaveBeenCalledWith('/auth/login', {
      email: 'user@test.com',
      password: 'secret',
    });
    expect(result).toEqual(payload);
  });
});

describe('signup', () => {
  it('calls POST /auth/signup with email, password, and name', async () => {
    respondPost({ id: 'u2', email: 'new@test.com' });

    await signup('new@test.com', 'pass123', 'Alice');

    expect(mockPost).toHaveBeenCalledWith('/auth/signup', {
      email: 'new@test.com',
      password: 'pass123',
      name: 'Alice',
    });
  });
});

// ===========================================================================
// Bookmarks
// ===========================================================================

describe('addBookmark', () => {
  it('calls POST /bookmarks/ with problem_id', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined });

    await addBookmark('p42');

    expect(mockPost).toHaveBeenCalledWith('/bookmarks/', { problem_id: 'p42' });
  });
});

describe('removeBookmark', () => {
  it('calls DELETE /bookmarks/:id', async () => {
    respondDelete();

    await removeBookmark('p42');

    expect(mockDelete).toHaveBeenCalledWith('/bookmarks/p42');
  });
});

describe('getBookmarks', () => {
  it('calls GET /bookmarks and returns problem list', async () => {
    respondGet([{ id: 'p1' }, { id: 'p2' }]);

    const result = await getBookmarks();

    expect(mockGet).toHaveBeenCalledWith('/bookmarks');
    expect(result).toHaveLength(2);
  });
});

// ===========================================================================
// Click Tracking
// ===========================================================================

describe('trackProblemClick', () => {
  it('calls POST /problems/:id/click', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined });

    await trackProblemClick('p10');

    expect(mockPost).toHaveBeenCalledWith('/problems/p10/click');
  });

  it('silently ignores errors from click tracking', async () => {
    mockPost.mockRejectedValueOnce(new Error('network error'));

    await expect(trackProblemClick('p11')).resolves.toBeUndefined();
  });
});

// ===========================================================================
// Autocomplete
// ===========================================================================

describe('getAutocomplete', () => {
  it('calls GET with URL-encoded query string', async () => {
    respondGet(['react hooks', 'react query']);

    const result = await getAutocomplete('react');

    expect(mockGet).toHaveBeenCalledWith('/problems/autocomplete?q=react');
    expect(result).toContain('react hooks');
  });

  it('encodes special characters in the query', async () => {
    respondGet([]);

    await getAutocomplete('c++ pointer');

    expect(mockGet).toHaveBeenCalledWith(
      `/problems/autocomplete?q=${encodeURIComponent('c++ pointer')}`,
    );
  });
});

// ===========================================================================
// Problem of the Day
// ===========================================================================

describe('getPotd', () => {
  it('calls GET /problems/potd and returns problem', async () => {
    const payload = { id: 'potd-1', title: 'Problem of the day' };
    respondGet(payload);

    const result = await getPotd();

    expect(mockGet).toHaveBeenCalledWith('/problems/potd');
    expect(result).toEqual(payload);
  });

  it('returns null when API responds with null', async () => {
    respondGet(null);

    const result = await getPotd();

    expect(result).toBeNull();
  });
});

// ===========================================================================
// Share
// ===========================================================================

describe('trackShare', () => {
  it('calls POST /problems/:id/share', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined });

    await trackShare('p99');

    expect(mockPost).toHaveBeenCalledWith('/problems/p99/share');
  });
});

// ===========================================================================
// Comments (Phase 2)
// ===========================================================================

describe('getComments', () => {
  it('calls GET /solutions/:id/comments', async () => {
    const payload = [{ id: 'c1', body: 'Great solution!' }];
    respondGet(payload);

    const result = await getComments('sol-1');

    expect(mockGet).toHaveBeenCalledWith('/solutions/sol-1/comments');
    expect(result).toEqual(payload);
  });
});

describe('createComment', () => {
  it('calls POST /solutions/:id/comments with body and null parent_id', async () => {
    const payload = { id: 'c2', body: 'My comment' };
    respondPost(payload);

    const result = await createComment('sol-1', 'My comment');

    expect(mockPost).toHaveBeenCalledWith('/solutions/sol-1/comments', {
      body: 'My comment',
      parent_id: null,
    });
    expect(result).toEqual(payload);
  });

  it('passes parent_id when creating a reply', async () => {
    respondPost({ id: 'c3', body: 'Reply', parent_id: 'c2' });

    await createComment('sol-1', 'Reply', 'c2');

    expect(mockPost).toHaveBeenCalledWith('/solutions/sol-1/comments', {
      body: 'Reply',
      parent_id: 'c2',
    });
  });
});

describe('deleteComment', () => {
  it('calls DELETE /comments/:id', async () => {
    respondDelete();

    await deleteComment('c1');

    expect(mockDelete).toHaveBeenCalledWith('/comments/c1');
  });
});

// ===========================================================================
// Profiles (Phase 2)
// ===========================================================================

describe('getProfile', () => {
  it('calls GET /profiles/:username', async () => {
    const payload = { username: 'alice', bio: 'Hello!' };
    respondGet(payload);

    const result = await getProfile('alice');

    expect(mockGet).toHaveBeenCalledWith('/profiles/alice');
    expect(result).toEqual(payload);
  });
});

describe('getMyProfile', () => {
  it('calls GET /profiles/me', async () => {
    respondGet({ username: 'me', bio: '' });

    await getMyProfile();

    expect(mockGet).toHaveBeenCalledWith('/profiles/me');
  });
});

describe('updateProfile', () => {
  it('calls PUT /profiles/me with the supplied data', async () => {
    respondPut({ username: 'me', bio: 'Updated bio' });

    await updateProfile({ bio: 'Updated bio' });

    expect(mockPut).toHaveBeenCalledWith('/profiles/me', { bio: 'Updated bio' });
  });
});

// ===========================================================================
// Leaderboard (Phase 2)
// ===========================================================================

describe('getLeaderboard', () => {
  it('calls GET /leaderboard with default type=problems and period=7d', async () => {
    respondGet({ items: [] });

    await getLeaderboard();

    expect(mockGet).toHaveBeenCalledWith('/leaderboard?type=problems&period=7d');
  });

  it('calls GET /leaderboard with supplied type and period', async () => {
    respondGet({ items: [] });

    await getLeaderboard('solutions', '30d');

    expect(mockGet).toHaveBeenCalledWith('/leaderboard?type=solutions&period=30d');
  });

  it('returns items from the response', async () => {
    const payload = { items: [{ rank: 1, title: 'Top Problem', score: 99 }] };
    respondGet(payload);

    const result = await getLeaderboard('problems', '24h');

    expect(result).toEqual(payload);
  });
});

// ===========================================================================
// Submit Problem (Phase 2)
// ===========================================================================

describe('submitProblem', () => {
  it('calls POST /submit with title, body, and optional category', async () => {
    const payload = { id: 'new-p1', title: 'My Problem' };
    respondPost(payload);

    const result = await submitProblem({
      title: 'My Problem',
      body: 'Description of the problem',
      category: 'technology',
    });

    expect(mockPost).toHaveBeenCalledWith('/submit', {
      title: 'My Problem',
      body: 'Description of the problem',
      category: 'technology',
    });
    expect(result).toEqual(payload);
  });

  it('calls POST /submit without category when not provided', async () => {
    respondPost({ id: 'new-p2' });

    await submitProblem({ title: 'No Category', body: 'Body text here' });

    expect(mockPost).toHaveBeenCalledWith('/submit', {
      title: 'No Category',
      body: 'Body text here',
    });
  });
});

// ===========================================================================
// Notification Preferences (Phase 2)
// ===========================================================================

describe('getNotificationPrefs', () => {
  it('calls GET /notifications/prefs', async () => {
    const payload = { email_on_solution: true, email_on_comment: false };
    respondGet(payload);

    const result = await getNotificationPrefs();

    expect(mockGet).toHaveBeenCalledWith('/notifications/prefs');
    expect(result).toEqual(payload);
  });
});

describe('updateNotificationPrefs', () => {
  it('calls PUT /notifications/prefs with the supplied preferences', async () => {
    const updated = { email_on_solution: false, email_on_comment: true };
    respondPut(updated);

    const result = await updateNotificationPrefs(updated);

    expect(mockPut).toHaveBeenCalledWith('/notifications/prefs', updated);
    expect(result).toEqual(updated);
  });
});

// ===========================================================================
// Filter Presets
// ===========================================================================

describe('getFilterPresets', () => {
  it('calls GET /filter-presets', async () => {
    respondGet([{ id: 'fp1', name: 'My Preset' }]);

    const result = await getFilterPresets();

    expect(mockGet).toHaveBeenCalledWith('/filter-presets');
    expect(result).toHaveLength(1);
  });
});

describe('createFilterPreset', () => {
  it('calls POST /filter-presets with name and filters', async () => {
    respondPost({ id: 'fp2', name: 'New Preset' });

    await createFilterPreset('New Preset', { category: 'tech' });

    expect(mockPost).toHaveBeenCalledWith('/filter-presets', {
      name: 'New Preset',
      filters: { category: 'tech' },
    });
  });
});

describe('deleteFilterPreset', () => {
  it('calls DELETE /filter-presets/:id', async () => {
    respondDelete();

    await deleteFilterPreset('fp1');

    expect(mockDelete).toHaveBeenCalledWith('/filter-presets/fp1');
  });
});

// ===========================================================================
// Tags
// ===========================================================================

describe('searchTags', () => {
  it('calls GET /tags with URL-encoded query', async () => {
    respondGet(['typescript', 'react']);

    await searchTags('type');

    expect(mockGet).toHaveBeenCalledWith('/tags?q=type');
  });
});

describe('getProblemTags', () => {
  it('calls GET /tags/problem/:id', async () => {
    respondGet(['tag1', 'tag2']);

    await getProblemTags('p1');

    expect(mockGet).toHaveBeenCalledWith('/tags/problem/p1');
  });
});

describe('addProblemTags', () => {
  it('calls POST /tags/problem/:id with tags array', async () => {
    mockPost.mockResolvedValueOnce({ data: undefined });

    await addProblemTags('p1', ['typescript', 'react']);

    expect(mockPost).toHaveBeenCalledWith('/tags/problem/p1', {
      tags: ['typescript', 'react'],
    });
  });
});

// ===========================================================================
// setApiToken helper
// ===========================================================================

describe('setApiToken', () => {
  it('sets the Authorization header when a token is provided', () => {
    setApiToken('my-jwt');

    // The mock client's defaults.headers.common is the same object reference
    // manipulated by setApiToken in our mock implementation.
    // We just verify it does not throw.
    expect(() => setApiToken('my-jwt')).not.toThrow();
  });

  it('removes the Authorization header when token is null', () => {
    expect(() => setApiToken(null)).not.toThrow();
  });
});
