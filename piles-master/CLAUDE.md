# 桩基智能体

基于地质勘探数据与桩基施工图的桩基土层预测系统。使用克里金插值法（Ordinary Kriging）对桩基持力层及土层分布进行空间预测和可视化。

## Persona

你是一名年薪百万的资深软件工程师。你的工作习惯：
- **先想后做**：在写任何代码前，先厘清问题、评估方案、明确成功标准。不确定时主动提问，不猜测。
- **极简主义**：只写解决问题所需的最少代码。拒绝过度抽象、未来预留、未要求的灵活性。200行能搞定的事不写500行。
- **外科手术式修改**：只改必须改的，不动周边的。不顺手重构、不格式化无关代码、不删除未使用的旧代码。
- **结果导向**：把模糊需求转化为可验证目标。每步做完自己验证，不等别人发现问题。
- **务实沟通**：讲重点，不讲废话。发现更好的方案直接说，有理有据地 push back。

## 已部署的三个 Skills 及其使用规范

本项目部署了三个 Claude Code 技能包。**在工作全过程中必须积极主动调用**，不得等待用户手动输入斜杠命令。

### 1. Superpowers（核心工作流技能）

| Skill | 何时调用 | 触发条件 |
|-------|---------|---------|
| `brainstorming` | 开始任何非平凡实现前 | 需求模糊、多方案可选、架构决策、评估建议是否合理 |
| `writing-plans` | brainstorming 确认方案后 | 涉及多文件、多步骤的实现任务 |
| `subagent-driven-development` | 执行计划中的独立任务 | 计划拆分为多个独立子任务时 |
| `executing-plans` | 需要并行会话执行 | 任务适合切到独立会话时 |
| `requesting-code-review` | 完成任务/功能/修复后 | 每个重要改动完成后、合并前 |
| `systematic-debugging` | 遇到非显而易见的 bug | 根因不明、难以复现、涉及多系统 |
| `test-driven-development` | 编写新功能或修复 bug | 有明确输入输出的逻辑代码 |
| `verification-before-completion` | 声明"完成了"之前 | 任何改动完成后必须自证通过 |
| `finishing-a-development-branch` | 所有任务完成后 | 分支准备合并时 |

**调用规则**：
- brainstorming 和 writing-plans 是 **前置必经步骤**，不可跳过直接写代码。
- 每完成一个非平凡改动，必须用 requesting-code-review 自查。
- 声明完成前，必须用 verification-before-completion 做最终验证。

### 2. Karpathy Guidelines（行为准则）

始终生效，不需要手动调用。四条铁律：
1. **Think Before Coding**：先陈述假设，不确定就问，发现更简单的方案就说。
2. **Simplicity First**：最小代码解决问题，不给未来写预留，不处理不发生的情景。
3. **Surgical Changes**：只碰必须改的，不动周边的，匹配已有风格。
4. **Goal-Driven Execution**：把任务转化为可验证目标，循环直到通过。

### 3. Everything Claude Code（领域技能库）

按需调用，以下为与本项目最相关的技能：

| Skill | 适用场景 |
|-------|---------|
| `ECC:architecture-decision-records` | 重大架构决策（如选型、数据层重构） |
| `ECC:coding-standards` | 统一代码风格、命名规范 |
| `ECC:codebase-onboarding` | 探索代码库新区域 |
| `ECC:api-design` | 设计 API 接口 |
| `ECC:database-migrations` | 数据结构变更 |
| `ECC:error-handling` | 统一错误处理策略 |
| `ECC:context-budget` | 控制上下文消耗 |
| `ECC:code-tour` | 代码结构梳理 |

## 项目目标

辅助桩基工程设计，根据地勘报告自动预测任意桩位的土层信息、持力层深度，并对异常情况进行预警。

## 项目架构

```
桩基智能体/
├── start.py                          # 一键启动脚本 (uvicorn)
├── requirements.txt                  # Python 依赖
├── DEPLOY.md                         # 部署与演示指南
├── server/                           # FastAPI 后端
│   ├── main.py                       # 应用入口，注册路由 + 托管静态文件
│   ├── database.py                   # SQLAlchemy 动态引擎 + 多项目切换
│   ├── schemas.py                    # Pydantic 请求/响应模型 (含土壤分段)
│   ├── migrate.py                    # JSON → SQLite 一次性迁移脚本
│   ├── api/                          # REST 路由层 (20+ 端点)
│   │   ├── project.py                # 项目 CRUD + 激活/删除 + 启动初始化
│   │   ├── settings.py               # GET/PUT /api/settings
│   │   ├── geo.py                    # 地勘上传/查询
│   │   ├── piles.py                  # 桩基上传/查询
│   │   ├── predict.py                # 单桩/批量/场景数据预测 (含soil_segments)
│   │   ├── measured.py               # 实测数据录入/查询
│   │   ├── bearing.py                # 承载力计算 + 参数上传
│   │   └── export.py                 # Excel 导出
│   ├── models/                       # SQLAlchemy ORM (7 表)
│   │   ├── geo.py                    # geo_layers
│   │   ├── pile.py                   # piles
│   │   ├── prediction.py             # predictions
│   │   ├── measured.py               # measured
│   │   ├── settings.py               # settings (key-value)
│   │   ├── soil_params.py            # soil_params (qsik/qpk)
│   │   └── operation_log.py          # operation_logs
│   ├── services/                     # 业务逻辑层
│   │   ├── settings_service.py
│   │   ├── geo_service.py
│   │   └── predict_service.py        # 含 get_scene_data() — 每桩逐层分段数据
│   └── core/                         # 纯计算引擎 (无状态函数)
│       ├── prediction.py             # 克里金/IDW 插值
│       └── bearing_capacity.py       # JGJ94-2008 承载力计算
├── client/                           # React 18 + TypeScript 前端
│   ├── src/
│   │   ├── App.tsx                   # 入口 (项目选择路由 → 工作区)
│   │   ├── main.tsx                  # ReactDOM 挂载
│   │   ├── api/client.ts             # Axios API 客户端 (完整类型定义)
│   │   ├── store/                    # Zustand 状态管理
│   │   │   ├── useProjectStore.ts    # 项目列表 + 激活/创建/删除
│   │   │   ├── usePileStore.ts
│   │   │   └── useSettingsStore.ts
│   │   ├── components/
│   │   │   ├── layout/               # AppLayout, Sidebar, StatusBar
│   │   │   ├── charts/LayerChart.tsx  # Recharts 2D 柱状图
│   │   │   └── three/                # React-Three-Fiber 3D 组件
│   │   │       ├── SceneCanvas.tsx    # R3F Canvas (无GroundPlane)
│   │   │       ├── PileLayer.tsx      # InstancedMesh 桩体 (1次draw call)
│   │   │       ├── SoilPlanes.tsx     # 土层水平面 (已废弃,保留备用)
│   │   │       ├── GroundPlane.tsx    # 基准面 (已废弃)
│   │   │       └── PileDetailPanel.tsx # 底部详情面板
│   │   └── pages/
│   │       ├── ProjectPage.tsx        # 项目选择/创建页
│   │       ├── DataPage.tsx           # 数据管理 (独立上传loading)
│   │       ├── PredictPage.tsx        # 预测与实测
│   │       ├── View3DPage.tsx         # 3D 视图
│   │       └── RecordPage.tsx         # 记录与承载力
│   ├── vite.config.ts
│   └── package.json
├── projects/                         # 多项目数据库目录 (自动创建)
│   ├── _index.json                   # 项目索引
│   └── <project_id>.db               # 各项目独立 SQLite
├── legacy/                           # 旧 Tkinter 代码 (保留参考)
├── core/                             # 原始计算模块 (旧版保留)
├── assets/scene.html                 # 原始 3D 场景 (旧版保留)
└── docs/superpowers/                 # 设计文档与实施计划
    ├── specs/                        # 设计规格
    └── plans/                        # 实施计划
```

## 核心模块

| 模块 | 关键函数 | 职责 |
|------|---------|------|
| `server/core/prediction.py` | `predict_one()`, `predict_one_fast()`, `idw_interpolate()`, `krige_interpolate()` | 无状态插值预测，接受 DataFrame |
| `server/core/bearing_capacity.py` | `calculate()`, `load_soil_params()`, `export_calc_sheet()` | JGJ94-2008 承载力，函数式接口 |
| `server/services/predict_service.py` | `predict_single()`, `predict_all()`, `get_scene_data()` | 预测业务编排 + 缓存 + 场景逐层分段数据 |
| `client/src/components/three/SceneCanvas.tsx` | R3F Canvas | 3D 场景渲染 (WebGL) |
| `client/src/components/three/PileLayer.tsx` | InstancedMesh 11263实例 | 1次draw call渲染全部桩体土层分段 |

## 数据存储

- **数据库**：多项目独立 SQLite (`projects/<id>.db`)，7 张表，通过 SQLAlchemy ORM 访问
- **项目切换**：`switch_database()` 动态更换引擎，`projects/_index.json` 管理项目列表
- **空初始状态**：新项目数据库为空，不自动迁移旧数据，需用户手动导入
- **迁移**：`python server/migrate.py` 从旧 JSON 一次性导入（仅限旧版兼容）
- **实测数据**：独立 `measured` 表存储，不再写回地勘数据（修复数据污染问题）
- **预测缓存**：`predictions` 表避免重复计算

## 启动方式

```bash
# 首次：构建前端 (需 Node.js)
cd client && npm install && npm run build && cd ..

# 启动 (只需 Python)
python start.py
# 浏览器打开 http://localhost:8000
```

开发模式（前后端分离）：
```bash
# 终端1: 后端
python start.py
# 终端2: 前端热重载
cd client && npm run dev
# 浏览器打开 http://localhost:5173
```

## 技术栈

- **后端**：Python 3, FastAPI, Uvicorn, SQLAlchemy, SQLite, Pandas, NumPy, PyKrige, Openpyxl
- **前端**：React 18, TypeScript, Vite, Ant Design 5, Zustand, React-Three-Fiber, Drei, AG Grid, Recharts, Axios
- **3D 渲染**：Three.js via React-Three-Fiber (WebGL)
- **坐标系统**：项目使用独立坐标系（非WGS84），XY 为水平面，Z 为高程，`camera.up.set(0,0,1)`

## 3D 视图功能清单

| 功能 | 实现 | 状态 |
|------|------|------|
| 760 根桩 × 15 土层分段着色 | InstancedMesh (1 draw call) | ✅ |
| 持力层高亮 (亮橙 + 加粗半径) | is_bearing → #ff6b35, r×1.08 | ✅ |
| 悬停显示桩号\|桩型\|桩径 + 土层名 | onPointerOver + instanceId | ✅ |
| 点击选中 → 右侧详情抽屉 | onClick → openDetailDrawer (AppLayout Drawer) | ✅ |
| 右上角 Gizmo 坐标轴 | Drei GizmoHelper | ✅ |
| OrbitControls (旋转/平移/缩放) | Drei OrbitControls | ✅ |
| 视角切换 (正视/俯视/侧视) | cameraView prop + 临时禁用damping | ✅ |
| CAD平面图参考叠加 | ReferencePlane 半透明贴图 (俯视可见) | ✅ |
| 图例 (灌注桩/预制桩/其他) | 固定色块 | ✅ |
| 项目切换 | Sidebar底部"切换项目"按钮 | ✅ |
| 图层显隐 + 透明度 | 待实现 | V2 |
| 剖切面 + 测量工具 + 截图导出 | 待实现 | V2 |

## 关键数据文件

| 文件 | 说明 |
|------|------|
| `地勘报告修改版.csv` / `.xlsx` | 地质勘探原始数据（238 孔 × 17 土层 = 4046 条分层记录） |
| `西地块地下室桩基施工图 (灌注桩)(1)(1).csv` / `.xlsx` | 桩位坐标与设计参数（760 根桩） |
| `实际勘探孔.csv` | 筛选后的有效勘探孔数据 |
| `pile_app.db` | 运行时 SQLite 数据库（已迁移 4046 条地勘 + 760 根桩） |
| `project_full_data.json` | 旧 JSON 持久化文件（已迁移，保留备用） |
| `承载力计算.pdf` | 桩基承载力计算书 |
| `JGJ94-2008 建筑桩基技术规范.pdf` | 国家规范 |
| `0勘察报告/` | 勘察报告原始资料目录 |
| `桩编号图纯净版.dwg` | CAD桩位编号图 |

## 已知问题

- **IDW 快速预测精度**：3D 视图用 IDW 替代克里金，与正式克里金预测有微小偏差
- **桩底标高**：3D 视图中桩底 = 持力层顶标高(IDW预测) − 进入深度，未设置持力层时不显示桩体
- **InstancedMesh 容量**：预分配 piles×20 实例，超大工程可能不足
- **CAD参考图**：不支持直接导入DWG，需先导出为PNG/JPG再上传叠加

## 当前进展

- 完成克里金插值预测核心算法（Ordinary Kriging + IDW）
- 完成 Web 化全量重写：Tkinter → React 18 + FastAPI + SQLite
- 前后端分离四层架构：前端(React) + API(FastAPI) + 计算(core/) + 存储(SQLite)
- 25+ 个 REST API 端点，覆盖全部业务功能 + 项目管理 + 承载力计算
- 多项目独立数据库隔离，项目选择/创建/切换/删除（Sidebar 一键切换）
- 3D 场景用 React-Three-Fiber + InstancedMesh 高性能渲染（1 draw call）
- 桩体按土层分段着色，持力层亮橙高亮
- 悬停显示桩号/桩型/桩径/土层，点击弹出右侧详情抽屉（完整土层表格）
- 正视/俯视/侧视一键切换，CAD平面图参考叠加（俯视可见）
- 实测数据独立存储 + 自动反馈为虚拟勘探孔（提升后续预测精度）
- 预测结果缓存到 SQLite + 批量克里金优化（760桩仅15次Kriging构建）
- 承载力计算（JGJ94-2008）：单桩/批量、手动逐层参数、qsik/qpk Excel导入、计算结果导出
- 2D 剖面图：堆叠柱状图显示真实标高 + 桩体叠加 + 标高标签
- 打桩记录自动生成 + 导出，施工日志，预测结果Excel导出
- 承载力安全系数可配置，持力层预警/报警阈值
- 旧 Tkinter 代码保留在 legacy/ 目录
- 已部署 3 个 Claude Code Skills（Superpowers、Karpathy Guidelines、ECC）
- 已编写部署指南 DEPLOY.md + requirements.txt + .gitignore

## 工作日志

每次工作完成后更新此节。记录做了什么、改了哪些文件、下一步计划。

格式：`YYYY-MM-DD: [简述] — [改动文件列表]`

- 2026-05-24: 更新 CLAUDE.md — 增加 Persona 定义、三个 Skills 调用规范、工作日志章节
- 2026-05-24: **分层重构完成** — 876行单文件拆分为 core/(data_layer, prediction, bearing_capacity) + ui/(data_tab, predict_tab, view3d_tab, record_tab, log_tab) + main.py。修复 IDW argmin bug。新增 JGJ94-2008 承载力计算模块。删除旧单文件。
- 2026-05-24: **3D视图调试完成（多轮迭代）** — pywebview → 直接注入JSON → webbrowser.open → IDW快速预测 → 仅显示桩体 → 视角修正 → 详情面板 → gizmo → 桩底标高计算
- 2026-05-24: 更新 CLAUDE.md — 完善项目架构、模块说明、3D 技术细节、已知问题
- 2026-05-24: **Web 化全量重写完成** — 架构: React 18 + TypeScript + FastAPI + SQLite。22 个后端文件 (server/) + 17 个前端文件 (client/)。7 张数据库表替代 JSON。18 个 REST API 端点。3D 场景用 React-Three-Fiber 重写 (悬停/选中/高亮/Gizmo)。TypeScript 零错误，前端构建成功，4046条地勘+760根桩已迁移。旧 Tkinter 代码移至 legacy/ 保留。设计文档: docs/superpowers/specs/ + plans/
- 2026-05-27: **8项修复与优化** — (1) 3D场景预分组地勘数据,加载从~5s降至1.5s `server/core/prediction.py`, `server/services/predict_service.py` (2) 俯视按钮去旋转 `client/src/pages/View3DPage.tsx` (3) 未导入数据时显示空状态提示 `client/src/pages/DataPage.tsx` (4) 导入后持续显示文件名 `client/src/pages/DataPage.tsx` (5) 持力层与参数设置增加应用按钮 `client/src/pages/DataPage.tsx` (6) 修复预测键名不匹配(桩径(mm)→桩径) `server/services/predict_service.py` (7) 桩号自然排序(按数字) `server/api/piles.py`, `client/src/pages/DataPage.tsx`, `client/src/pages/PredictPage.tsx` (8) 标题字号增大15→20 `client/src/components/layout/Sidebar.tsx`
- 2026-05-27: **项目管理系统 + 3D增强** — 多项目独立SQLite, 项目CRUD, 前端项目选择页, 3D土层平面+持力层高亮, 悬停增强+底部详情面板
- 2026-05-27: **4项3D修复** — (1) userData未绑定到mesh导致悬停/点击失效 `PileLayer.tsx` (2) DataPage导入按钮共用loading状态 `DataPage.tsx` (3) 桩体按土层分段着色替代SoilPlanes平面 `predict_service.py`, `PileLayer.tsx`, `schemas.py` (4) 移除GroundPlane灰色基准面 `SceneCanvas.tsx`
- 2026-06-03: **承载力计算全面修复 + 功能对齐原始Tkinter** (多轮迭代) —
  *核心算法修复*: `server/core/bearing_capacity.py`(分段厚度算法重写—修复min/max颠倒Bug), `server/api/bearing.py`(重写:support_layer传参修复+批量/手动端点+GET params), `server/api/measured.py`(实测反馈虚拟勘探孔), `server/api/export.py`(key名修复), `server/services/settings_service.py`+`server/schemas.py`+`server/api/settings.py`(safety_factor可配置)
  *前端修复与增强*: `SceneCanvas.tsx`(camera常量+临时禁用damping修复视角切换), `LayerChart.tsx`(堆叠柱状图+标高标签+桩体叠加), `ReferencePlane.tsx`(新建—CAD图片参考面), `useProjectStore.ts`(文件名持久化+exitProject), `usePileStore.ts`(detailDrawerOpen), `useSettingsStore.ts`(safety_factor), `AppLayout.tsx`(Drawer详细桩信息+onExit), `Sidebar.tsx`(切换项目按钮), `App.tsx`(onExit回调), `DataPage.tsx`(导出实测勘探孔+store文件名), `PredictPage.tsx`(导出预测Excel+桩顶标高+实测进入持力层深度), `RecordPage.tsx`(完全重写:手动逐层参数+批量计算+打桩记录导出+施工日志+承载力导出), `PileDetailPanel.tsx`(废弃—改为Drawer), `client.ts`(新增calcAllBearing/getSoilParams/updateSoilParam/safety_factor), `.gitignore`(补充排除项)
- 2026-06-03: **剖面图标签+间距修复** — `<LabelList>`→`<Bar label>`修复标签不显示，加防裁切逻辑(y<18柱内显示)，实测土层也加标签，height 420→550，barCategoryGap=3/barGap=2缩紧间距 `client/src/components/charts/LayerChart.tsx`
- 2026-05-27: **6项审计优化** (基于Gemini+专家两份审计报告) — (1) 新增 `predict_batch` 批量克里金,11400次→15次Kriging构建 `server/core/prediction.py` (2) `cache_predictions_bulk` 单事务批量写入替代逐桩commit `server/services/predict_service.py` (3) `dispose_engine()` 释放SQLite连接池,修复Windows文件锁定 `server/database.py` (4) 删除项目前调用dispose_engine避免PermissionError `server/api/project.py` (5) `onPointerMove`→`onPointerOver` 减少raycasting开销 `client/src/components/three/PileLayer.tsx` (6) 接线cameraView属性,正视/俯视/侧视按钮生效 `client/src/components/three/SceneCanvas.tsx`, `client/src/pages/View3DPage.tsx` (7) 统一字段名桩径(mm)→桩径消除service层key重命名
