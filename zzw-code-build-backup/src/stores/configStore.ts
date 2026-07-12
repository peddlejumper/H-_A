import { create } from 'zustand';
import type { ApiConfig } from '@/types';

interface ConfigState {
  config: ApiConfig | null;
  isConfigured: boolean;
  setConfig: (config: ApiConfig) => void;
  clearConfig: () => void;
  loadFromStorage: () => void;
}

export const useConfigStore = create<ConfigState>((set) => ({
  config: null,
  isConfigured: false,
  setConfig: (config) => {
    localStorage.setItem('zzw-api-config', JSON.stringify(config));
    set({ config, isConfigured: true });
  },
  clearConfig: () => {
    localStorage.removeItem('zzw-api-config');
    set({ config: null, isConfigured: false });
  },
  loadFromStorage: () => {
    const stored = localStorage.getItem('zzw-api-config');
    if (stored) {
      try {
        const config = JSON.parse(stored) as ApiConfig;
        set({ config, isConfigured: true });
      } catch {
        set({ config: null, isConfigured: false });
      }
    }
  },
}));