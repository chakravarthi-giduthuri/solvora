'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { X, Plus, Save } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { useAuthStore } from '@/store/authStore';
import { useFilterStore } from '@/store/filterStore';
import apiClient from '@/lib/api';
import type { Platform, Sentiment, DateRange } from '@/types';

interface ApiPreset {
  id: string;
  name: string;
  filters: {
    platform?: Platform | '';
    category?: string;
    sentiment?: Sentiment | '';
    dateRange?: DateRange;
    hasSolution?: boolean | null;
    search?: string;
  };
}

async function fetchPresets(): Promise<ApiPreset[]> {
  const res = await apiClient.get<ApiPreset[]>('/filter-presets');
  return res.data;
}

async function createPreset(payload: { name: string; filters: object }): Promise<ApiPreset> {
  const res = await apiClient.post<ApiPreset>('/filter-presets', payload);
  return res.data;
}

async function deletePreset(id: string): Promise<void> {
  await apiClient.delete(`/filter-presets/${id}`);
}

export function FilterPresets() {
  const { isAuthenticated } = useAuthStore();
  const setFilter = useFilterStore((s) => s.setFilter);
  const filterState = useFilterStore((s) => s);

  const [showNameInput, setShowNameInput] = useState(false);
  const [presetName, setPresetName] = useState('');

  const queryClient = useQueryClient();

  const { data: presets = [] } = useQuery<ApiPreset[]>({
    queryKey: ['filter-presets'],
    queryFn: fetchPresets,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  const createMutation = useMutation({
    mutationFn: createPreset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['filter-presets'] });
      setPresetName('');
      setShowNameInput(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deletePreset,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['filter-presets'] });
    },
  });

  if (!isAuthenticated) return null;

  const applyPreset = (preset: ApiPreset) => {
    const f = preset.filters;
    if (f.platform !== undefined) setFilter('platform', f.platform ?? '');
    if (f.category !== undefined) setFilter('category', f.category ?? '');
    if (f.sentiment !== undefined) setFilter('sentiment', f.sentiment ?? '');
    if (f.dateRange !== undefined) setFilter('dateRange', f.dateRange ?? {});
    if (f.hasSolution !== undefined) setFilter('hasSolution', f.hasSolution ?? null);
    if (f.search !== undefined) setFilter('search', f.search ?? '');
  };

  const handleSave = () => {
    if (!presetName.trim()) return;
    createMutation.mutate({
      name: presetName.trim(),
      filters: {
        platform: filterState.platform,
        category: filterState.category,
        sentiment: filterState.sentiment,
        dateRange: filterState.dateRange,
        hasSolution: filterState.hasSolution,
        search: filterState.search,
      },
    });
  };

  return (
    <div className="space-y-2">
      {presets.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {presets.map((preset) => (
            <div key={preset.id} className="flex items-center gap-0.5 group">
              <button
                onClick={() => applyPreset(preset)}
                className="text-xs px-2 py-1 rounded-l-md border border-input bg-background hover:bg-accent hover:text-accent-foreground transition-colors truncate max-w-[120px]"
                title={preset.name}
              >
                {preset.name}
              </button>
              <button
                onClick={() => deleteMutation.mutate(preset.id)}
                disabled={deleteMutation.isPending}
                className="p-1 rounded-r-md border border-l-0 border-input bg-background hover:bg-destructive hover:text-destructive-foreground transition-colors"
                aria-label={`Delete preset ${preset.name}`}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {showNameInput ? (
        <div className="flex items-center gap-1">
          <Input
            autoFocus
            value={presetName}
            onChange={(e) => setPresetName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSave();
              if (e.key === 'Escape') setShowNameInput(false);
            }}
            placeholder="Preset name…"
            className="h-7 text-xs flex-1"
          />
          <Button
            size="sm"
            onClick={handleSave}
            disabled={!presetName.trim() || createMutation.isPending}
            className="h-7 px-2"
          >
            <Save className="h-3 w-3" />
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setShowNameInput(false)}
            className="h-7 px-2"
          >
            <X className="h-3 w-3" />
          </Button>
        </div>
      ) : (
        <Button
          variant="outline"
          size="sm"
          onClick={() => setShowNameInput(true)}
          className="h-7 px-2 text-xs gap-1 w-full"
        >
          <Plus className="h-3 w-3" />
          Save current
        </Button>
      )}
    </div>
  );
}
