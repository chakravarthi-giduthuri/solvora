'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { Search, X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useFilterStore } from '@/store/filterStore';
import { cn } from '@/lib/utils';

interface SearchBarProps {
  className?: string;
  placeholder?: string;
}

export function SearchBar({
  className,
  placeholder = 'Search problems…',
}: SearchBarProps) {
  const search = useFilterStore((s) => s.search);
  const setFilter = useFilterStore((s) => s.setFilter);

  const [localValue, setLocalValue] = useState(search);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Sync external changes (e.g., preset load) back to local input
  useEffect(() => {
    setLocalValue(search);
  }, [search]);

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const value = e.target.value;
      setLocalValue(value);

      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(() => {
        setFilter('search', value);
      }, 300);
    },
    [setFilter],
  );

  const handleClear = useCallback(() => {
    setLocalValue('');
    setFilter('search', '');
  }, [setFilter]);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  return (
    <div className={cn('relative flex items-center', className)}>
      <Search
        className="absolute left-3 h-4 w-4 text-muted-foreground pointer-events-none"
        aria-hidden="true"
      />
      <Input
        type="search"
        value={localValue}
        onChange={handleChange}
        placeholder={placeholder}
        className="pl-9 pr-9"
        aria-label="Search problems"
      />
      {localValue && (
        <Button
          variant="ghost"
          size="icon"
          className="absolute right-1 h-7 w-7"
          onClick={handleClear}
          aria-label="Clear search"
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      )}
    </div>
  );
}
