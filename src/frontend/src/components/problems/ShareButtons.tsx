'use client';

import { useState } from 'react';
import { Share2, Linkedin, Copy } from 'lucide-react';
import { Button } from '@/components/ui/button';
import apiClient from '@/lib/api';

interface ShareButtonsProps {
  title: string;
  url: string;
  problemId: string;
}

function fireShare(problemId: string) {
  apiClient.post(`/problems/${problemId}/share`).catch(() => {
    // Fire-and-forget: silently ignore errors
  });
}

export function ShareButtons({ title, url, problemId }: ShareButtonsProps) {
  const [copied, setCopied] = useState(false);

  const resolvedUrl = url || (typeof window !== 'undefined' ? window.location.href : '');

  const handleTwitter = () => {
    const tweetUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(title)}&url=${encodeURIComponent(resolvedUrl)}`;
    window.open(tweetUrl, '_blank', 'noopener,noreferrer');
    fireShare(problemId);
  };

  const handleLinkedIn = () => {
    const liUrl = `https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(resolvedUrl)}`;
    window.open(liUrl, '_blank', 'noopener,noreferrer');
    fireShare(problemId);
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(resolvedUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Silently ignore clipboard errors
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Button
        variant="ghost"
        size="sm"
        onClick={handleTwitter}
        className="h-8 px-2 text-xs gap-1.5"
        aria-label="Share on X (Twitter)"
      >
        <Share2 className="h-3.5 w-3.5" />
        X
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={handleLinkedIn}
        className="h-8 px-2 text-xs gap-1.5"
        aria-label="Share on LinkedIn"
      >
        <Linkedin className="h-3.5 w-3.5" />
        LinkedIn
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={handleCopy}
        className="h-8 px-2 text-xs gap-1.5"
        aria-label="Copy link"
      >
        <Copy className="h-3.5 w-3.5" />
        {copied ? 'Copied!' : 'Copy'}
      </Button>
    </div>
  );
}
