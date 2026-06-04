import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

export interface ProjectSummary {
  geo_loaded: boolean;
  pile_loaded: boolean;
  geo_holes_count: number;
  geo_layers_count: number;
  piles_count: number;
  support_layer: string;
  interp_method: string;
}

export interface SettingsData {
  support_layer: string;
  support_depth: number;
  support_depth_type: string;
  warning_threshold: number;
  alarm_threshold: number;
  interp_method: string;
  pile_top_elev: number;
  safety_factor: number;
}

export interface PileItem {
  pile_no: string;
  x: number;
  y: number;
  diameter: number;
  pile_type: string;
}

export interface PredictionResult {
  桩号: string;
  X坐标: number;
  Y坐标: number;
  桩径: number;
  桩型: string;
  土层预测: Record<string, number>;
  土层底标高预测: Record<string, number>;
  土层排序: string[];
  持力层顶标高?: number;
  持力层进入深度?: number;
  桩顶标高: number;
}

export interface SceneData {
  piles: {
    id: string;
    x: number;
    y: number;
    diameter: number;
    pile_type: string;
    top_elev: number;
    bottom_elev: number | null;
    bearing_elev: number | null;
    soil_segments: { name: string; top: number; bottom: number; color: string; is_bearing: boolean }[];
  }[];
  support_layer: string;
  bounds: { x: number[]; y: number[]; z: number[] };
  soil_planes: { name: string; elevation: number; color: string }[];
}

// Settings
export const fetchSettings = () => api.get<SettingsData>('/settings');
export const updateSettings = (data: Partial<SettingsData>) => api.put<SettingsData>('/settings', data);

// Project
export const fetchProject = () => api.get<ProjectSummary>('/project');

// Geo
export const uploadGeo = (file: File) => {
  const fd = new FormData(); fd.append('file', file);
  return api.post('/geo/upload', fd);
};
export const fetchLayers = () => api.get<{ layers: string[] }>('/geo/layers');

// Piles
export const uploadPiles = (file: File) => {
  const fd = new FormData(); fd.append('file', file);
  return api.post('/piles/upload', fd);
};
export const fetchPiles = (search = '') => api.get<{ piles: PileItem[] }>(`/piles?search=${search}`);

// Predict
export const predictSingle = (pileNo: string) => api.post<{ ok: boolean; result: PredictionResult }>(`/predict/single/${pileNo}`);
export const predictAll = () => api.post<{ ok: boolean; count: number }>('/predict/all');
export const fetchSceneData = () => api.get<SceneData>('/predict/scene-data');

// Measured
export const saveMeasured = (data: { pile_no: string; layer_name: string; measured_elev: number; actual_depth?: number }) =>
  api.post('/measured', data);
export const fetchMeasured = (pileNo: string) =>
  api.get<{ pile_no: string; layers: Record<string, { measured_elev: number; recorded_at: string }> }>(`/measured/${pileNo}`);

// Bearing
export const calcBearing = (pileNo: string) => api.post(`/bearing/calc/${pileNo}`);
export const calcAllBearing = () => api.post('/bearing/calc-all');
export const getSoilParams = () => api.get('/bearing/params');
export const updateSoilParam = (layerName: string, qsik?: number, qpk?: number) =>
  api.put('/bearing/params', { layer_name: layerName, qsik, qpk });
export const uploadSoilParams = (file: File) => {
  const fd = new FormData(); fd.append('file', file);
  return api.post('/bearing/params', fd);
};

// Export
export const exportPredictions = () => api.get('/export/predictions', { responseType: 'blob' });
export const exportMeasuredHoles = () => api.get('/export/measured-holes', { responseType: 'blob' });

export interface ProjectInfo {
  id: string;
  name: string;
  created_at: string;
}

export interface ProjectListResponse {
  projects: ProjectInfo[];
  active_id: string | null;
}

// Project management
export const fetchProjects = () => api.get<ProjectListResponse>('/projects');
export const createProject = (name: string) => api.post<ProjectInfo>('/projects', { name });
export const activateProject = (id: string) => api.put<void>(`/projects/${id}/activate`);
export const deleteProject = (id: string) => api.delete<void>(`/projects/${id}`);
