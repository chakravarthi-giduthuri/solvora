'use client';

import { useState, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import apiClient from '@/lib/api';
import { cn } from '@/lib/utils';

interface TagListProps {
  problemId: string;
  editable?: boolean;
}

interface TagResult {
  name: string;
}

async function fetchProblemTags(problemId: string): Promise<string[]> {
  const res = await apiClient.get<string[] | TagResult[]>(`/tags/problem/${problemId}`);
  const data = res.data;
  if (!Array.isArray(data)) return [];
  return data.map((t) => (typeof t === 'string' ? t : t.name));
}

async function searchTags(q: string): Promise<string[]> {
  const res = await apiClient.get<string[] | TagResult[]>(`/tags?q=${encodeURIComponent(q)}`);
  const data = res.data;
  if (!Array.isArray(data)) return [];
  return data.map((t) => (typeof t === 'string' ? t : t.name));
}

async function addTags(problemId: string, tags: string[]): Promise<void> {
  await apiClient.post(`/tags/problem/${problemId}`, { tags });
}

// ─── Tag adder sub-component ──────────────────────────────────────────────────

function TagAdder({ problemId }: { problemId: string }) {
  const [query, setQuery] = useState('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [showInput, setShowInput] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const queryClient = useQueryClient();

  const addMutation = useMutation({
    mutationFn: (tag: string) => addTags(problemId, [tag]),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tags', problemId] });
      setQuery('');
      setSuggestions([]);
      setOpen(false);
      setShowInput(false);
    },
  });

  const handleQueryChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setQuery(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!val.trim()) { setSuggestions([]); setOpen(false); return; }
    debounceRef.current = setTimeout(async () => {
      try {
        const results = await searchTags(val);
        setSuggestions(results.slice(0, 8));
        setOpen(results.length > 0);
      } catch {
        setSuggestions([]);
        setOpen(false);
      }
    }, 250);
  };

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, []);

  if (!showInput) {
    return (
      <button
        onClick={() => setShowInput(true)}
        className="inline-flex items-center gap-0.5 text-xs text-muted-foreground hover:text-foreground transition-colors rounded px-1"
        aria-label="Add tag"
      >
        <Plus className="h-3 w-3" />
      </button>
    );
  }

  return (
    <div ref={containerRef} className="relative inline-block">
      <input
        autoFocus
        type="text"
        value={query}
        onChange={handleQueryChange}
        onKeyDown={(e) => {
          if (e.key === 'Escape') { setShowInput(false); setOpen(false); }
          if (e.key === 'Enter' && query.trim()) {
            addMutation.mutate(query.trim());
          }
        }}
        placeholder="Add tag…"
        className={cn(
          'text-xs h-6 px-2 rounded border border-input bg-background',
          'focus:outline-none focus:ring-1 focus:ring-ring w-28',
        )}
      />
      {open && suggestions.length > 0 && (
        <ul className="absolute z-50 mt-0.5 left-0 w-40 rounded-md border border-input bg-popover shadow-md overflow-hidden">
          {suggestions.map((s) => (
            <li
              key={s}
              onMouseDown={(e) => {
                e.preventDefault();
                addMutation.mutate(s);
              }}
              className="px-2 py-1.5 text-xs cursor-pointer hover:bg-accent hover:text-accent-foreground truncate"
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function TagList({ problemId, editable = false }: TagListProps) {
  const { data: tags = [] } = useQuery<string[]>({
    queryKey: ['tags', problemId],
    queryFn: () => fetchProblemTags(problemId),
    staleTime: 5 * 60 * 1000,
  });

  if (!editable && tags.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1">
      {tags.map((tag) => (
        <Badge key={tag} variant="secondary" className="text-xs px-1.5 py-0">
          {tag}
        </Badge>
      ))}
      {editable && <TagAdder problemId={problemId} />}
    </div>
  );
}
