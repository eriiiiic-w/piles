import { create } from 'zustand';
import { fetchSettings, updateSettings } from '../api/client';
import type { SettingsData } from '../api/client';

interface SettingsState {
  settings: SettingsData;
  loading: boolean;
  load: () => Promise<void>;
  update: (data: Partial<SettingsData>) => Promise<void>;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  settings: {
    support_layer: '', support_depth: 1.5, support_depth_type: '直接输入',
    warning_threshold: 0.3, alarm_threshold: 0.5, interp_method: '克里金法', pile_top_elev: 0.5
  },
  loading: false,
  load: async () => {
    set({ loading: true });
    try {
      const res = await fetchSettings();
      set({ settings: res.data, loading: false });
    } catch {
      set({ loading: false });
    }
  },
  update: async (data) => {
    await updateSettings(data);
    set((s) => ({ settings: { ...s.settings, ...data } }));
  },
}));
