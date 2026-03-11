'use client';

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Platform, Sentiment, FilterPreset, DateRange } from '@/types';

interface FilterState {
  platform: Platform | '';
  category: string;
  sentiment: Sentiment | '';
  dateRange: DateRange;
  hasSolution: boolean | null;
  search: string;
  page: number;
  sortBy: 'recent' | 'upvotes' | 'comments';

  savedPresets: FilterPreset[];

  setFilter: <K extends keyof FilterValues>(key: K, value: FilterValues[K]) => void;
  resetFilters: () => void;
  savePreset: (name: string) => void;
  loadPreset: (id: string) => void;
  deletePreset: (id: string) => void;
}

interface FilterValues {
  platform: Platform | '';
  category: string;
  sentiment: Sentiment | '';
  dateRange: DateRange;
  hasSolution: boolean | null;
  search: string;
  page: number;
  sortBy: 'recent' | 'upvotes' | 'comments';
}

const defaultFilters: FilterValues = {
  platform: '',
  category: '',
  sentiment: '',
  dateRange: {},
  hasSolution: null,
  search: '',
  page: 1,
  sortBy: 'recent',
};

export const useFilterStore = create<FilterState>()(
  persist(
    (set, get) => ({
      ...defaultFilters,
      savedPresets: [],

      setFilter: <K extends keyof FilterValues>(key: K, value: FilterValues[K]) => {
        // Reset to page 1 whenever a filter (other than page itself) changes
        const resetPage = key !== 'page' ? { page: 1 } : {};
        set({ [key]: value, ...resetPage } as Partial<FilterState>);
      },

      resetFilters: () => {
        set({ ...defaultFilters });
      },

      savePreset: (name: string) => {
        const state = get();
        const preset: FilterPreset = {
          id: `preset-${Date.now()}`,
          name,
          platform: state.platform,
          category: state.category,
          sentiment: state.sentiment,
          dateRange: state.dateRange,
          hasSolution: state.hasSolution,
          search: state.search,
          createdAt: new Date().toISOString(),
        };
        set((s) => ({ savedPresets: [...s.savedPresets, preset] }));
      },

      loadPreset: (id: string) => {
        const preset = get().savedPresets.find((p) => p.id === id);
        if (!preset) return;
        set({
          platform: preset.platform,
          category: preset.category,
          sentiment: preset.sentiment,
          dateRange: preset.dateRange,
          hasSolution: preset.hasSolution,
          search: preset.search,
          page: 1,
        });
      },

      deletePreset: (id: string) => {
        set((s) => ({
          savedPresets: s.savedPresets.filter((p) => p.id !== id),
        }));
      },
    }),
    {
      name: 'filter-storage',
      partialize: (state) => ({
        savedPresets: state.savedPresets,
        // Only persist presets; runtime filters reset on page load
      }),
    },
  ),
);
