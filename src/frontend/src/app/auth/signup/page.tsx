import type { Metadata } from 'next';
import { SignupForm } from './SignupForm';
import { Brain } from 'lucide-react';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'Sign Up',
  description: 'Create your Solvora account',
};

export default function SignupPage() {
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
            Create your free account
          </p>
        </div>

        <SignupForm />

        <p className="text-center text-sm text-muted-foreground mt-6">
          Already have an account?{' '}
          <Link href="/auth/login" className="text-primary hover:underline font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
