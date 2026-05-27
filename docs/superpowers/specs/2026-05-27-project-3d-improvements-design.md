# 项目管理系统 + 3D 视图增强 设计文档

日期: 2026-05-27

## 一、项目管理系统

### 目标

解决数据库残留数据导致"未导入时显示 760 根桩"的问题，引入多项目独立管理。

### 方案

多数据库文件隔离：每个项目 = 一个独立 SQLite 文件。

### 数据层

```
projects/                       # 新增目录
├── _index.json                 # 项目索引 [{"id":"uuid","name":"项目名","created_at":"ISO","db_path":"..."}]
├── <project_id_1>.db
└── <project_id_2>.db
```

- `_index.json`：启动时加载，运行时内存中维护
- 每个 `.db` 文件包含现有 7 张表，表结构不变
- 首次启动：自动迁移旧 `pile_app.db` → 创建"默认项目"

### 后端改动

| 文件 | 改动 |
|------|------|
| `server/database.py` | 新增 `switch_database(project_id)` → 动态更换 SQLAlchemy engine；新增 `get_active_db_path()` |
| `server/api/project.py` | 新增 `POST /api/project` 创建, `DELETE /api/project/{id}` 删除, `PUT /api/project/{id}/activate` 切换 |
| `server/main.py` | 启动时初始化项目系统，检查/创建默认项目 |
| 现有所有 API | 不变——每次只有一个活跃连接，SQLAlchemy session 自动指向活跃 db |

### 前端改动

| 文件 | 改动 |
|------|------|
| `client/src/store/useProjectStore.ts` | 扩展：projects 列表、activeProject、createProject、switchProject |
| `client/src/components/layout/Sidebar.tsx` | 增加项目名称显示 + 切换/创建入口 |
| 新建 `ProjectPage.tsx` | 项目列表页面（创建、选择、删除） |
| `App.tsx` | 路由：无活跃项目 → 项目选择页，有项目 → 正常工作区 |

### 流程

1. 打开应用 → GET /api/project → 获取项目列表 + 活跃项目
2. 无项目 → 显示项目创建页 → 创建后自动激活
3. 有项目 → 侧边栏显示项目名，点击可切换
4. 新建项目 → 创建空 `.db` + 初始化 7 张空表

---

## 二、3D 土层可视化

### 目标

在 3D 场景中显示土层分界面，用不同颜色标明，着重突出桩基进入持力层的深度。

### 后端改动

`server/services/predict_service.py` 的 `get_scene_data()` 返回增加 `soil_planes` 字段：

```python
soil_planes: [
  {"name": "填土", "elevation": 3.5, "color": "#c8b68e"},
  {"name": "粉质黏土", "elevation": -2.1, "color": "#b5a67c"},
  ...
]
```

计算方式：对每个土层，取所有地勘钻孔该层顶标高的平均值作为参考平面标高。按标高降序排列。

### 前端改动

| 文件 | 改动 |
|------|------|
| 新建 `client/src/components/three/SoilPlanes.tsx` | 渲染半透明水平面，每层一个 Plane |
| `client/src/components/three/SceneCanvas.tsx` | 引入 SoilPlanes，渲染在桩层下方 |
| `client/src/api/client.ts` | 更新 SceneDataResponse 类型，增加 soil_planes 字段 |

### SoilPlanes 组件规格

- 每个土层：一个 `PlaneGeometry(50, 50)` 水平放置（rotation.x = -Math.PI/2）
- 材质：`MeshBasicMaterial({ color, transparent: true, opacity: 0.25, side: DoubleSide })`
- 持力层特殊处理：opacity 0.45 + 更醒目的颜色（如亮橙色边框效果，用 Ring 或 EdgesGeometry 实现）
- 所有面放在 `bounds.z[0]` 到 `bounds.z[1]` 范围内

---

## 三、桩悬停增强 + 点击底部详情面板

### 目标

- 悬停桩体时 tooltip 显示更多信息（桩号 + 桩径 + 桩型）
- 点击桩体后在页面底部展开详情面板

### 前端改动

| 文件 | 改动 |
|------|------|
| `client/src/components/three/PileLayer.tsx` | onPointerMove 传递更多 userData（桩径、桩型）到 hover 回调 |
| `client/src/pages/View3DPage.tsx` | 底部增加 PileDetailPanel，点击桩时展开 |
| 新建 `client/src/components/three/PileDetailPanel.tsx` | 底部面板组件 |
| `client/src/api/client.ts` | 可能需要更新类型（scenePile 增加更多字段） |

### PileDetailPanel 组件规格

- 位置：3D 场景下方，高度约 200px，可折叠
- 内容分三区：
  1. **基本信息行**：桩号、坐标(X,Y)、桩型、桩径(mm)、桩顶标高(m)
  2. **土层剖面表**：层名 | 顶标高 | 底标高 | 层厚 | 进入持力层深度
  3. **承载力**（如有）：Qsk, Qpk, Quk, Ra
- 数据来源：`usePileStore.currentPrediction`（点击时调用 predictSingle 填充）
- 空状态：未选中桩时显示"点击桩体查看详细信息"

### PileLayer 悬停增强

当前 `onPointerMove` 只传 `id`，改为传 `{id, pileType, diameter, topElev}`，tooltip 显示：
```
桩号: ZJ-001
桩型: 灌注桩
桩径: 800mm
```

---

## 四、实施顺序

1. **项目管理系统**：基础架构变更，最先做
2. **3D 土层**：依赖项目系统完成后进行
3. **悬停增强 + 底部面板**：独立改动，可与 3D 土层并行
