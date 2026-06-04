# Project Management + 3D Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-project management (isolated SQLite DBs per project), 3D soil layer visualization, and enhanced pile hover/click details.

**Architecture:** Three independent workstreams. Project system adds dynamic DB switching via `projects/` directory with `_index.json`. 3D soil layers render as semi-transparent horizontal planes at each layer's average elevation. Pile detail panel appears as a collapsible bottom drawer in the 3D view.

**Tech Stack:** Python 3, FastAPI, SQLAlchemy, SQLite, React 18, TypeScript, React-Three-Fiber, Ant Design

---

## Feature 1: Project Management System

### Task 1.1: Update database.py — Dynamic DB Switching

**Files:**
- Modify: `server/database.py`

- [ ] **Step 1: Rewrite database.py with dynamic engine management**

```python
import os
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

PROJECTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "projects")
os.makedirs(PROJECTS_DIR, exist_ok=True)

_active_db_path: str | None = None
_engine = None
_SessionLocal = None


class Base(DeclarativeBase):
    pass


def _build_engine(db_path: str):
    return create_engine(f"sqlite:///{db_path}", echo=False, connect_args={"check_same_thread": False})


def init_db():
    global _engine, _SessionLocal
    if _engine is None:
        _engine = _build_engine(":memory:")
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)


def switch_database(db_path: str):
    global _engine, _SessionLocal, _active_db_path
    _engine = _build_engine(db_path)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)
    Base.metadata.create_all(bind=_engine)
    _active_db_path = db_path


def get_active_db_path() -> str | None:
    return _active_db_path


def get_db():
    if _SessionLocal is None:
        init_db()
    db = _SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 2: Commit**

```bash
git add server/database.py
git commit -m "feat: add dynamic database switching for multi-project support"
```

---

### Task 1.2: Add Project Management API Endpoints

**Files:**
- Modify: `server/schemas.py`
- Modify: `server/api/project.py`

- [ ] **Step 1: Add project schemas to server/schemas.py**

Append to `server/schemas.py`:

```python
class ProjectInfo(BaseModel):
    id: str
    name: str
    created_at: str

class ProjectListResponse(BaseModel):
    projects: List[ProjectInfo]
    active_id: Optional[str] = None

class CreateProjectRequest(BaseModel):
    name: str
```

- [ ] **Step 2: Rewrite server/api/project.py**

```python
import os
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from server.database import get_db, switch_database, get_active_db_path, PROJECTS_DIR
from server.models.geo import GeoLayer
from server.models.pile import Pile
from server.schemas import ProjectSummary, ProjectInfo, ProjectListResponse, CreateProjectRequest
from server.services.settings_service import get_all_settings

router = APIRouter(prefix="/api", tags=["project"])

INDEX_PATH = os.path.join(PROJECTS_DIR, "_index.json")


def _read_index() -> list[dict]:
    if not os.path.exists(INDEX_PATH):
        return []
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_index(data: list[dict]):
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _init_first_project():
    """Migrate legacy pile_app.db into a default project if it exists."""
    index = _read_index()
    if index:
        return
    legacy_db = os.path.join(os.path.dirname(PROJECTS_DIR), "pile_app.db")
    pid = str(uuid.uuid4())[:8]
    proj = {"id": pid, "name": "默认项目", "created_at": datetime.now().isoformat()}
    index.append(proj)
    _write_index(index)
    target = os.path.join(PROJECTS_DIR, f"{pid}.db")
    if os.path.exists(legacy_db):
        import shutil
        shutil.copy(legacy_db, target)
    switch_database(target)


@router.get("/project", response_model=ProjectSummary)
def get_project(db: Session = Depends(get_db)):
    s = get_all_settings(db)
    geo_count = db.query(GeoLayer).count()
    pile_count = db.query(Pile).count()
    hole_count = db.query(GeoLayer.hole_id).distinct().count()
    return ProjectSummary(
        geo_loaded=geo_count > 0,
        pile_loaded=pile_count > 0,
        geo_holes_count=hole_count,
        geo_layers_count=geo_count,
        piles_count=pile_count,
        support_layer=s.get("support_layer", ""),
        interp_method=s.get("interp_method", ""),
    )


@router.get("/projects", response_model=ProjectListResponse)
def list_projects():
    index = _read_index()
    projects = [ProjectInfo(**p) for p in index]
    return ProjectListResponse(projects=projects, active_id=_active_project_id(index))


def _active_project_id(index: list[dict]) -> str | None:
    active_path = get_active_db_path()
    if not active_path:
        return None
    for p in index:
        if active_path.endswith(f"{p['id']}.db"):
            return p["id"]
    return None


@router.post("/projects", response_model=ProjectInfo)
def create_project(req: CreateProjectRequest):
    pid = str(uuid.uuid4())[:8]
    proj = {"id": pid, "name": req.name, "created_at": datetime.now().isoformat()}
    index = _read_index()
    index.append(proj)
    _write_index(index)
    db_path = os.path.join(PROJECTS_DIR, f"{pid}.db")
    switch_database(db_path)
    return ProjectInfo(**proj)


@router.put("/projects/{project_id}/activate")
def activate_project(project_id: str):
    index = _read_index()
    for p in index:
        if p["id"] == project_id:
            db_path = os.path.join(PROJECTS_DIR, f"{project_id}.db")
            switch_database(db_path)
            return {"ok": True, "active_id": project_id}
    raise HTTPException(404, "项目不存在")


@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    index = _read_index()
    index = [p for p in index if p["id"] != project_id]
    _write_index(index)
    db_path = os.path.join(PROJECTS_DIR, f"{project_id}.db")
    if os.path.exists(db_path):
        os.remove(db_path)
    # If deleted the active project, switch to another or memory
    active_path = get_active_db_path()
    if active_path and active_path == db_path:
        if index:
            new_path = os.path.join(PROJECTS_DIR, f"{index[0]['id']}.db")
            switch_database(new_path)
        else:
            switch_database(":memory:")
    return {"ok": True}
```

- [ ] **Step 3: Commit**

```bash
git add server/schemas.py server/api/project.py
git commit -m "feat: add project CRUD + activate/delete API endpoints"
```

---

### Task 1.3: Update server/main.py — Startup Initialization

**Files:**
- Modify: `server/main.py`

- [ ] **Step 1: Add project initialization to startup event**

Replace the `startup` function in `server/main.py`:

```python
@app.on_event("startup")
def startup():
    from server.api.project import _init_first_project
    _init_first_project()
```

- [ ] **Step 2: Commit**

```bash
git add server/main.py
git commit -m "feat: auto-initialize default project on startup"
```

---

### Task 1.4: Update Frontend API Client

**Files:**
- Modify: `client/src/api/client.ts`

- [ ] **Step 1: Add project API types and functions**

Append to `client/src/api/client.ts`:

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add client/src/api/client.ts
git commit -m "feat: add project management API functions to frontend client"
```

---

### Task 1.5: Update useProjectStore

**Files:**
- Modify: `client/src/store/useProjectStore.ts`

- [ ] **Step 1: Extend store with project list and management actions**

Replace `client/src/store/useProjectStore.ts`:

```typescript
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
```

- [ ] **Step 2: Commit**

```bash
git add client/src/store/useProjectStore.ts
git commit -m "feat: extend project store with list, create, activate, delete actions"
```

---

### Task 1.6: Create ProjectPage Component

**Files:**
- Create: `client/src/pages/ProjectPage.tsx`

- [ ] **Step 1: Write ProjectPage.tsx**

```typescript
import { useState, useEffect } from 'react';
import { Card, Button, List, Modal, Input, message, Popconfirm } from 'antd';
import { PlusOutlined, DeleteOutlined, FolderOutlined } from '@ant-design/icons';
import { useProjectStore } from '../store/useProjectStore';

const ProjectPage: React.FC<{ onEnter: () => void }> = ({ onEnter }) => {
  const { projects, activeId, refreshProjects, create, activate, remove } = useProjectStore();
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => { refreshProjects(); }, []);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setLoading(true);
    await create(newName.trim());
    setLoading(false);
    setModalOpen(false);
    setNewName('');
    message.success('项目已创建');
  };

  const handleEnter = async (id: string) => {
    await activate(id);
    onEnter();
  };

  return (
    <div style={{ maxWidth: 500, margin: '80px auto', padding: 24 }}>
      <h1 style={{ textAlign: 'center', marginBottom: 32, fontSize: 24, fontWeight: 700, color: '#2c3e55' }}>
        桩基预测系统
      </h1>
      <Card
        title="选择项目"
        extra={
          <Button type="primary" icon={<PlusOutlined />} size="small" onClick={() => setModalOpen(true)}>
            新建项目
          </Button>
        }
      >
        {projects.length === 0 ? (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
            <p>暂无项目，请点击"新建项目"开始</p>
          </div>
        ) : (
          <List
            dataSource={projects}
            renderItem={(p) => (
              <List.Item
                actions={[
                  <Button key="enter" type="primary" size="small" onClick={() => handleEnter(p.id)}>
                    进入
                  </Button>,
                  <Popconfirm key="del" title="确定删除此项目？数据不可恢复" onConfirm={() => remove(p.id)}>
                    <Button size="small" danger icon={<DeleteOutlined />} />
                  </Popconfirm>
                ]}
              >
                <List.Item.Meta
                  avatar={<FolderOutlined style={{ fontSize: 24, color: p.id === activeId ? '#1890ff' : '#999' }} />}
                  title={p.name + (p.id === activeId ? ' (当前)' : '')}
                  description={`创建于 ${p.created_at.slice(0, 10)}`}
                />
              </List.Item>
            )}
          />
        )}
      </Card>

      <Modal title="新建项目" open={modalOpen} onOk={handleCreate} onCancel={() => setModalOpen(false)} confirmLoading={loading}>
        <Input placeholder="请输入项目名称" value={newName} onChange={(e) => setNewName(e.target.value)}
          onPressEnter={handleCreate} />
      </Modal>
    </div>
  );
};

export default ProjectPage;
```

- [ ] **Step 2: Commit**

```bash
git add client/src/pages/ProjectPage.tsx
git commit -m "feat: add project selection/creation page"
```

---

### Task 1.7: Update App.tsx — Project Selection Routing

**Files:**
- Modify: `client/src/App.tsx`

- [ ] **Step 1: Add project-aware routing**

Replace `client/src/App.tsx`:

```typescript
import { useState, useEffect } from 'react';
import { ConfigProvider, Spin } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import AppLayout from './components/layout/AppLayout';
import ProjectPage from './pages/ProjectPage';
import { useProjectStore } from './store/useProjectStore';

function App() {
  const [inProject, setInProject] = useState(false);
  const [checking, setChecking] = useState(true);
  const { activeId, refreshProjects } = useProjectStore();

  useEffect(() => {
    refreshProjects().finally(() => setChecking(false));
  }, []);

  useEffect(() => {
    if (activeId) setInProject(true);
  }, [activeId]);

  if (checking) {
    return (
      <ConfigProvider locale={zhCN}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh' }}>
          <Spin size="large" tip="加载中..." />
        </div>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider locale={zhCN}>
      {inProject ? <AppLayout /> : <ProjectPage onEnter={() => setInProject(true)} />}
    </ConfigProvider>
  );
}

export default App;
```

- [ ] **Step 2: Commit**

```bash
git add client/src/App.tsx
git commit -m "feat: add project selection routing to App"
```

---

### Task 1.8: Update Sidebar — Project Name Display

**Files:**
- Modify: `client/src/components/layout/Sidebar.tsx`

- [ ] **Step 1: Add project name below title**

Add import at top of file (after existing imports):

```typescript
import { useProjectStore } from '../../store/useProjectStore';
```

Inside the component function, add before the return statement:

```typescript
const activeId = useProjectStore((s) => s.activeId);
const projects = useProjectStore((s) => s.projects);
const activeProject = projects.find(p => p.id === activeId);

// Replace the header div:
<div style={{ padding: '16px', borderBottom: '1px solid #e8e8e8' }}>
  <div style={{ fontWeight: 700, fontSize: 20, color: '#2c3e55' }}>桩基预测系统</div>
  {activeProject && (
    <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
      项目: {activeProject.name}
    </div>
  )}
</div>
```

- [ ] **Step 2: Commit**

```bash
git add client/src/components/layout/Sidebar.tsx
git commit -m "feat: show active project name in sidebar"
```

---

### Task 1.9: Integration Test — Verify Project System

- [ ] **Step 1: Start the server and test project APIs**

```bash
python start.py &
sleep 3
# Test list projects
curl -s http://localhost:8000/api/projects | python -m json.tool
# Test create project
curl -s -X POST http://localhost:8000/api/projects -H "Content-Type: application/json" -d '{"name":"测试项目"}' | python -m json.tool
```

- [ ] **Step 2: Build frontend and verify**

```bash
cd client && npm run build
```

- [ ] **Step 3: Commit if any fixes needed**

```bash
git add -A
git commit -m "fix: project system integration fixes"
```

---

## Feature 2: 3D Soil Layer Visualization

### Task 2.1: Add Soil Plane Data to Backend

**Files:**
- Modify: `server/schemas.py`
- Modify: `server/services/predict_service.py`

- [ ] **Step 1: Add SoilPlaneItem to schemas.py**

Append to `server/schemas.py`:

```python
class SoilPlaneItem(BaseModel):
    name: str
    elevation: float
    color: str

# Update SceneDataResponse to include soil_planes:
class SceneDataResponse(BaseModel):
    piles: List[ScenePileItem]
    support_layer: str
    bounds: Dict[str, List[float]]
    soil_planes: List[SoilPlaneItem] = []
```

- [ ] **Step 2: Add soil_planes computation to get_scene_data()**

In `server/services/predict_service.py`, after computing `z_min/z_max` and before the return statement, add:

```python
# Compute soil planes: average elevation per layer, + color per layer
SOIL_COLORS = [
    "#c8b68e", "#b5a67c", "#a2b578", "#8f9e74", "#7c8e70",
    "#d4c5a0", "#bfb386", "#aaa16c", "#958f52", "#807d38",
    "#e8dcc8", "#d5c9b3", "#c2b69e", "#afa389", "#9c9074",
]
soil_planes = []
if not geo_df.empty:
    layer_names = core_get_layer_list(geo_df)
    for i, layer in enumerate(layer_names):
        avg_elev = float(geo_df[geo_df['土层名称'] == layer]['土层顶标高'].mean())
        color = SOIL_COLORS[i % len(SOIL_COLORS)]
        soil_planes.append({"name": layer, "elevation": round(avg_elev, 2), "color": color})

# Add soil_planes to return dict:
return {
    "piles": pile_items,
    "support_layer": support_layer,
    "bounds": { ... },
    "soil_planes": soil_planes,
}
```

- [ ] **Step 3: Commit**

```bash
git add server/schemas.py server/services/predict_service.py
git commit -m "feat: add soil plane data to scene-data API"
```

---

### Task 2.2: Create SoilPlanes 3D Component

**Files:**
- Create: `client/src/components/three/SoilPlanes.tsx`
- Modify: `client/src/api/client.ts`

- [ ] **Step 1: Update SceneData type in client.ts**

Add to the `SceneData` interface in `client/src/api/client.ts`:

```typescript
export interface SceneData {
  piles: {
    id: string; x: number; y: number; diameter: number;
    pile_type: string; top_elev: number; bottom_elev: number | null;
  }[];
  support_layer: string;
  bounds: { x: number[]; y: number[]; z: number[] };
  soil_planes: { name: string; elevation: number; color: string }[];
}
```

- [ ] **Step 2: Write SoilPlanes.tsx**

```typescript
import * as THREE from 'three';
import { useMemo } from 'react';

interface SoilPlaneData {
  name: string;
  elevation: number;
  color: string;
}

interface SoilPlanesProps {
  planes: SoilPlaneData[];
  supportLayer: string;
  bounds: { x: number[]; y: number[]; z: number[] };
}

const SoilPlanes = ({ planes, supportLayer, bounds }: SoilPlanesProps) => {
  const w = bounds.x[1] - bounds.x[0];
  const d = bounds.y[1] - bounds.y[0];
  const cx = (bounds.x[0] + bounds.x[1]) / 2;
  const cy = (bounds.y[0] + bounds.y[1]) / 2;

  const items = useMemo(() => {
    return planes.map((p) => ({
      ...p,
      isSupport: p.name === supportLayer,
    }));
  }, [planes, supportLayer]);

  if (w <= 0 || d <= 0) return null;

  return (
    <group>
      {items.map((p) => (
        <mesh
          key={p.name}
          rotation={[-Math.PI / 2, 0, 0]}
          position={[cx, cy, p.elevation]}
        >
          <planeGeometry args={[w * 1.3, d * 1.3]} />
          <meshBasicMaterial
            color={p.isSupport ? '#ff6b35' : p.color}
            side={THREE.DoubleSide}
            transparent
            opacity={p.isSupport ? 0.45 : 0.2}
          />
          {/* Support layer gets a visible edge ring */}
          {p.isSupport && (
            <lineSegments>
              <edgesGeometry args={[new THREE.PlaneGeometry(w * 1.3, d * 1.3)]} />
              <lineBasicMaterial color="#ff6b35" linewidth={1} transparent opacity={0.7} />
            </lineSegments>
          )}
        </mesh>
      ))}
    </group>
  );
};

export default SoilPlanes;
```

- [ ] **Step 3: Commit**

```bash
git add client/src/components/three/SoilPlanes.tsx client/src/api/client.ts
git commit -m "feat: add SoilPlanes 3D component with bearing layer highlight"
```

---

### Task 2.3: Integrate SoilPlanes into SceneCanvas + View3DPage

**Files:**
- Modify: `client/src/components/three/SceneCanvas.tsx`
- Modify: `client/src/pages/View3DPage.tsx`

- [ ] **Step 1: Add SoilPlanes to SceneCanvas**

In `SceneCanvas.tsx`, import SoilPlanes and add it to the scene:

```typescript
import SoilPlanes from './SoilPlanes';
import GroundPlane from './GroundPlane';

// Inside the Suspense, before PileLayer, add:
<GroundPlane bounds={props.sceneData.bounds} />
{props.sceneData.soil_planes?.length > 0 && (
  <SoilPlanes
    planes={props.sceneData.soil_planes}
    supportLayer={props.sceneData.support_layer}
    bounds={props.sceneData.bounds}
  />
)}
```

- [ ] **Step 2: Update View3DPage legend to include soil layers**

Add a soil layer count to the info overlay in `View3DPage.tsx`:

```typescript
// In the info overlay div, change to:
{sceneData
  ? `桩: ${sceneData.piles.length} · 土层: ${sceneData.soil_planes?.length || 0} · 持力层: ${sceneData.support_layer || '未设'}`
  : '加载中...'}
```

- [ ] **Step 3: Commit**

```bash
git add client/src/components/three/SceneCanvas.tsx client/src/pages/View3DPage.tsx
git commit -m "feat: integrate soil planes into 3D scene"
```

---

## Feature 3: Hover Enhancement + Bottom Detail Panel

### Task 3.1: Enhance PileLayer Hover Data

**Files:**
- Modify: `client/src/components/three/PileLayer.tsx`

- [ ] **Step 1: Pass richer hover info (pile type + diameter)**

In `PileLayer.tsx`, update `handlePointerMove`:

```typescript
const handlePointerMove = useCallback(
  (e: ThreeEvent<PointerEvent>) => {
    e.stopPropagation();
    const d = e.object.userData;
    onHover(`${d.id} | ${d.pileType} | ${d.diameter}mm`);
  },
  [onHover]
);
```

- [ ] **Step 2: Commit**

```bash
git add client/src/components/three/PileLayer.tsx
git commit -m "feat: enhance hover tooltip with pile type and diameter"
```

---

### Task 3.2: Create PileDetailPanel Component

**Files:**
- Create: `client/src/components/three/PileDetailPanel.tsx`

- [ ] **Step 1: Write PileDetailPanel.tsx**

```typescript
import { Collapse, Descriptions, Table } from 'antd';
import type { PredictionResult } from '../../api/client';

interface PileDetailPanelProps {
  prediction: PredictionResult | null;
  visible: boolean;
}

const PileDetailPanel: React.FC<PileDetailPanelProps> = ({ prediction, visible }) => {
  if (!visible || !prediction) return null;

  const layerColumns = [
    { title: '土层', dataIndex: 'layer', key: 'layer' },
    { title: '顶标高(m)', dataIndex: 'top', key: 'top', render: (v: number) => v?.toFixed(2) ?? '—' },
    { title: '底标高(m)', dataIndex: 'bottom', key: 'bottom', render: (v: number) => v?.toFixed(2) ?? '—' },
    { title: '层厚(m)', dataIndex: 'thickness', key: 'thickness', render: (v: number) => v?.toFixed(2) ?? '—' },
  ];

  const layerData = prediction.土层排序.map((name, i) => {
    const top = prediction.土层预测[name];
    const nextName = prediction.土层排序[i + 1];
    const bottom = nextName ? prediction.土层预测[nextName] : prediction.土层底标高预测[name];
    const thickness = top - bottom;
    return {
      key: name,
      layer: name + (name === prediction.持力层顶标高 ? ' (持力层)' : ''),
      top,
      bottom,
      thickness: thickness > 0 ? thickness : 0,
    };
  });

  return (
    <div style={{
      borderTop: '2px solid #1890ff', background: '#fff', padding: '12px 24px',
      maxHeight: 200, overflowY: 'auto'
    }}>
      <Collapse
        size="small"
        items={[{
          key: 'detail',
          label: <strong>{prediction.桩号} — 详细信息</strong>,
          children: (
            <div>
              <Descriptions size="small" column={6}>
                <Descriptions.Item label="桩号">{prediction.桩号}</Descriptions.Item>
                <Descriptions.Item label="桩型">{prediction.桩型}</Descriptions.Item>
                <Descriptions.Item label="桩径">{prediction.桩径}mm</Descriptions.Item>
                <Descriptions.Item label="X坐标">{prediction.X坐标.toFixed(1)}</Descriptions.Item>
                <Descriptions.Item label="Y坐标">{prediction.Y坐标.toFixed(1)}</Descriptions.Item>
                <Descriptions.Item label="桩顶标高">{prediction.桩顶标高?.toFixed(2) ?? '—'} m</Descriptions.Item>
                <Descriptions.Item label="持力层顶标高">{prediction.持力层顶标高?.toFixed(2) ?? '—'} m</Descriptions.Item>
                <Descriptions.Item label="进入持力层深度">{prediction.持力层进入深度?.toFixed(2) ?? '—'} m</Descriptions.Item>
              </Descriptions>
              <Table
                columns={layerColumns}
                dataSource={layerData}
                size="small"
                pagination={false}
                style={{ marginTop: 8 }}
                rowClassName={(record) =>
                  record.layer.includes('持力层') ? 'bearing-row' : ''
                }
              />
            </div>
          ),
        }]}
        defaultActiveKey={['detail']}
      />
    </div>
  );
};

export default PileDetailPanel;
```

- [ ] **Step 2: Commit**

```bash
git add client/src/components/three/PileDetailPanel.tsx
git commit -m "feat: add pile detail bottom panel component"
```

---

### Task 3.3: Integrate Bottom Panel into View3DPage

**Files:**
- Modify: `client/src/pages/View3DPage.tsx`

- [ ] **Step 1: Add PileDetailPanel to View3DPage**

In `View3DPage.tsx`, import and add PileDetailPanel below the 3D canvas area:

```typescript
import PileDetailPanel from '../components/three/PileDetailPanel';

// Get currentPrediction from store:
const currentPrediction = usePileStore((s) => s.currentPrediction);

// Add panelVisible state:
const [panelVisible, setPanelVisible] = useState(false);

// In handlePileClick, after setting prediction:
setPanelVisible(true);

// Add PileDetailPanel at the bottom of the component, after the canvas div:
<PileDetailPanel prediction={currentPrediction} visible={panelVisible} />
```

Full modified component structure:

```typescript
const View3DPage = () => {
  // ... existing state ...
  const [panelVisible, setPanelVisible] = useState(false);
  const currentPrediction = usePileStore((s) => s.currentPrediction);

  // ... existing loadScene, useEffect ...

  const handlePileClick = async (pileData: any) => {
    setSelectedPileId(pileData.id);
    setPanelVisible(true);
    try {
      const res = await predictSingle(pileData.id);
      if (res.data.ok) {
        setPrediction(res.data.result);
      }
    } catch {
      // prediction load failed
    }
  };

  return (
    <div style={{ position: 'relative', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Top toolbar (unchanged) */}
      <div style={{ ... }}>
        ...
      </div>

      {/* 3D Canvas area */}
      <div style={{ flex: 1, position: 'relative' }}>
        {/* hover tooltip, info overlay, legend (unchanged) */}
        ...
        {sceneData ? (
          <SceneCanvas ... />
        ) : (
          <div style={{ ... }}>请先导入地勘和桩基数据，然后点击刷新</div>
        )}
      </div>

      {/* Bottom detail panel */}
      <PileDetailPanel prediction={currentPrediction} visible={panelVisible} />
    </div>
  );
};
```

- [ ] **Step 2: Commit**

```bash
git add client/src/pages/View3DPage.tsx
git commit -m "feat: integrate bottom detail panel into 3D view page"
```

---

### Task 3.4: Add Bearing Layer Row Highlight CSS

**Files:**
- Modify: `client/src/index.css` (or add inline style)

- [ ] **Step 1: Add bearing row highlight style**

Add to `client/src/index.css` (check if file exists, create if not):

```css
.bearing-row {
  background-color: #fff7e6 !important;
  font-weight: 600;
}
```

- [ ] **Step 2: Commit**

```bash
git add client/src/index.css
git commit -m "style: add bearing layer row highlight in detail panel"
```

---

### Task 3.5: Final Integration Build & Verification

- [ ] **Step 1: Build frontend**

```bash
cd client && npm run build
```

Verify TypeScript compilation succeeds with zero errors.

- [ ] **Step 2: Start server and test end-to-end**

```bash
python start.py
```

Manual verification checklist:
1. Open http://localhost:8000 → should see project selection page
2. Enter default project → should see DataPage with empty state (no piles)
3. Import geo data → layers appear in settings
4. Import pile data → 760 piles appear in table
5. Go to 3D view → soil planes visible, different colors, bearing layer highlighted
6. Hover over a pile → tooltip shows "桩号 | 桩型 | 桩径mm"
7. Click a pile → pile highlights orange, bottom panel shows details
8. Switch projects → data isolated

- [ ] **Step 3: Commit any remaining fixes**

```bash
git add -A
git commit -m "fix: final integration fixes and verification"
```
