import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: {
    default: 'Solvora — Discover & Solve Community Problems',
    template: '%s | Solvora',
  },
  description:
    'AI-powered dashboard that aggregates problems from Reddit and Hacker News, then generates solutions using Gemini, OpenAI, and Claude.',
  keywords: ['AI', 'problem solving', 'Reddit', 'Hacker News', 'dashboard'],
  authors: [{ name: 'Solvora Team' }],
  openGraph: {
    type: 'website',
    locale: 'en_US',
    title: 'Solvora',
    description: 'AI-powered community problem solving dashboard',
    siteName: 'Solvora',
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
