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
├── server/                           # FastAPI 后端
│   ├── main.py                       # 应用入口，注册路由 + 托管静态文件
│   ├── database.py                   # SQLAlchemy 引擎 + SQLite 连接
│   ├── schemas.py                    # Pydantic 请求/响应模型
│   ├── migrate.py                    # JSON → SQLite 一次性迁移脚本
│   ├── api/                          # REST 路由层 (18 个端点)
│   │   ├── project.py                # GET /api/project
│   │   ├── settings.py               # GET/PUT /api/settings
│   │   ├── geo.py                    # 地勘上传/查询
│   │   ├── piles.py                  # 桩基上传/查询
│   │   ├── predict.py                # 单桩/批量/场景数据预测
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
│   │   └── predict_service.py
│   └── core/                         # 纯计算引擎 (无状态函数)
│       ├── prediction.py             # 克里金/IDW 插值
│       └── bearing_capacity.py       # JGJ94-2008 承载力计算
├── client/                           # React 18 + TypeScript 前端
│   ├── src/
│   │   ├── App.tsx                   # 入口 (ConfigProvider + AppLayout)
│   │   ├── main.tsx                  # ReactDOM 挂载
│   │   ├── api/client.ts             # Axios API 客户端 (完整类型定义)
│   │   ├── store/                    # Zustand 状态管理
│   │   │   ├── useProjectStore.ts
│   │   │   ├── usePileStore.ts
│   │   │   └── useSettingsStore.ts
│   │   ├── components/
│   │   │   ├── layout/               # AppLayout, Sidebar, StatusBar
│   │   │   ├── charts/LayerChart.tsx  # Recharts 2D 柱状图
│   │   │   └── three/                # React-Three-Fiber 3D 组件
│   │   │       ├── SceneCanvas.tsx
│   │   │       ├── PileLayer.tsx
│   │   │       └── GroundPlane.tsx
│   │   └── pages/
│   │       ├── DataPage.tsx           # 数据管理
│   │       ├── PredictPage.tsx        # 预测与实测
│   │       ├── View3DPage.tsx         # 3D 视图
│   │       └── RecordPage.tsx         # 记录与承载力
│   ├── vite.config.ts
│   └── package.json
├── legacy/                           # 旧 Tkinter 代码 (保留参考)
│   ├── main.py
│   └── ui/
├── core/                             # 原始计算模块 (旧版保留)
├── assets/scene.html                 # 原始 3D 场景 (旧版保留)
└── project_full_data.json            # 旧 JSON 数据 (已迁移到 SQLite)
```

## 核心模块

| 模块 | 关键函数 | 职责 |
|------|---------|------|
| `server/core/prediction.py` | `predict_one()`, `predict_one_fast()`, `idw_interpolate()`, `krige_interpolate()` | 无状态插值预测，接受 DataFrame |
| `server/core/bearing_capacity.py` | `calculate()`, `load_soil_params()`, `export_calc_sheet()` | JGJ94-2008 承载力，函数式接口 |
| `server/services/predict_service.py` | `predict_single()`, `predict_all()`, `get_scene_data()` | 预测业务编排 + 缓存 |
| `client/src/components/three/SceneCanvas.tsx` | R3F Canvas | 3D 场景渲染 (WebGL) |
| `client/src/components/three/PileLayer.tsx` | 760 根桩体圆柱 | 悬停/点击交互 + 选中高亮 |

## 数据存储

- **数据库**：SQLite (`pile_app.db`)，7 张表，通过 SQLAlchemy ORM 访问
- **迁移**：`python server/migrate.py` 从旧 JSON 一次性导入
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
| 760 根桩体圆柱 (按桩型着色) | PileLayer + colorMap | V1 |
| 半透明地面参考面 | GroundPlane | V1 |
| 悬停识别 → 桩号 Tooltip | onPointerMove + state | V1 |
| 点击选中 → 高亮 + Drawer 联动 | onClick + emissive | V1 |
| 右上角 Gizmo 坐标轴 | Drei GizmoHelper | V1 |
| OrbitControls (旋转/平移/缩放) | Drei OrbitControls | V1 |
| 视角切换 (正视/俯视/侧视) | 按钮已就位 (相机动画待实现) | V1 |
| 图例 (灌注桩/预制桩/其他) | 固定色块 | V1 |
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

- **IDW 快速预测精度**：3D 视图用 IDW 替代克里金（约 0.2s 完成 760 桩），与正式克里金预测有微小偏差
- **桩底标高**：3D 视图中桩底 = 持力层顶标高(IDW预测) − 进入深度，未设置持力层时无桩底
- **首次启动**：需要先 `npm run build` 构建前端，之后纯 Python 启动
- **视角切换按钮**：正视/俯视/侧视按钮 UI 已就位，相机动画逻辑待接入

## 当前进展

- 完成克里金插值预测核心算法
- 完成 Web 化全量重写：Tkinter → React + FastAPI + SQLite
- 前后端分离四层架构：前端(React) + API(FastAPI) + 计算(core/) + 存储(SQLite)
- 18 个 REST API 端点，覆盖全部业务功能
- 3D 场景从独立 HTML → React-Three-Fiber 组件化
- 实测数据独立存储，修复数据污染问题
- 预测结果缓存到 SQLite，避免重复计算
- 旧 Tkinter 代码保留在 legacy/ 目录
- 已部署 3 个 Claude Code Skills（Superpowers、Karpathy Guidelines、ECC）

## 工作日志

每次工作完成后更新此节。记录做了什么、改了哪些文件、下一步计划。

格式：`YYYY-MM-DD: [简述] — [改动文件列表]`

- 2026-05-24: 更新 CLAUDE.md — 增加 Persona 定义、三个 Skills 调用规范、工作日志章节
- 2026-05-24: **分层重构完成** — 876行单文件拆分为 core/(data_layer, prediction, bearing_capacity) + ui/(data_tab, predict_tab, view3d_tab, record_tab, log_tab) + main.py。修复 IDW argmin bug。新增 JGJ94-2008 承载力计算模块。删除旧单文件。
- 2026-05-24: **3D视图调试完成（多轮迭代）** — pywebview → 直接注入JSON → webbrowser.open → IDW快速预测 → 仅显示桩体 → 视角修正 → 详情面板 → gizmo → 桩底标高计算
- 2026-05-24: 更新 CLAUDE.md — 完善项目架构、模块说明、3D 技术细节、已知问题
- 2026-05-24: **Web 化全量重写完成** — 架构: React 18 + TypeScript + FastAPI + SQLite。22 个后端文件 (server/) + 17 个前端文件 (client/)。7 张数据库表替代 JSON。18 个 REST API 端点。3D 场景用 React-Three-Fiber 重写 (悬停/选中/高亮/Gizmo)。TypeScript 零错误，前端构建成功，4046条地勘+760根桩已迁移。旧 Tkinter 代码移至 legacy/ 保留。设计文档: docs/superpowers/specs/ + plans/
