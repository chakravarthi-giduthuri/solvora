'use client';

import { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SessionProvider, useSession } from 'next-auth/react';
import { ToastProvider, ToastViewport } from '@/components/ui/toast';
import { ThemeProvider } from '@/components/layout/ThemeProvider';
import { setApiToken } from '@/lib/api';

// Syncs the NextAuth session token (from Google OAuth or credentials) into
// apiClient so every axios request includes the correct Authorization header.
function AuthSync() {
  const { data: session } = useSession();
  useEffect(() => {
    const token = (session as { accessToken?: string } | null)?.accessToken ?? null;
    setApiToken(token);
  }, [session]);
  return null;
}

function makeQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 60 * 1000, // 1 minute
        gcTime: 5 * 60 * 1000, // 5 minutes
        retry: 1,
        refetchOnWindowFocus: false,
      },
    },
  });
}

let browserQueryClient: QueryClient | undefined;

function getQueryClient(): QueryClient {
  if (typeof window === 'undefined') {
    return makeQueryClient();
  }
  if (!browserQueryClient) {
    browserQueryClient = makeQueryClient();
  }
  return browserQueryClient;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => getQueryClient());

  return (
    <SessionProvider>
      <AuthSync />
      <QueryClientProvider client={queryClient}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <ToastProvider>
            {children}
            <ToastViewport />
          </ToastProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </SessionProvider>
  );
}
