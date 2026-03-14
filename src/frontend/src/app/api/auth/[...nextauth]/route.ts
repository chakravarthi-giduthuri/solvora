import NextAuth, { type NextAuthOptions } from 'next-auth';
import GoogleProvider from 'next-auth/providers/google';
import CredentialsProvider from 'next-auth/providers/credentials';
import type { JWT } from 'next-auth/jwt';
import type { Session } from 'next-auth';
import axios from 'axios';

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';

declare module 'next-auth' {
  interface Session {
    accessToken?: string;
    user: {
      id?: string;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
    userId?: string;
  }
}

const authOptions: NextAuthOptions = {
  providers: [
    // ── Google OAuth ──────────────────────────────────────────────────────────
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID ?? '',
      clientSecret: process.env.GOOGLE_CLIENT_SECRET ?? '',
    }),

    // ── Email/password credentials ────────────────────────────────────────────
    CredentialsProvider({
      name: 'Credentials',
      credentials: {
        email: { label: 'Email', type: 'email' },
        password: { label: 'Password', type: 'password' },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) {
          return null;
        }

        try {
          const response = await axios.post<{
            access_token: string;
            user: { id: string; email: string; name: string; avatarUrl?: string };
          }>(`${API_URL}/auth/login`, {
            email: credentials.email,
            password: credentials.password,
          });

          const { access_token, user } = response.data;

          return {
            id: user.id,
            email: user.email,
            name: user.name,
            image: user.avatarUrl ?? null,
            accessToken: access_token,
          };
        } catch {
          return null;
        }
      },
    }),
  ],

  callbacks: {
    async jwt({ token, user, account }): Promise<JWT> {
      // Initial sign in
      if (user && 'accessToken' in user) {
        token.accessToken = user.accessToken as string;
        token.userId = user.id;
      }

      // Google sign in — exchange Google token for backend JWT if needed
      if (account?.provider === 'google' && account.id_token) {
        try {
          const response = await axios.post<{ access_token: string }>(
            `${API_URL}/auth/google-id-token`,
            { id_token: account.id_token },
          );
          token.accessToken = response.data.access_token;
        } catch {
          // Fall back — user will need email/password for authenticated actions
        }
      }

      return token;
    },

    async session({ session, token }): Promise<Session> {
      session.accessToken = token.accessToken;
      if (token.userId) {
        session.user.id = token.userId;
      }
      return session;
    },
  },

  pages: {
    signIn: '/auth/login',
    newUser: '/auth/signup',
    error: '/auth/login',
  },

  session: {
    strategy: 'jwt',
    maxAge: 7 * 24 * 60 * 60, // 7 days
  },

  secret: process.env.NEXTAUTH_SECRET,
};

const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
