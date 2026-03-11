'use client';

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User } from '@/types';
import { setApiToken } from '@/lib/api';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  setAuth: (user: User, token: string) => void;
  clearAuth: () => void;
}

// Use sessionStorage instead of localStorage:
// - Token is cleared when the browser session ends (tab/window closed)
// - Reduces XSS persistence window compared to localStorage
// - Does not persist across browser restarts
const sessionStorage_ = createJSONStorage(() =>
  typeof window !== 'undefined' ? sessionStorage : (undefined as unknown as Storage),
);

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,

      setAuth: (user: User, token: string) => {
        setApiToken(token);
        set({ user, token, isAuthenticated: true });
      },

      clearAuth: () => {
        setApiToken(null);
        set({ user: null, token: null, isAuthenticated: false });
      },
    }),
    {
      name: 'auth-storage',
      storage: sessionStorage_,
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        if (state?.token) {
          setApiToken(state.token);
        }
      },
    },
  ),
);
