import type { Metadata } from 'next';
import { BookmarksClient } from './BookmarksClient';
import { Navbar } from '@/components/layout/Navbar';

export const metadata: Metadata = {
  title: 'Bookmarks',
  description: 'Your saved problems',
};

export default function BookmarksPage() {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1">
        <div className="container mx-auto px-4 py-6">
          <BookmarksClient />
        </div>
      </main>
    </div>
  );
}
