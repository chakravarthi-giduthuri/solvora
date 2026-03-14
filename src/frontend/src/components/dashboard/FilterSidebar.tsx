'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Filter, RotateCcw, Save, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from '@/components/ui/dialog';
import { useFilterStore } from '@/store/filterStore';
import { useAuthStore } from '@/store/authStore';
import { getCategories } from '@/lib/api';
import { cn } from '@/lib/utils';
import { SearchAutocomplete } from '@/components/dashboard/SearchAutocomplete';
import { FilterPresets } from '@/components/dashboard/FilterPresets';
import type { Platform, Sentiment } from '@/types';

const PLATFORMS: { value: Platform; label: string }[] = [
  { value: 'reddit', label: 'Reddit' },
  { value: 'hackernews', label: 'Hacker News' },
];

const SENTIMENTS: { value: Sentiment; label: string; color: string }[] = [
  { value: 'urgent', label: 'Urgent', color: 'text-red-500' },
  { value: 'frustrated', label: 'Frustrated', color: 'text-orange-500' },
  { value: 'curious', label: 'Curious', color: 'text-blue-500' },
  { value: 'neutral', label: 'Neutral', color: 'text-gray-500' },
];

// ─── Section wrapper ──────────────────────────────────────────────────────────

function FilterSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <h3 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
        {title}
      </h3>
      {children}
    </div>
  );
}

// ─── Save preset dialog ───────────────────────────────────────────────────────

function SavePresetDialog() {
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const savePreset = useFilterStore((s) => s.savePreset);

  const handleSave = () => {
    if (!name.trim()) return;
    savePreset(name.trim());
    setName('');
    setOpen(false);
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="w-full gap-2">
          <Save className="h-4 w-4" />
          Save Preset
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-sm">
        <DialogHeader>
          <DialogTitle>Save Filter Preset</DialogTitle>
        </DialogHeader>
        <div className="py-2">
          <Label htmlFor="preset-name">Preset name</Label>
          <Input
            id="preset-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. AI problems this week"
            className="mt-1"
            onKeyDown={(e) => e.key === 'Enter' && handleSave()}
            autoFocus
          />
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={() => setOpen(false)}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!name.trim()}>
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export function FilterSidebar() {
  const {
    platform,
    category,
    sentiment,
    dateRange,
    hasSolution,
    savedPresets,
    setFilter,
    resetFilters,
    loadPreset,
    deletePreset,
  } = useFilterStore();

  const { isAuthenticated } = useAuthStore();

  const { data: categories = [] } = useQuery({
    queryKey: ['categories'],
    queryFn: getCategories,
    staleTime: Infinity,
  });

  const hasActiveFilters =
    platform || category || sentiment || dateRange.from || dateRange.to || hasSolution !== null;

  return (
    <aside
      className="w-full space-y-5"
      aria-label="Filter sidebar"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <h2 className="font-semibold flex items-center gap-2">
          <Filter className="h-4 w-4" />
          Filters
        </h2>
        {hasActiveFilters && (
          <Button
            variant="ghost"
            size="sm"
            onClick={resetFilters}
            className="text-xs gap-1 h-7"
          >
            <RotateCcw className="h-3 w-3" />
            Reset
          </Button>
        )}
      </div>

      {/* Search */}
      <SearchAutocomplete />

      <Separator />

      {/* Platform */}
      <FilterSection title="Platform">
        <div className="space-y-1.5">
          {PLATFORMS.map(({ value, label }) => (
            <label
              key={value}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <input
                type="checkbox"
                checked={platform === value}
                onChange={(e) =>
                  setFilter('platform', e.target.checked ? value : '')
                }
                className="rounded border-input text-primary focus:ring-primary"
              />
              <span className="text-sm group-hover:text-foreground transition-colors">
                {label}
              </span>
            </label>
          ))}
        </div>
      </FilterSection>

      <Separator />

      {/* Category */}
      <FilterSection title="Category">
        <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="category"
              checked={!category}
              onChange={() => setFilter('category', '')}
              className="text-primary focus:ring-primary"
            />
            <span className="text-sm">All categories</span>
          </label>
          {categories.map((cat) => (
            <label
              key={cat.id}
              className="flex items-center gap-2 cursor-pointer group"
            >
              <input
                type="radio"
                name="category"
                checked={category === cat.slug}
                onChange={() => setFilter('category', cat.slug)}
                className="text-primary focus:ring-primary"
              />
              <span className="text-sm group-hover:text-foreground transition-colors truncate">
                {cat.name}
              </span>
              {cat.problemCount !== undefined && (
                <span className="ml-auto text-xs text-muted-foreground shrink-0">
                  {cat.problemCount}
                </span>
              )}
            </label>
          ))}
        </div>
      </FilterSection>

      <Separator />

      {/* Sentiment */}
      <FilterSection title="Sentiment">
        <div className="space-y-1.5">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="radio"
              name="sentiment"
              checked={!sentiment}
              onChange={() => setFilter('sentiment', '')}
              className="text-primary focus:ring-primary"
            />
            <span className="text-sm">Any sentiment</span>
          </label>
          {SENTIMENTS.map(({ value, label, color }) => (
            <label
              key={value}
              className="flex items-center gap-2 cursor-pointer"
            >
              <input
                type="radio"
                name="sentiment"
                checked={sentiment === value}
                onChange={() => setFilter('sentiment', value)}
                className="text-primary focus:ring-primary"
              />
              <span className={cn('text-sm font-medium', color)}>{label}</span>
            </label>
          ))}
        </div>
      </FilterSection>

      <Separator />

      {/* Date range */}
      <FilterSection title="Date range">
        <div className="space-y-2">
          <div>
            <Label htmlFor="date-from" className="text-xs">
              From
            </Label>
            <Input
              id="date-from"
              type="date"
              value={dateRange.from ?? ''}
              onChange={(e) =>
                setFilter('dateRange', { ...dateRange, from: e.target.value || undefined })
              }
              className="mt-1 h-8 text-xs"
            />
          </div>
          <div>
            <Label htmlFor="date-to" className="text-xs">
              To
            </Label>
            <Input
              id="date-to"
              type="date"
              value={dateRange.to ?? ''}
              onChange={(e) =>
                setFilter('dateRange', { ...dateRange, to: e.target.value || undefined })
              }
              className="mt-1 h-8 text-xs"
            />
          </div>
        </div>
      </FilterSection>

      <Separator />

      {/* Has AI solution */}
      <FilterSection title="Solutions">
        <div className="flex items-center gap-3">
          <Switch
            id="has-solution"
            checked={hasSolution === true}
            onCheckedChange={(checked) =>
              setFilter('hasSolution', checked ? true : null)
            }
          />
          <Label htmlFor="has-solution" className="text-sm cursor-pointer">
            Has AI solution
          </Label>
        </div>
      </FilterSection>

      {/* Saved presets (auth required) */}
      {isAuthenticated && (
        <>
          <Separator />
          <FilterSection title="Saved presets">
            {savedPresets.length > 0 ? (
              <div className="space-y-1.5 mb-2">
                {savedPresets.map((preset) => (
                  <div
                    key={preset.id}
                    className="flex items-center gap-1 group"
                  >
                    <button
                      onClick={() => loadPreset(preset.id)}
                      className="flex-1 text-left text-xs px-2 py-1.5 rounded-md hover:bg-accent transition-colors truncate"
                    >
                      {preset.name}
                    </button>
                    <button
                      onClick={() => deletePreset(preset.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded hover:text-destructive transition-all"
                      aria-label={`Delete preset ${preset.name}`}
                    >
                      <Trash2 className="h-3 w-3" />
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-muted-foreground mb-2">
                No saved presets yet.
              </p>
            )}
            <SavePresetDialog />
          </FilterSection>
        </>
      )}

      {/* API-backed filter presets */}
      <Separator />
      <FilterSection title="Cloud presets">
        <FilterPresets />
      </FilterSection>
    </aside>
  );
}
