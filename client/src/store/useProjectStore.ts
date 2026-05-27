import { create } from 'zustand';
import { fetchProject, fetchProjects, createProject, activateProject, deleteProject } from '../api/client';
import type { ProjectSummary, ProjectInfo } from '../api/client';

interface ProjectState {
  summary: ProjectSummary;
  projects: ProjectInfo[];
  activeId: string | null;
  loading: boolean;
  refresh: () => Promise<void>;
  refreshProjects: () => Promise<void>;
  create: (name: string) => Promise<void>;
  activate: (id: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
}

export const useProjectStore = create<ProjectState>((set, get) => ({
  summary: {
    geo_loaded: false, pile_loaded: false, geo_holes_count: 0,
    geo_layers_count: 0, piles_count: 0, support_layer: '', interp_method: ''
  },
  projects: [],
  activeId: null,
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
  refreshProjects: async () => {
    try {
      const res = await fetchProjects();
      set({ projects: res.data.projects, activeId: res.data.active_id });
    } catch {}
  },
  create: async (name: string) => {
    await createProject(name);
    await get().refreshProjects();
    await get().refresh();
  },
  activate: async (id: string) => {
    await activateProject(id);
    set({ activeId: id });
    await get().refresh();
  },
  remove: async (id: string) => {
    await deleteProject(id);
    await get().refreshProjects();
    await get().refresh();
  },
}));
