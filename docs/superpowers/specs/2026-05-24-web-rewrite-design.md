# 桩基土层预测系统 — Web 化重写设计文档

**日期**: 2026-05-24  
**状态**: design-approved, pending-plan  
**源需求**: 桩基土层预测系统_网页版重构与全面优化建议报告.docx

---

## 1. 目标

将现有 Tkinter 桌面程序重写为浏览器端 Web 应用，保持全部现有功能，同时升级为前后端分离的专业工程软件架构。

## 2. 技术选型

| 层 | 技术 | 理由 |
|----|------|------|
| 前端 | React 18 + TypeScript + Vite | 组件化开发，静态类型安全，快速HMR |
| UI 库 | Ant Design 5 | 专业表格/表单/弹窗组件，适合工程软件 |
| 状态管理 | Zustand | 轻量，无 boilerplate，适合中型应用 |
| 3D 渲染 | React-Three-Fiber + Drei | Three.js 的 React 封装，状态联动自然 |
| 数据表格 | AG Grid Community | 高性能表格，支持排序筛选 |
| 2D 图表 | Recharts | React 原生图表，替代 Matplotlib |
| 后端 | FastAPI + Uvicorn | 高性能异步 Python，自动生成 OpenAPI 文档 |
| ORM | SQLAlchemy + SQLite | 单文件数据库，零运维 |
| 计算引擎 | 复用现有 core/ 模块 | prediction.py, bearing_capacity.py 几乎不变 |
| 文件处理 | Pandas + Openpyxl | Excel 读写 |

## 3. 系统架构

```
浏览器 localhost:8000
├── React SPA (Vite 构建)
│   ├── AppLayout (Shell)
│   │   ├── Sidebar (项目导航树 + 菜单)
│   │   ├── WorkArea (Tab切换的4个页面)
│   │   ├── DrawerPanel (桩详情/属性面板)
│   │   └── StatusBar (系统状态/消息)
│   └── Zustand Store (全局状态)
│
FastAPI 后端 (同进程)
├── /api/*  REST 端点 (18个)
├── /       静态文件托管 (React build)
├── server/services/  业务层
├── server/models/    SQLAlchemy 模型
├── server/core/      复用现有计算引擎
└── server/database.py  SQLite 连接
```

### 3.1 目录结构

```
桩基智能体/
├── server/                  # FastAPI 后端
│   ├── main.py              # 应用入口，挂载静态文件
│   ├── database.py          # SQLAlchemy 引擎 + session
│   ├── api/                 # 路由层
│   │   ├── __init__.py
│   │   ├── project.py       # GET /api/project
│   │   ├── geo.py           # 地勘数据 CRUD
│   │   ├── piles.py         # 桩基数据 CRUD
│   │   ├── predict.py       # 预测端点
│   │   ├── measured.py      # 实测数据端点
│   │   ├── settings.py      # 设置端点
│   │   ├── bearing.py       # 承载力计算端点
│   │   └── export.py        # 导出端点
│   ├── models/              # SQLAlchemy ORM
│   │   ├── __init__.py
│   │   ├── geo.py
│   │   ├── pile.py
│   │   ├── prediction.py
│   │   ├── measured.py
│   │   ├── settings.py
│   │   └── soil_params.py
│   ├── services/            # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── geo_service.py
│   │   ├── predict_service.py
│   │   ├── bearing_service.py
│   │   └── export_service.py
│   ├── core/                # 现有计算引擎 (最小修改)
│   │   ├── __init__.py
│   │   ├── prediction.py    # → 从 E:\A桩基智能体\core\ 复制
│   │   └── bearing_capacity.py
│   └── schemas.py           # Pydantic 请求/响应模型
├── client/                  # React 前端
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── api/             # API 调用封装 (axios)
│   │   ├── store/           # Zustand stores
│   │   │   ├── useProjectStore.ts
│   │   │   ├── usePileStore.ts
│   │   │   └── useSettingsStore.ts
│   │   ├── components/      # 共享组件
│   │   │   ├── layout/      # AppLayout, Sidebar, TabBar...
│   │   │   ├── charts/      # 2D柱状图 (Recharts)
│   │   │   ├── table/       # AG Grid 封装
│   │   │   └── three/       # R3F 3D组件
│   │   │       ├── SceneCanvas.tsx
│   │   │       ├── PileLayer.tsx
│   │   │       ├── GroundPlane.tsx
│   │   │       ├── Gizmo.tsx
│   │   │       ├── Toolbar.tsx
│   │   │       └── MeasureTool.tsx
│   │   └── pages/
│   │       ├── DataPage.tsx
│   │       ├── PredictPage.tsx
│   │       ├── View3DPage.tsx
│   │       └── RecordPage.tsx
│   ├── vite.config.ts
│   └── package.json
├── start.py                  # 一键启动脚本
└── assets/                   # (保留原始 scene.html 供参考)
```

## 4. 数据库设计 (SQLite)

### 4.1 表结构

**geo_layers** — 勘探孔分层数据
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| hole_id | TEXT | 孔号 |
| x, y | REAL | 坐标 |
| layer_name | TEXT | 土层名称 |
| top_elev | REAL | 土层顶标高 |
| thickness | REAL | 土层厚度 |
| bottom_elev | REAL | 土层底标高 (计算列) |

**piles** — 桩基数据
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| pile_no | TEXT UNIQUE | 桩号 |
| x, y | REAL | 坐标 |
| diameter | REAL | 桩径(mm) |
| pile_type | TEXT | 桩型 |

**predictions** — 预测结果缓存
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| pile_no | TEXT FK | |
| layer_name | TEXT | |
| top_elev_pred | REAL | 预测顶标高 |
| bottom_elev_pred | REAL | 预测底标高 |
| method | TEXT | 克里金法/IDW |
| created_at | TEXT | |

**measured** — 实测数据 (独立存储，不再写回 geo_layers)
| 列 | 类型 | 说明 |
|----|------|------|
| id | INTEGER PK | |
| pile_no | TEXT FK | |
| layer_name | TEXT | |
| measured_elev | REAL | |
| actual_depth | REAL | 实测进入持力层深度 |
| recorded_at | TEXT | |

**settings** — 系统设置 (key-value)
| 列 | 类型 |
|----|------|
| key | TEXT PK |
| value | TEXT |

**soil_params** — 土层承载力参数
| 列 | 类型 |
|----|------|
| id | INTEGER PK |
| layer_name | TEXT UNIQUE |
| qsik | REAL |
| qpk | REAL |

**operation_logs** — 操作日志 (新增)
| 列 | 类型 |
|----|------|
| id | INTEGER PK |
| action | TEXT |
| detail | TEXT |
| created_at | TEXT |

### 4.2 与旧 JSON 的关键差异

- **实测数据独立存储** (measured 表)，不再调用 `add_measured_pile_as_geo_hole()` 写回 geo_layers。修复报告中指出的数据污染问题。
- **预测结果缓存** (predictions 表)，避免每次页面加载都重新计算 760 根桩。
- **不再有 `project_full_data.json`**，所有数据通过 SQLite 持久化。

## 5. API 设计

共 18 个 REST 端点，8 个模块。

### 5.1 端点列表

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 项目 | GET | `/api/project` | 项目摘要 (数据量、设置状态) |
| 地勘 | POST | `/api/geo/upload` | 上传 Excel，写入 geo_layers |
| 地勘 | GET | `/api/geo/layers` | 土层名称列表 |
| 地勘 | GET | `/api/geo/holes` | 勘探孔列表 (分页) |
| 桩基 | POST | `/api/piles/upload` | 上传 Excel，写入 piles |
| 桩基 | GET | `/api/piles` | 桩列表 (分页/搜索/筛选) |
| 桩基 | GET | `/api/piles/{pile_no}` | 单桩详情含预测 |
| 预测 | POST | `/api/predict/single/{pile_no}` | 单桩预测，写入 predictions |
| 预测 | POST | `/api/predict/all` | 全量批量预测 |
| 预测 | GET | `/api/predict/scene-data` | 3D场景数据 (IDW快速模式) |
| 实测 | POST | `/api/measured` | 录入实测数据 |
| 实测 | GET | `/api/measured/{pile_no}` | 查询某桩实测 |
| 设置 | GET | `/api/settings` | 获取所有设置 |
| 设置 | PUT | `/api/settings` | 更新设置 |
| 承载力 | POST | `/api/bearing/calc/{pile_no}` | 单桩承载力计算 |
| 承载力 | POST | `/api/bearing/params` | 上传土层参数 |
| 导出 | GET | `/api/export/predictions` | 导出全部预测 Excel |
| 导出 | GET | `/api/export/measured-holes` | 导出实测勘探孔 |

### 5.2 关键原则

- API 层只做薄封装：校验输入 → 调用 services → 返回 JSON
- 现有 `core/prediction.py` 和 `core/bearing_capacity.py` 的 PredictEngine 和 BearingCalc 类保持不变，仅移除对 `DataStore` 类的直接依赖，改为接受 DataFrame 参数
- 文件上传用 multipart/form-data
- 大数据导出用 StreamingResponse

## 6. 前端设计

### 6.1 布局 (Abaqus 风格)

```
┌──────────┬──────────────────────────────────────┐
│ Sidebar  │  TabBar: [数据管理] [预测实测] [3D] [记录] │
│ 260px    ├──────────────────────────────────────┤
│          │                                      │
│ 项目导航  │         中央工作区 (flex: 1)             │
│ · 数据    │         当前 Tab 对应的 Page            │
│ · 预测    │                                      │
│ · 3D      │                                      │
│ · 记录    │                                      │
│          │                                      │
├──────────┴──────────────────────────────────────┤
│ StatusBar: 已加载238孔 760桩 | 持力层:xxx | 算法:克里金 │
└──────────────────────────────────────────────────┘
```

- 点击桩/勘探孔 → 右侧弹出 Drawer (宽度380px) 显示详情面板
- Drawer 包含：属性信息、预测结果、实测对比、承载力数据、历史记录
- 底部 StatusBar 常驻显示系统状态

### 6.2 四个页面

| 页面 | 核心组件 | 功能 |
|------|---------|------|
| DataPage | FileUploader, PileTable(AG Grid), SettingsPanel, MethodSelector | 导入数据、持力层设置、插值方法、预警阈值 |
| PredictPage | PileSelector, LayerChart(Recharts), MeasuredForm, ErrorBadge | 单桩选择→预测→2D柱状图、实测录入、误差预警 |
| View3DPage | SceneCanvas(R3F), Toolbar, PileLayer, GroundPlane, MeasureTool | 全3D场景、悬停Tooltip、点击选中→Drawer、视角切换 |
| RecordPage | DrivingRecordCard, BearingCalcSheet, ConstructionLog | 打桩记录生成、承载力计算书、施工日志 |

### 6.3 状态管理 (Zustand)

三个核心 Store：
- **useProjectStore**: geoLoaded, pileLoaded, dataSummary, refresh()
- **usePileStore**: selectedPileNo, predictionResult, measuredData
- **useSettingsStore**: supportLayer, thresholds, interpMethod

### 6.4 前端依赖

```json
{
  "react": "^18.3",
  "react-dom": "^18.3",
  "antd": "^5.20",
  "@ant-design/icons": "^5.4",
  "zustand": "^4.5",
  "@react-three/fiber": "^8.17",
  "@react-three/drei": "^9.110",
  "three": "^0.168",
  "ag-grid-react": "^32.0",
  "ag-grid-community": "^32.0",
  "recharts": "^2.12",
  "axios": "^1.7",
  "dayjs": "^1.11"
}
```

## 7. 3D 视图功能 (分阶段)

### V1 — 本次重写必需 (对应现有 scene.html 功能 + 基础交互升级)
1. 760根桩体圆柱 (按桩型着色) + 图例
2. 半透明地面参考面 + 持力层参考面
3. 悬停识别 (Raycaster) → Html Tooltip 显示桩号
4. 点击选中 → 轮廓高亮 (OutlinePass / emissive) → 右侧 Drawer 联动
5. 视角切换按钮 (正视/俯视/侧视/重置) + 平滑相机动画
6. 右上角 Gizmo 坐标轴 (Drei GizmoHelper)
7. OrbitControls (旋转/平移/缩放)
8. 响应式画布

### V2 — 报告核心建议
9. 图层显隐控制面板 (桩体/地面/持力层面/勘探孔)
10. 透明度调节滑块
11. 剖切面工具 (ClippingPlanes, 可拖拽)
12. 测量距离/标高工具
13. 截图导出 (canvas.toDataURL)

### V3 — 后续迭代
14. 区域筛选显示 (按桩号范围过滤)
15. 勘探孔3D显示 (分段圆柱, 真实土层颜色)

## 8. 启动脚本

`start.py`:
```python
import uvicorn
if __name__ == "__main__":
    uvicorn.run("server.main:app", host="127.0.0.1", port=8000)
```

首次使用需先构建前端:
```bash
cd client && npm install && npm run build
python start.py
# 浏览器打开 http://localhost:8000
```

## 9. 迁移路径

- 现有 Tkinter 代码 (ui/, main.py) **保留不删**，可在 `legacy/` 目录中保留
- 现有 core/ 模块 **复制**到 server/core/，最小化修改（移除 DataStore 耦合，改为接受 DataFrame）
- 现有 assets/scene.html **保留**供参考，3D 逻辑完全用 R3F 重写
- 现有 project_full_data.json 通过一次性迁移脚本导入 SQLite
- 所有新代码放在 server/ 和 client/ 目录，不影响现有文件

## 10. 风险与约束

- **克里金插值性能**: 批量预测 760 根桩时 OrdinaryKriging 较慢，沿用 `predict_one_fast()` 的 IDW 模式用于 3D 场景数据生成
- **节点环境**: 开发阶段需要 Node.js 构建前端，交付时只需 Python + 浏览器
- **SQLite 并发**: 单用户场景无并发问题，未来多用户可无缝迁移到 PostgreSQL
- **不再使用的依赖将被移除**: tkinter, matplotlib 不再作为运行时依赖
