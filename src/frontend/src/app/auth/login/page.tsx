import type { Metadata } from 'next';
import { LoginForm } from './LoginForm';
import { Brain } from 'lucide-react';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Login',
  description: 'Sign in to your Solvora account',
};

export default function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background p-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 font-bold text-2xl">
            <Brain className="h-8 w-8 text-primary" />
            <span>Solvora</span>
          </Link>
          <p className="text-muted-foreground mt-2 text-sm">
            Sign in to access your dashboard
          </p>
        </div>

        <LoginForm />

        <p className="text-center text-sm text-muted-foreground mt-6">
          Don&apos;t have an account?{' '}
          <Link href="/auth/signup" className="text-primary hover:underline font-medium">
            Sign up
          </Link>
        </p>
      </div>
    </div>
  );
}
