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
| `superpowers:brainstorming` | 开始任何非平凡实现前 | 需求模糊、多方案可选、架构决策、评估建议是否合理 |
| `superpowers:writing-plans` | brainstorming 确认方案后 | 涉及多文件、多步骤的实现任务 |
| `superpowers:subagent-driven-development` | 执行计划中的独立任务 | 计划拆分为多个独立子任务时 |
| `superpowers:executing-plans` | 需要并行会话执行 | 任务适合切到独立会话时 |
| `superpowers:requesting-code-review` | 完成任务/功能/修复后 | 每个重要改动完成后、合并前 |
| `superpowers:systematic-debugging` | 遇到非显而易见的 bug | 根因不明、难以复现、涉及多系统 |
| `superpowers:test-driven-development` | 编写新功能或修复 bug | 有明确输入输出的逻辑代码 |
| `superpowers:verification-before-completion` | 声明"完成了"之前 | 任何改动完成后必须自证通过 |
| `superpowers:finishing-a-development-branch` | 所有任务完成后 | 分支准备合并时 |

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
├── main.py                          # 程序入口，组装 core 和 ui
├── core/                            # 纯 Python，零 UI 依赖，未来可复用为 FastAPI 后端
│   ├── __init__.py
│   ├── data_layer.py                # DataStore：数据读写、JSON 持久化
│   ├── prediction.py                # PredictEngine：克里金/IDW 插值预测
│   └── bearing_capacity.py          # BearingCalc：JGJ94-2008 承载力计算
├── ui/                              # Tkinter 界面层
│   ├── __init__.py
│   ├── data_tab.py                  # 数据管理页（导入、持力层设置）
│   ├── predict_tab.py               # 预测与实测对比页（2D 柱状图）
│   ├── view3d_tab.py                # 3D 视图页（生成数据 → 浏览器打开 scene.html）
│   ├── record_tab.py                # 打桩记录页
│   └── log_tab.py                   # 施工日志页
├── assets/
│   └── scene.html                   # Three.js 3D 场景（浏览器渲染，CDN 加载）
└── project_full_data.json           # 运行时持久化数据
```

## 核心模块

| 模块 | 类 | 职责 |
|------|-----|------|
| `core/data_layer.py` | `DataStore` | 地勘/桩基数据加载、实测数据管理、JSON 持久化 |
| `core/prediction.py` | `PredictEngine` | 克里金/IDW 插值、单桩/批量预测、`predict_one_fast()` 用 IDW 快速预测（供 3D 视图） |
| `core/bearing_capacity.py` | `BearingCalc` | JGJ94-2008 单桩竖向承载力：Qsk + Qpk = Quk → Ra |
| `ui/view3d_tab.py` | `View3DTab` | 生成桩位 JSON → 注入 HTML → `webbrowser.open()` 浏览器渲染 |

## 3D 视图技术细节

- **渲染方案**：Three.js (WebGL)，浏览器打开，非 pywebview 内嵌（避免线程死锁）
- **数据注入**：Python 生成 IDW 快速预测结果 → JSON → 写入临时 HTML → 浏览器打开
- **显示内容**：760 根桩体圆柱（按桩型着色）+ 半透明地面 + 持力层参考面
- **交互**：OrbitControls 旋转/平移/缩放、Raycaster 悬停显示桩号、点击弹出左侧详情面板
- **视角**：正视(YZ平面)、俯视(XY平面)、侧视(XZ平面)，按钮置于页面顶部中央
- **坐标轴**：右上角 80px gizmo 随视角旋转，红X绿Y蓝Z
- **相机**：`camera.up.set(0,0,1)`，Z 轴为垂直方向

## 关键数据文件

| 文件 | 说明 |
|------|------|
| `地勘报告修改版.csv` / `.xlsx` | 地质勘探原始数据（238 孔 × 17 土层 = 4046 条分层记录） |
| `西地块地下室桩基施工图 (灌注桩)(1)(1).csv` / `.xlsx` | 桩位坐标与设计参数（760 根桩） |
| `实际勘探孔.csv` | 筛选后的有效勘探孔数据 |
| `project_full_data.json` | 系统运行时持久化的项目数据 |
| `承载力计算.pdf` | 桩基承载力计算书 |
| `JGJ94-2008 建筑桩基技术规范.pdf` | 国家规范 |
| `0勘察报告/` | 勘察报告原始资料目录 |
| `桩编号图纯净版.dwg` | CAD桩位编号图 |

## 技术栈

- Python 3，依赖：`pandas`, `numpy`, `pykrige`, `matplotlib` (仅 2D), `scipy`, `tkinter`
- 3D 渲染：Three.js v0.160 (CDN + 离线降级)
- 坐标系统：项目使用独立坐标系（非WGS84），XY 为水平面，Z 为高程
- 编码注意：CSV 文件可能为 GBK 或 UTF-8，读取时需兼容处理

## 已知问题

- **IDW 快速预测精度**：3D 视图用 IDW 替代克里金（约 0.2s 完成 760 桩），与正式克里金预测有微小偏差
- **桩底标高**：3D 视图中桩底 = 持力层顶标高(IDW预测) − 进入深度，未设置持力层时无桩底
- **离线模式**：3D 视图首次需要联网加载 Three.js CDN

## 当前进展

- 完成克里金插值预测核心算法
- 完成分层重构（876行单文件 → 12 个模块化文件）
- 修复 IDW argmin → np.argmin bug
- 新增 JGJ94-2008 承载力计算模块
- 3D 视图从 Matplotlib 切换为 Three.js WebGL（浏览器渲染）
- 3D 交互：旋转/平移/缩放、悬停显示桩号、点击显示详情面板
- 数据持久化（JSON）已修复读写错误
- 已部署 3 个 Claude Code Skills（Superpowers、Karpathy Guidelines、ECC）

## 工作日志

每次工作完成后更新此节。记录做了什么、改了哪些文件、下一步计划。

格式：`YYYY-MM-DD: [简述] — [改动文件列表]`

<!-- 工作日志开始 -->
- 2026-05-24: 更新 CLAUDE.md — 增加 Persona 定义、三个 Skills 调用规范、工作日志章节
- 2026-05-24: **分层重构完成** — 876行单文件拆分为 core/(data_layer, prediction, bearing_capacity) + ui/(data_tab, predict_tab, view3d_tab, record_tab, log_tab) + main.py。修复 IDW argmin bug。新增 JGJ94-2008 承载力计算模块。删除旧单文件。
- 2026-05-24: **3D视图调试完成（多轮迭代）**：
  - pywebview JS API → 直接注入 JSON 数据
  - pywebview 子线程死锁 → 改用 `webbrowser.open()` 系统浏览器
  - 全量克里金预测卡死 → `predict_one_fast()` 仅对持力层做 IDW（760桩 × 0.2s）
  - 勘探孔+桩体分段圆柱 15000+ 几何体 → 仅显示桩体（760 根单色圆柱）
  - 按钮 onclick 模块作用域问题 → addEventListener 绑定
  - 视角修正（正视=YZ, 俯视=XY, 侧视=XZ），Z 轴向上
  - 左侧详情面板（点击显示完整信息）、悬停仅显示桩号
  - 右上角坐标轴 gizmo、按钮移至顶部中央
  - 桩底标高通过持力层 IDW 预测计算
- 2026-05-24: 更新 CLAUDE.md — 完善项目架构、模块说明、3D 技术细节、已知问题
<!-- 工作日志结束 -->
