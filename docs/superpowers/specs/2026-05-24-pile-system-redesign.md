# 桩基土层预测系统 — 分层重构与功能增强设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 将876行单文件Tkinter程序拆分为 core/ui 双层架构，修复已知bug，用 WebGL 替换 Matplotlib 3D，新增承载力计算模块。

**Architecture:** `core/`（纯Python，零UI依赖）包含数据读写、插值预测、承载力计算三个模块，未来可直接作为FastAPI后端包复用。`ui/`（Tkinter）每个Tab独立文件，通过构造函数接收core对象。3D视图用 pywebview 内嵌 Three.js 场景，Python-JS之间通过单次JSON数据传递和回调通信。

**Tech Stack:** Python 3, pandas, numpy, pykrige, matplotlib (2D only), scipy, tkinter, pywebview, Three.js (CDN + 本地降级)

---

## 文件结构

```
桩基智能体/
├── core/
│   ├── __init__.py
│   ├── data_layer.py              # DataStore: 数据读写与持久化
│   ├── prediction.py              # PredictEngine: 克里金/IDW插值
│   └── bearing_capacity.py        # BearingCalc: JGJ94-2008承载力
├── ui/
│   ├── __init__.py
│   ├── data_tab.py                # 数据管理页
│   ├── predict_tab.py             # 预测与实测对比页（2D matplotlib）
│   ├── view3d_tab.py              # 3D视图页（pywebview + Three.js）
│   ├── record_tab.py              # 打桩记录页
│   └── log_tab.py                 # 施工日志页
├── assets/
│   └── scene.html                 # Three.js 3D场景（内嵌JS，离线可用）
├── main.py                        # 入口 ~30行
└── project_full_data.json         # 数据持久化
```

## 接口设计

### DataStore (data_layer.py)

```
DataStore
  .geo_data: DataFrame (columns: 孔号, X, Y, 土层名称, 土层顶标高, 土层底标高, 土层厚度)
  .pile_data: DataFrame (columns: 桩号, X, Y, 桩径, 桩型)
  .support_layer, .support_depth, .support_depth_type, .user_pile_top_elev
  .warning_threshold, .alarm_threshold, .interp_method

  .load_geo(path) → (bool, str)
  .load_pile(path) → (bool, str)
  .add_measured_pile(x, y, layers_dict, pile_no) → None
  .export_measured_holes() → (DataFrame|None, str)
  .save() / .load() → JSON持久化
```

### PredictEngine (prediction.py)

```
PredictEngine(store: DataStore)

  .predict_one(pile_no) → dict | None
      返回: {桩号, X坐标, Y坐标, 桩径, 桩型, 土层预测: {层名: 标高}, 土层底标高预测: {层名: 标高},
            持力层顶标高, 持力层进入深度, 桩顶标高, 土层排序}

  .predict_all() → DataFrame
  .idw_interpolate(x, y, xv, yv, val) → float  [修复: np.argmin]
  .krige_interpolate(x, y, xv, yv, val) → float
  .get_layer_list() → list[str]
  .calculate_support_depth(pile_diameter) → float
```

### BearingCalc (bearing_capacity.py)

```
SoilParams: {layer_name, qsik, qpk}
BearingResult: {pile_no, Qsk, Qpk, Quk, Ra, layer_details[], passes_check}

BearingCalc(store: DataStore, engine: PredictEngine)
  .load_soil_params(path) → (bool, str)     # 从Excel加载土工参数
  .calculate(pile_no, safety_factor=2.0) → BearingResult
  .export_calc_sheet(result) → str           # 计算书文本
  .batch_calculate(pile_list) → DataFrame    # 批量计算
```

## 3D场景设计 (scene.html)

### 几何体
- 勘探孔：按土层颜色分段的细竖线（`LineBasicMaterial`，线宽1）
- 桩体：按土层颜色分段的圆柱体（`CylinderGeometry`，半径=桩径/2000）
- 持力层参考面：半透明红色平面
- 地面：半透明灰色平面
- 标牌：CSS2DRenderer 文字标签（勘探孔白底黑字，桩黄底红字）

### 交互
| 操作 | 效果 |
|------|------|
| 鼠标拖拽 | OrbitControls 旋转/平移/缩放（GPU侧，无Python调用） |
| 悬停桩体 | Raycaster → tooltip（桩号、桩径、桩型、持力层标高、桩长、预测状态） |
| 点击桩体 | 高亮描边 + 锁定信息面板，点击空白取消 |
| 点击勘探孔 | 显示该孔分层信息列表 |

### Python-JS通信
```
Python → JS (启动时一次性):
  window.exposed.get_scene_data() → JSON{ boreholes[], piles[], support_layer, bounds }

JS → Python (点击事件):
  window.exposed.on_pile_click(pile_id)
  window.exposed.on_borehole_click(hole_id)
```

## 承载力计算

### 公式 (JGJ94-2008 §5.3.5)
```
Quk = Qsk + Qpk = u × Σ(qsik × li) + qpk × Ap
Ra  = Quk / K   (K=2)

u = π×d       桩周长(m)
Ap = π×d²/4   桩端面积(m²)
li            第i层土在桩身范围内的厚度(m)
qsik          第i层土极限侧阻力标准值(kPa)
qpk           极限端阻力标准值(kPa)
```

### 参数来源
- 土层分层和厚度：来自 PredictEngine 预测结果
- qsik, qpk：用户从 Excel 模板导入或手工录入（规范查表值）
- 桩径、桩型：来自桩基施工图数据

## 实施步骤

### Step 1: 修复 IDW bug
- `argmin → np.argmin` at 原文件 line 149

### Step 2: core/data_layer.py
- 从原文件提取 DataStore 类
- 包含 geo_data、pile_data 管理、JSON 持久化

### Step 3: core/prediction.py
- 从原文件提取 PredictEngine
- 包含 IDW、Kriging、predict_one、predict_all、_calc_geo_bottom_elev

### Step 4: core/bearing_capacity.py
- 新增 BearingCalc 类、SoilParams、BearingResult dataclass
- JGJ94-2008 公式实现

### Step 5: ui/*.py（view3d_tab 除外）
- 从原文件提取 4 个 Tab 页面
- 每个 Tab 接收 DataStore/PredictEngine/BearingCalc

### Step 6: ui/view3d_tab.py + assets/scene.html
- pywebview 启动内嵌 Three.js 场景
- 实现悬停提示、点击锁定、视角切换

### Step 7: main.py
- 组装 core 对象和 UI 对象
- 删除旧单文件
