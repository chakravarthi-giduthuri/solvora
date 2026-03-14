'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Search } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { useFilterStore } from '@/store/filterStore';
import apiClient from '@/lib/api';
import { cn } from '@/lib/utils';

interface SearchAutocompleteProps {
  className?: string;
}

export function SearchAutocomplete({ className }: SearchAutocompleteProps) {
  const search = useFilterStore((s) => s.search);
  const setFilter = useFilterStore((s) => s.setFilter);

  const [inputValue, setInputValue] = useState(search);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Sync if store changes externally
  useEffect(() => {
    setInputValue(search);
  }, [search]);

  const fetchSuggestions = useCallback(async (q: string) => {
    if (!q.trim()) {
      setSuggestions([]);
      setOpen(false);
      return;
    }
    try {
      const res = await apiClient.get<string[]>(
        `/problems/autocomplete?q=${encodeURIComponent(q)}`,
      );
      const items = Array.isArray(res.data) ? res.data.slice(0, 10) : [];
      setSuggestions(items);
      setOpen(items.length > 0);
      setActiveIndex(-1);
    } catch {
      setSuggestions([]);
      setOpen(false);
    }
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setInputValue(val);
    setFilter('search', val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => fetchSuggestions(val), 300);
  };

  const handleSelect = (suggestion: string) => {
    setInputValue(suggestion);
    setFilter('search', suggestion);
    setSuggestions([]);
    setOpen(false);
    setActiveIndex(-1);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, -1));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      handleSelect(suggestions[activeIndex]);
    } else if (e.key === 'Escape') {
      setOpen(false);
      setActiveIndex(-1);
    }
  };

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        setActiveIndex(-1);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  // Cleanup debounce on unmount
  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
        <Input
          type="text"
          placeholder="Search problems…"
          value={inputValue}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          onFocus={() => suggestions.length > 0 && setOpen(true)}
          className="pl-8 h-8 text-xs"
          aria-autocomplete="list"
          aria-expanded={open}
          aria-controls="autocomplete-list"
          role="combobox"
        />
      </div>

      {open && suggestions.length > 0 && (
        <ul
          id="autocomplete-list"
          role="listbox"
          className="absolute z-50 mt-1 w-full rounded-md border border-input bg-popover shadow-md overflow-hidden"
        >
          {suggestions.map((s, i) => (
            <li
              key={s}
              role="option"
              aria-selected={i === activeIndex}
              onMouseDown={(e) => {
                e.preventDefault();
                handleSelect(s);
              }}
              className={cn(
                'px-3 py-2 text-xs cursor-pointer truncate',
                i === activeIndex
                  ? 'bg-accent text-accent-foreground'
                  : 'hover:bg-accent hover:text-accent-foreground',
              )}
            >
              {s}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
