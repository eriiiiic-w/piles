import { create } from 'zustand';
import { fetchProject, ProjectSummary } from '../api/client';

interface ProjectState {
  summary: ProjectSummary;
  loading: boolean;
  refresh: () => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set) => ({
  summary: {
    geo_loaded: false, pile_loaded: false, geo_holes_count: 0,
    geo_layers_count: 0, piles_count: 0, support_layer: '', interp_method: ''
  },
  loading: false,
  refresh: async () => {
    set({ loading: true });
    try {
      const res = await fetchProject();
      set({ summary: res.data, loading: false });
    } catch {
      set({ loading: false });
    }
  },
}));
