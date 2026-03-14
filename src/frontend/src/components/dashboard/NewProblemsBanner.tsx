'use client';

import { useState, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';

function buildSseUrl(): string {
  const base = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000/api/v1';
  // Strip /api/v1 suffix then re-add the SSE path
  const origin = base.replace(/\/api\/v1\/?$/, '');
  return `${origin}/api/v1/stream/problems`;
}

export function NewProblemsBanner() {
  const [count, setCount] = useState(0);
  const queryClient = useQueryClient();
  const esRef = useRef<EventSource | null>(null);
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = () => {
    if (typeof window === 'undefined') return;

    const url = buildSseUrl();
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (event) => {
      const num = parseInt(event.data, 10);
      if (!isNaN(num) && num > 0) {
        setCount((c) => c + num);
      }
    };

    es.onerror = () => {
      es.close();
      esRef.current = null;
      // Reconnect after 10 seconds
      reconnectRef.current = setTimeout(connect, 10000);
    };
  };

  useEffect(() => {
    connect();
    return () => {
      esRef.current?.close();
      if (reconnectRef.current) clearTimeout(reconnectRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (count === 0) return null;

  const handleClick = () => {
    setCount(0);
    queryClient.invalidateQueries({ queryKey: ['problems'] });
  };

  return (
    <div
      role="status"
      onClick={handleClick}
      className="w-full bg-blue-600 text-white text-sm font-medium py-2 text-center cursor-pointer select-none hover:bg-blue-700 transition-colors"
    >
      {'\u2191'} {count} new {count === 1 ? 'problem' : 'problems'} — click to refresh
    </div>
  );
}
