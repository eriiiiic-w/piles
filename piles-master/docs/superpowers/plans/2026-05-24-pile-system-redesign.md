# 桩基土层预测系统 — 分层重构与功能增强 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将876行单文件拆分为 core (3个模块) + ui (5个tab) + WebGL 3D，修复IDW bug，新增承载力计算。

**Architecture:** core/ 零UI依赖，ui/ 每个Tab一个文件通过构造函数接收 core 对象，3D用 pywebview + Three.js 替代 Matplotlib 3D。

**Tech Stack:** Python 3, pandas, numpy, pykrige, matplotlib (2D only), scipy, tkinter, pywebview, Three.js

---

### Task 1: 修复 IDW bug + 创建 core/__init__.py

**Files:**
- Modify: `桩基土层预测系统.py:149`
- Create: `core/__init__.py`

- [ ] **Step 1: 修复 argmin 为 np.argmin**

```python
# 原文件第149行，将:
if np.any(distances == 0):
    return float(val[argmin(distances)])

# 改为:
if np.any(distances == 0):
    return float(val[np.argmin(distances)])
```

- [ ] **Step 2: 创建 core/__init__.py**

```python
# core/__init__.py
from .data_layer import DataStore
from .prediction import PredictEngine
from .bearing_capacity import BearingCalc, BearingResult, SoilParams
```

- [ ] **Step 3: 验证 — 运行原程序，选择IDW法预测一根桩，确认不报错**

Run: `python 桩基土层预测系统.py`

- [ ] **Step 4: 提交**

```bash
git add 桩基土层预测系统.py core/__init__.py
git commit -m "fix: IDW argmin → np.argmin, add core package init"
```

---

### Task 2: core/data_layer.py — 数据层

**Files:**
- Create: `core/data_layer.py`
- Modify: `core/__init__.py` (已有import，本步确认路径正确)

- [ ] **Step 1: 从原文件提取 DataStore 类，写入 core/data_layer.py**

```python
# core/data_layer.py
import pandas as pd
import numpy as np
import os
import json

SAVE_FILE = "project_full_data.json"

class DataStore:
    """地质与桩基数据管理，JSON持久化"""
    
    def __init__(self):
        self.geo_data = pd.DataFrame()
        self.pile_data = pd.DataFrame()
        self.support_layer = ""
        self.support_depth = 1.5
        self.support_depth_type = "直接输入"
        self.user_pile_top_elev = 0.5
        self.warning_threshold = 0.3
        self.alarm_threshold = 0.5
        self.interp_method = "克里金法"
    
    def _calc_geo_bottom_elev(self, geo_df):
        adjusted_df = []
        for hole_id, hole_data in geo_df.groupby('孔号'):
            hole_data = hole_data.sort_values('土层顶标高', ascending=False).reset_index(drop=True)
            for i in range(len(hole_data)):
                layer = hole_data.iloc[i]
                layer = layer.copy()
                if pd.notna(layer['土层厚度']) and layer['土层厚度'] > 0:
                    layer['土层底标高'] = layer['土层顶标高'] - layer['土层厚度']
                else:
                    layer['土层厚度'] = 2.0
                    layer['土层底标高'] = layer['土层顶标高'] - 2.0
                adjusted_df.append(layer)
        return pd.DataFrame(adjusted_df)
    
    def load_geo_data(self, file_path):
        try:
            self.geo_data = pd.read_excel(file_path)
            self.geo_data = self.geo_data.fillna("无")
            self.geo_data['X'] = pd.to_numeric(self.geo_data['X'], errors='coerce')
            self.geo_data['Y'] = pd.to_numeric(self.geo_data['Y'], errors='coerce')
            self.geo_data['土层顶标高'] = pd.to_numeric(self.geo_data['土层顶标高'], errors='coerce')
            self.geo_data['土层厚度'] = pd.to_numeric(self.geo_data['土层厚度'], errors='coerce')
            self.geo_data = self.geo_data.dropna(subset=['X', 'Y', '土层顶标高'])
            self.geo_data = self._calc_geo_bottom_elev(self.geo_data)
            return True, f"地勘数据加载完成！共{len(self.geo_data)}条分层数据"
        except Exception as e:
            return False, f"地勘数据加载失败：{str(e)}"
    
    def add_measured_pile_as_geo_hole(self, pile_x, pile_y, measured_layers, pile_no):
        new_rows = []
        for layer_name, top_elev in measured_layers.items():
            new_rows.append({
                "孔号": f"实测桩_{pile_no}",
                "X": pile_x,
                "Y": pile_y,
                "土层名称": layer_name,
                "土层顶标高": top_elev,
                "土层厚度": 2.0,
                "土层底标高": top_elev - 2.0
            })
        new_df = pd.DataFrame(new_rows)
        self.geo_data = pd.concat([self.geo_data, new_df], ignore_index=True)
        self.geo_data = self._calc_geo_bottom_elev(self.geo_data)
    
    def export_measured_holes(self):
        measured_holes = self.geo_data[self.geo_data['孔号'].str.startswith('实测桩_', na=False)]
        if measured_holes.empty:
            return None, "暂无实测勘探孔数据"
        return measured_holes, f"共导出 {len(measured_holes)} 条实测勘探孔数据"
    
    def load_pile_data(self, file_path):
        try:
            self.pile_data = pd.read_excel(file_path)
            self.pile_data['X'] = pd.to_numeric(self.pile_data['X'], errors='coerce')
            self.pile_data['Y'] = pd.to_numeric(self.pile_data['Y'], errors='coerce')
            self.pile_data['桩径'] = pd.to_numeric(self.pile_data['桩径'], errors='coerce')
            return True, f"桩基数据加载完成！共{len(self.pile_data)}根桩"
        except Exception as e:
            return False, f"桩基数据加载失败：{str(e)}"
    
    def get_layer_list(self):
        if self.geo_data.empty:
            return []
        avg_elev = self.geo_data.groupby('土层名称')['土层顶标高'].mean().sort_values(ascending=False)
        return list(avg_elev.index)
    
    def get_pile_list(self):
        if self.pile_data.empty:
            return []
        return list(self.pile_data['桩号'].unique())
    
    def save(self):
        data = {
            "geo_data": self.geo_data.to_dict("records") if not self.geo_data.empty else [],
            "pile_data": self.pile_data.to_dict("records") if not self.pile_data.empty else [],
            "support_layer": self.support_layer,
            "support_depth": self.support_depth,
            "support_depth_type": self.support_depth_type,
            "user_pile_top_elev": self.user_pile_top_elev,
            "warning_threshold": self.warning_threshold,
            "alarm_threshold": self.alarm_threshold,
            "interp_method": self.interp_method
        }
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load(self):
        if not os.path.exists(SAVE_FILE):
            return {}
        with open(SAVE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if data.get("geo_data"):
            self.geo_data = pd.DataFrame(data["geo_data"])
        if data.get("pile_data"):
            self.pile_data = pd.DataFrame(data["pile_data"])
        self.support_layer = data.get("support_layer", "")
        self.support_depth = data.get("support_depth", 1.5)
        self.support_depth_type = data.get("support_depth_type", "直接输入")
        self.user_pile_top_elev = data.get("user_pile_top_elev", 0.5)
        self.warning_threshold = data.get("warning_threshold", 0.3)
        self.alarm_threshold = data.get("alarm_threshold", 0.5)
        self.interp_method = data.get("interp_method", "克里金法")
        return data.get("measured_data", {})
```

- [ ] **Step 2: 验证 — Python导入不报错**

Run: `python -c "from core.data_layer import DataStore; d = DataStore(); print('DataStore OK')"`
Expected: `DataStore OK`

- [ ] **Step 3: 提交**

```bash
git add core/data_layer.py core/__init__.py
git commit -m "feat: add DataStore — geo/pile data management and JSON persistence"
```

---

### Task 3: core/prediction.py — 预测引擎

**Files:**
- Create: `core/prediction.py`

- [ ] **Step 1: 创建预测引擎模块**

```python
# core/prediction.py
import numpy as np
import pandas as pd
from pykrige import OrdinaryKriging


class PredictEngine:
    """克里金/IDW土层插值预测引擎"""
    
    def __init__(self, store):
        self.store = store
    
    def _get_geo(self):
        return self.store.geo_data
    
    def _get_pile(self):
        return self.store.pile_data
    
    def idw_interpolate(self, x, y, xv, yv, val):
        distances = np.sqrt((xv - x)**2 + (yv - y)**2)
        if np.any(distances == 0):
            return float(val[np.argmin(distances)])
        weights = 1 / (distances ** 2)
        return float(np.sum(weights * val) / np.sum(weights))
    
    def krige_interpolate(self, x, y, xv, yv, val):
        try:
            ok = OrdinaryKriging(xv, yv, val, variogram_model='spherical', enable_plotting=False)
            z, _ = ok.execute('points', np.array([x]), np.array([y]))
            return float(z[0])
        except Exception:
            return float(np.mean(val))
    
    def predict_one(self, pile_no):
        geo = self._get_geo()
        pile = self._get_pile()
        if geo.empty or pile.empty:
            return None
        
        pile_info = pile[pile['桩号'] == pile_no]
        if pile_info.empty:
            return None
        
        pile_x = pile_info['X'].values[0]
        pile_y = pile_info['Y'].values[0]
        pile_diameter = pile_info['桩径'].values[0]
        pile_type = pile_info['桩型'].values[0] if '桩型' in pile_info.columns else '未知'
        layer_list = self.get_layer_list()
        
        result = {
            "桩号": pile_no,
            "X坐标": pile_x, "Y坐标": pile_y,
            "桩径(mm)": pile_diameter, "桩型": pile_type,
            "土层预测": {}, "土层底标高预测": {},
            "土层排序": layer_list,
            "桩顶标高": self.store.user_pile_top_elev
        }
        
        for layer in layer_list:
            layer_data = geo[geo['土层名称'] == layer]
            if len(layer_data) < 2:
                z_pred = round(layer_data['土层顶标高'].mean() if not layer_data.empty else 10.0, 2)
            else:
                xv, yv, val = layer_data['X'].values, layer_data['Y'].values, layer_data['土层顶标高'].values
                if self.store.interp_method == "克里金法":
                    z_pred = round(self.krige_interpolate(pile_x, pile_y, xv, yv, val), 2)
                else:
                    z_pred = round(self.idw_interpolate(pile_x, pile_y, xv, yv, val), 2)
            result["土层预测"][layer] = z_pred
        
        for i, layer in enumerate(layer_list):
            if i < len(layer_list) - 1:
                result["土层底标高预测"][layer] = result["土层预测"][layer_list[i + 1]]
            else:
                avg_thick = geo[geo['土层名称'] == layer]['土层厚度'].mean()
                result["土层底标高预测"][layer] = round(result["土层预测"][layer] - avg_thick, 2)
        
        support_depth = self.calc_support_depth(pile_diameter)
        if self.store.support_layer in result["土层预测"]:
            result["持力层顶标高"] = result["土层预测"][self.store.support_layer]
            result["持力层进入深度(m)"] = support_depth
        
        return result
    
    def predict_all(self):
        geo = self._get_geo()
        pile = self._get_pile()
        if geo.empty or pile.empty:
            return None
        
        rows = []
        for pno in self.get_pile_list():
            res = self.predict_one(pno)
            if res:
                flat = {
                    "桩号": res["桩号"], "X": res["X坐标"], "Y": res["Y坐标"],
                    "桩径": res["桩径(mm)"], "桩型": res["桩型"],
                    "持力层顶标高": res.get("持力层顶标高", ""), "桩顶标高": res["桩顶标高"]
                }
                for k, v in res["土层预测"].items():
                    flat[f"{k}顶标高"] = v
                rows.append(flat)
        return pd.DataFrame(rows)
    
    def get_layer_list(self):
        return self.store.get_layer_list()
    
    def get_pile_list(self):
        return self.store.get_pile_list()
    
    def calc_support_depth(self, pile_diameter_mm):
        if self.store.support_depth_type == "n倍桩径":
            return self.store.support_depth * (pile_diameter_mm / 1000)
        return self.store.support_depth
```

- [ ] **Step 2: 验证导入和基本预测**

Run: `python -c "from core.data_layer import DataStore; from core.prediction import PredictEngine; s = DataStore(); e = PredictEngine(s); print('PredictEngine OK')"`
Expected: `PredictEngine OK`

- [ ] **Step 3: 提交**

```bash
git add core/prediction.py
git commit -m "feat: add PredictEngine — Kriging/IDW interpolation and pile prediction"
```

---

### Task 4: core/bearing_capacity.py — 承载力计算引擎

**Files:**
- Create: `core/bearing_capacity.py`

- [ ] **Step 1: 创建承载力计算模块**

```python
# core/bearing_capacity.py
from dataclasses import dataclass, field
import pandas as pd
import numpy as np


@dataclass
class SoilParams:
    layer_name: str
    qsik: float = 0.0
    qpk: float = 0.0


@dataclass
class LayerDetail:
    layer_name: str
    thickness: float
    qsik: float
    side_resistance: float


@dataclass
class BearingResult:
    pile_no: str
    pile_diameter_mm: float
    pile_length_m: float
    Qsk: float
    Qpk: float
    Quk: float
    Ra: float
    layer_details: list = field(default_factory=list)
    passes_check: bool = True


class BearingCalc:
    """JGJ94-2008 单桩竖向承载力计算"""
    
    def __init__(self, store, engine):
        self.store = store
        self.engine = engine
        self.soil_params = {}
    
    def load_soil_params(self, file_path):
        try:
            df = pd.read_excel(file_path)
            required = ['土层名称', 'qsik']
            for col in required:
                if col not in df.columns:
                    return False, f"缺少必要列: {col}"
            self.soil_params = {}
            for _, row in df.iterrows():
                sp = SoilParams(
                    layer_name=row['土层名称'],
                    qsik=float(row['qsik']),
                    qpk=float(row.get('qpk', 0))
                )
                self.soil_params[row['土层名称']] = sp
            return True, f"加载 {len(self.soil_params)} 个土层参数"
        except Exception as e:
            return False, f"加载失败: {e}"
    
    def _get_soil_param(self, layer_name):
        if layer_name in self.soil_params:
            return self.soil_params[layer_name]
        return SoilParams(layer_name=layer_name, qsik=0, qpk=0)
    
    def calculate(self, pile_no, safety_factor=2.0):
        pred = self.engine.predict_one(pile_no)
        if pred is None:
            return None
        
        pile_info = self.store.pile_data[self.store.pile_data['桩号'] == pile_no]
        diameter_mm = pile_info['桩径'].values[0]
        diameter_m = diameter_mm / 1000.0
        
        u = np.pi * diameter_m
        Ap = np.pi * (diameter_m ** 2) / 4.0
        
        pile_top = pred["桩顶标高"]
        pile_bottom = pred.get("持力层顶标高", pile_top - 20) - pred.get("持力层进入深度(m)", 0)
        pile_length = pile_top - pile_bottom
        
        layer_list = pred["土层排序"]
        layers = pred["土层预测"]
        bottoms = pred["土层底标高预测"]
        
        Qsk = 0.0
        details = []
        
        for layer_name in layer_list:
            top = layers[layer_name]
            bottom = bottoms[layer_name]
            
            seg_top = max(top, pile_bottom)
            seg_bottom = min(bottom, pile_bottom)
            if seg_bottom > seg_top:
                seg_bottom, seg_top = seg_top, seg_bottom
            thickness = max(0, seg_top - seg_bottom)
            
            sp = self._get_soil_param(layer_name)
            side_res = u * sp.qsik * thickness
            Qsk += side_res
            details.append(LayerDetail(
                layer_name=layer_name,
                thickness=round(thickness, 2),
                qsik=sp.qsik,
                side_resistance=round(side_res, 2)
            ))
        
        support_layer = self.store.support_layer
        sp_end = self._get_soil_param(support_layer)
        Qpk = sp_end.qpk * Ap
        
        Quk = Qsk + Qpk
        Ra = Quk / safety_factor
        
        return BearingResult(
            pile_no=pile_no,
            pile_diameter_mm=diameter_mm,
            pile_length_m=round(pile_length, 2),
            Qsk=round(Qsk, 2),
            Qpk=round(Qpk, 2),
            Quk=round(Quk, 2),
            Ra=round(Ra, 2),
            layer_details=details,
            passes_check=True
        )
    
    def export_calc_sheet(self, result):
        if result is None:
            return "无计算数据"
        
        lines = []
        lines.append("=" * 70)
        lines.append("                桩基竖向承载力计算书")
        lines.append("              （依据 JGJ94-2008 §5.3.5）")
        lines.append("=" * 70)
        lines.append("")
        lines.append(f"桩号: {result.pile_no}")
        lines.append(f"桩径: {result.pile_diameter_mm} mm = {result.pile_diameter_mm/1000:.2f} m")
        lines.append(f"桩长: {result.pile_length_m} m")
        lines.append(f"安全系数 K = 2.0")
        lines.append("")
        lines.append("-" * 50)
        lines.append(f"{'土层名称':<12} {'厚度/m':<8} {'qsik/kPa':<10} {'侧阻力/kN':<12}")
        lines.append("-" * 50)
        for d in result.layer_details:
            lines.append(f"{d.layer_name:<12} {d.thickness:<8.2f} {d.qsik:<10.1f} {d.side_resistance:<12.2f}")
        lines.append("-" * 50)
        lines.append("")
        lines.append(f"总侧阻力 Qsk = {result.Qsk:.2f} kN")
        lines.append(f"总端阻力 Qpk = {result.Qpk:.2f} kN")
        lines.append(f"极限承载力 Quk = {result.Quk:.2f} kN")
        lines.append(f"承载力特征值 Ra = Quk/2 = {result.Ra:.2f} kN")
        lines.append("")
        lines.append("=" * 70)
        lines.append("  计算人: ________  复核人: ________  日期: ________")
        lines.append("=" * 70)
        
        return "\n".join(lines)
```

- [ ] **Step 2: 验证导入**

Run: `python -c "from core.data_layer import DataStore; from core.prediction import PredictEngine; from core.bearing_capacity import BearingCalc; s = DataStore(); e = PredictEngine(s); b = BearingCalc(s, e); print('BearingCalc OK')"`
Expected: `BearingCalc OK`

- [ ] **Step 3: 提交**

```bash
git add core/bearing_capacity.py
git commit -m "feat: add BearingCalc — JGJ94-2008 single pile bearing capacity"
```

---

### Task 5: ui/*.py — Tab页面（除3D外）

**Files:**
- Create: `ui/__init__.py`
- Create: `ui/data_tab.py`
- Create: `ui/predict_tab.py`
- Create: `ui/record_tab.py`
- Create: `ui/log_tab.py`

- [ ] **Step 1: 创建 ui/__init__.py**

```python
# ui/__init__.py (empty)
```

- [ ] **Step 2: 创建 ui/data_tab.py**

```python
# ui/data_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class DataTab:
    def __init__(self, parent, store, engine):
        self.store = store
        self.engine = engine
        self.frame = ttk.Frame(parent, padding=15)
        
        ttk.Label(self.frame, text="数据管理中心", font=('微软雅黑', 16, 'bold'), foreground='#2c3e55').pack(pady=(0, 15))
        
        self._build_geo_section()
        self._build_pile_section()
        self._build_settings_section()
        self._build_status_bar()
    
    def _build_geo_section(self):
        f = ttk.LabelFrame(self.frame, text="地勘数据管理", padding=12)
        f.pack(fill=tk.X, pady=(0, 10))
        row = ttk.Frame(f)
        row.pack(fill=tk.X)
        ttk.Button(row, text="选择地勘文件", command=self._select_geo).pack(side=tk.LEFT, padx=(0, 10))
        self.geo_path = tk.StringVar()
        ttk.Entry(row, textvariable=self.geo_path, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(row, text="加载地勘", command=self._load_geo).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(row, text="导出实测勘探孔Excel", command=self._export_measured).pack(side=tk.LEFT)
    
    def _build_pile_section(self):
        f = ttk.LabelFrame(self.frame, text="桩基数据管理", padding=12)
        f.pack(fill=tk.X, pady=(0, 10))
        row = ttk.Frame(f)
        row.pack(fill=tk.X)
        ttk.Button(row, text="选择桩基文件", command=self._select_pile).pack(side=tk.LEFT, padx=(0, 10))
        self.pile_path = tk.StringVar()
        ttk.Entry(row, textvariable=self.pile_path, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(row, text="加载桩基", command=self._load_pile).pack(side=tk.LEFT)
        
        self.pile_tree = ttk.Treeview(f, columns=("桩号","X","Y","桩径","桩型"), show="headings", height=6)
        for c in self.pile_tree["columns"]:
            self.pile_tree.heading(c, text=c)
            self.pile_tree.column(c, width=120, anchor=tk.CENTER)
        self.pile_tree.pack(fill=tk.X, pady=(10, 0))
    
    def _build_settings_section(self):
        f = ttk.LabelFrame(self.frame, text="持力层与预警阈值设置", padding=12)
        f.pack(fill=tk.X, pady=(0, 10))
        row = ttk.Frame(f)
        row.pack(fill=tk.X)
        
        ttk.Label(row, text="持力层：").pack(side=tk.LEFT, padx=(0,5))
        self.support_var = tk.StringVar(value=self.store.support_layer)
        self.support_cb = ttk.Combobox(row, textvariable=self.support_var, width=15)
        self.support_cb.pack(side=tk.LEFT, padx=(0,15))
        
        ttk.Label(row, text="深度方式：").pack(side=tk.LEFT, padx=(0,5))
        self.depth_mode = tk.StringVar(value=self.store.support_depth_type)
        ttk.Combobox(row, textvariable=self.depth_mode, values=["直接输入","n倍桩径"], width=10).pack(side=tk.LEFT, padx=(0,15))
        
        ttk.Label(row, text="深度：").pack(side=tk.LEFT, padx=(0,5))
        self.depth_val = tk.DoubleVar(value=self.store.support_depth)
        ttk.Entry(row, textvariable=self.depth_val, width=8).pack(side=tk.LEFT, padx=(0,15))
        
        ttk.Label(row, text="预警：").pack(side=tk.LEFT, padx=(0,5))
        self.warn_val = tk.DoubleVar(value=self.store.warning_threshold)
        ttk.Entry(row, textvariable=self.warn_val, width=5).pack(side=tk.LEFT, padx=(0,15))
        
        ttk.Label(row, text="报警：").pack(side=tk.LEFT, padx=(0,5))
        self.alarm_val = tk.DoubleVar(value=self.store.alarm_threshold)
        ttk.Entry(row, textvariable=self.alarm_val, width=5).pack(side=tk.LEFT, padx=(0,15))
        
        ttk.Button(row, text="确认设置", command=self._set_support).pack(side=tk.LEFT)
        
        mf = ttk.LabelFrame(self.frame, text="土层插值算法", padding=12)
        mf.pack(fill=tk.X)
        mr = ttk.Frame(mf)
        mr.pack(fill=tk.X)
        ttk.Label(mr, text="选择算法：").pack(side=tk.LEFT, padx=(0,5))
        self.method_var = tk.StringVar(value=self.store.interp_method)
        self.method_cb = ttk.Combobox(mr, textvariable=self.method_var, values=["克里金法", "IDW反距离加权"], width=15)
        self.method_cb.pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(mr, text="应用算法", command=self._set_method).pack(side=tk.LEFT)
    
    def _build_status_bar(self):
        self.status_var = tk.StringVar(value="系统就绪 | 数据自动保存已启用")
        ttk.Label(self.frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=8).pack(fill=tk.X, pady=(15, 0))
    
    def _select_geo(self):
        p = filedialog.askopenfilename(filetypes=[("Excel","*.xlsx")])
        if p: self.geo_path.set(p)
    
    def _load_geo(self):
        ok, m = self.store.load_geo_data(self.geo_path.get())
        messagebox.showinfo("提示", m)
        self.support_cb.config(values=self.store.get_layer_list())
        self.status_var.set(m)
    
    def _select_pile(self):
        p = filedialog.askopenfilename(filetypes=[("Excel","*.xlsx")])
        if p: self.pile_path.set(p)
    
    def _load_pile(self):
        ok, m = self.store.load_pile_data(self.pile_path.get())
        self.pile_tree.delete(*self.pile_tree.get_children())
        for _, r in self.store.pile_data.iterrows():
            self.pile_tree.insert("", "end", values=(r["桩号"], r["X"], r["Y"], r["桩径"], r.get("桩型", "未知")))
        self.status_var.set(m)
        messagebox.showinfo("提示", m)
    
    def _set_support(self):
        self.store.support_layer = self.support_var.get()
        self.store.support_depth_type = self.depth_mode.get()
        self.store.support_depth = self.depth_val.get()
        self.store.warning_threshold = self.warn_val.get()
        self.store.alarm_threshold = self.alarm_val.get()
        messagebox.showinfo("成功", "持力层、深度及预警阈值已设置")
    
    def _set_method(self):
        self.store.interp_method = self.method_var.get()
        messagebox.showinfo("成功", f"已切换为：{self.store.interp_method}")
    
    def _export_measured(self):
        df, msg = self.store.export_measured_holes()
        if df is None:
            messagebox.showwarning("提示", msg)
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel文件", "*.xlsx")])
        if path:
            df.to_excel(path, index=False)
            messagebox.showinfo("成功", "导出完成")
    
    def refresh_pile_tree(self):
        self.pile_tree.delete(*self.pile_tree.get_children())
        for _, r in self.store.pile_data.iterrows():
            self.pile_tree.insert("", "end", values=(r["桩号"], r["X"], r["Y"], r["桩径"], r.get("桩型", "未知")))
```

- [ ] **Step 3: 创建 ui/predict_tab.py**

```python
# ui/predict_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import datetime


class PredictTab:
    def __init__(self, parent, store, engine, bearing_calc=None):
        self.store = store
        self.engine = engine
        self.bearing_calc = bearing_calc
        self.frame = ttk.Frame(parent, padding=15)
        self.current_pile_result = None
        self.pile_original_predicts = {}
        self.measured_data = {}
        self.on_pile_selected_callback = None
        
        ttk.Label(self.frame, text="预测与实测管理", font=('微软雅黑', 16, 'bold'), foreground='#2c3e55').pack(pady=(0, 15))
        
        self._build_top_bar()
        self._build_main_area()
    
    def _build_top_bar(self):
        top = ttk.Frame(self.frame)
        top.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(top, text="桩号：").pack(side=tk.LEFT, padx=(0, 5))
        self.pile_cb_var = tk.StringVar()
        self.pile_cb = ttk.Combobox(top, textvariable=self.pile_cb_var, width=15)
        self.pile_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.pile_cb.bind("<<ComboboxSelected>>", self._on_pile_select)
        
        ttk.Button(top, text="全部桩基预测", command=self._predict_all).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(top, text="导出全部预测Excel", command=self._export_all).pack(side=tk.LEFT, padx=(0, 15))
        
        ttk.Label(top, text="桩顶标高(m)：").pack(side=tk.LEFT, padx=(0, 5))
        self.pile_top_var = tk.DoubleVar(value=0.5)
        ttk.Entry(top, textvariable=self.pile_top_var, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(top, text="确认", command=self._set_pile_top).pack(side=tk.LEFT)
    
    def _build_main_area(self):
        main = ttk.Frame(self.frame)
        main.pack(fill=tk.BOTH, expand=True)
        
        left = ttk.LabelFrame(main, text="土层标高数据", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        self.tree = ttk.Treeview(left, columns=("土层","预测顶标高","实测顶标高","误差","录入时间"), show="headings", height=12)
        for c, w in [("土层",150),("预测顶标高",130),("实测顶标高",130),("误差",90),("录入时间",190)]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        input_f = ttk.LabelFrame(left, text="实测数据录入", padding=10)
        input_f.pack(fill=tk.X)
        ir = ttk.Frame(input_f)
        ir.pack(fill=tk.X)
        ttk.Label(ir, text="实测顶标高：").pack(side=tk.LEFT, padx=(0, 5))
        self.meas_val = tk.StringVar()
        ttk.Entry(ir, textvariable=self.meas_val, width=10).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(ir, text="实测进入持力层深度：").pack(side=tk.LEFT, padx=(0, 5))
        self.real_support_depth = tk.StringVar()
        ttk.Entry(ir, textvariable=self.real_support_depth, width=10).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(ir, text="确认录入", command=self._save_meas).pack(side=tk.LEFT)
        
        right = ttk.LabelFrame(main, text="土层与桩身示意图（预测/实测）", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.fig, self.ax = plt.subplots(figsize=(10, 12))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
    
    def refresh_pile_combobox(self):
        self.pile_cb.config(values=self.engine.get_pile_list())
    
    def _set_pile_top(self):
        self.store.user_pile_top_elev = self.pile_top_var.get()
        if self.current_pile_result:
            self.current_pile_result["桩顶标高"] = self.pile_top_var.get()
        messagebox.showinfo("成功", f"桩顶标高已设置为：{self.pile_top_var.get()} m")
    
    def _on_pile_select(self, *args):
        pno = self.pile_cb_var.get()
        if not pno:
            return
        if pno not in self.pile_original_predicts:
            res = self.engine.predict_one(pno)
            if not res:
                messagebox.showerror("错误", f"无法预测桩号{pno}")
                return
            self.pile_original_predicts[pno] = res
        
        self.current_pile_result = self.pile_original_predicts[pno]
        self._refresh_tree()
        self._draw_2d()
        
        if self.on_pile_selected_callback:
            self.on_pile_selected_callback(pno)
    
    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        res = self.current_pile_result
        pno = res["桩号"]
        meas = self.measured_data.get(pno, {})
        for lay in res["土层排序"]:
            pred = res["土层预测"][lay]
            m_val = meas.get(lay, {}).get("标高", "")
            m_time = meas.get(lay, {}).get("时间", "")
            err = round(float(m_val) - pred, 2) if m_val != "" else ""
            self.tree.insert("", "end", values=(lay, pred, m_val, err, m_time))
    
    def _draw_2d(self):
        self.ax.clear()
        res = self.current_pile_result
        pno = res["桩号"]
        layer_list = res["土层排序"]
        bar_w = 0.35
        x_pos = np.arange(len(layer_list))
        pile_x = len(layer_list) + 0.5
        
        pred_tops = [res["土层预测"][l] for l in layer_list]
        pred_bots = [res["土层底标高预测"][l] for l in layer_list]
        
        meas_tops = []
        meas_bots = []
        for i, l in enumerate(layer_list):
            md = self.measured_data.get(pno, {}).get(l, {})
            mt = md.get("标高")
            if mt is None:
                meas_tops.append(None)
                meas_bots.append(None)
            else:
                meas_tops.append(mt)
                if i < len(layer_list) - 1:
                    nm = self.measured_data.get(pno, {}).get(layer_list[i+1], {}).get("标高")
                    mb = nm if nm else mt - (pred_tops[i] - pred_bots[i])
                else:
                    mb = mt - (pred_tops[i] - pred_bots[i])
                meas_bots.append(round(mb, 2))
        
        for i in range(len(layer_list)):
            h = pred_tops[i] - pred_bots[i]
            self.ax.bar(x_pos[i] - bar_w/2, h, bar_w, bottom=pred_bots[i],
                        color='#3498db', alpha=0.7, edgecolor='#2980b9',
                        label='预测土层' if i == 0 else "")
            self.ax.text(x_pos[i] - bar_w/2, pred_tops[i] + 0.1, f'{pred_tops[i]:.2f}',
                         ha='center', fontsize=9, color='#2980b9')
        
        for i in range(len(layer_list)):
            if meas_tops[i] is not None:
                h = meas_tops[i] - meas_bots[i]
                self.ax.bar(x_pos[i] + bar_w/2, h, bar_w, bottom=meas_bots[i],
                            color='#e74c3c', alpha=0.7, edgecolor='#c0392b',
                            label='实测土层' if i == 0 else "")
                self.ax.text(x_pos[i] + bar_w/2, meas_tops[i] + 0.1, f'{meas_tops[i]:.2f}',
                             ha='center', fontsize=9, color='#c0392b')
        
        pile_top = res["桩顶标高"]
        sup_elev = res.get("持力层顶标高", 0)
        sup_depth = res.get("持力层进入深度(m)", 0)
        pile_bottom = sup_elev - sup_depth
        self.ax.plot([pile_x, pile_x], [pile_top, pile_bottom], color="#e67e22", lw=12, label="桩体")
        self.ax.text(pile_x + 0.2, pile_top, f"桩顶\n{pile_top:.1f}", color="#d35400", fontweight='bold')
        self.ax.text(pile_x + 0.2, pile_bottom, f"桩底\n{pile_bottom:.1f}", color="#d35400", fontweight='bold')
        
        if self.store.support_layer in layer_list:
            idx = layer_list.index(self.store.support_layer)
            self.ax.annotate('持力层', xy=(x_pos[idx], pred_tops[idx]),
                             xytext=(x_pos[idx] + 0.5, pred_tops[idx] + 1),
                             arrowprops=dict(arrowstyle='->', color='#f39c12', lw=2),
                             fontsize=11, color='#f39c12', fontweight='bold')
        
        self.ax.set_ylim(min(pred_bots) - 2, max(pred_tops) + 3)
        self.ax.set_ylabel("标高(m)")
        self.ax.set_title(f"{pno} 土层与桩身示意图", fontsize=14, pad=20)
        self.ax.set_xticks(np.append(x_pos, pile_x))
        self.ax.set_xticklabels(layer_list + ["桩体"], rotation=45, ha="right")
        self.ax.legend(loc='upper right')
        self.ax.grid(alpha=0.3)
        self.canvas.draw()
    
    def _save_meas(self):
        if not self.current_pile_result:
            return
        pno = self.current_pile_result["桩号"]
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请选择土层")
            return
        lay = self.tree.item(sel[0])["values"][0]
        try:
            val = float(self.meas_val.get())
        except ValueError:
            messagebox.showerror("错误", "请输入有效数值")
            return
        
        if pno not in self.measured_data:
            self.measured_data[pno] = {}
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.measured_data[pno][lay] = {"标高": val, "时间": now}
        
        if "开工时间" not in self.current_pile_result:
            self.current_pile_result["开工时间"] = now
        if lay == self.store.support_layer:
            try:
                self.current_pile_result["实测持力层深度"] = float(self.real_support_depth.get())
            except ValueError:
                pass
        
        measured_dict = {l: self.measured_data[pno][l]["标高"] for l in self.measured_data[pno]}
        px = self.current_pile_result["X坐标"]
        py = self.current_pile_result["Y坐标"]
        self.store.add_measured_pile_as_geo_hole(px, py, measured_dict, pno)
        self._on_pile_select()
        
        if lay == self.store.support_layer:
            err = round(val - self.current_pile_result["土层预测"][lay], 2)
            w = self.store.warning_threshold
            a = self.store.alarm_threshold
            ae = abs(err)
            if ae >= a:
                messagebox.showerror("报警", f"持力层误差超标：{err:.2f}m\n阈值：{a}m")
            elif ae >= w:
                messagebox.showwarning("预警", f"持力层误差超限：{err:.2f}m\n阈值：{w}m")
    
    def _predict_all(self):
        df = self.engine.predict_all()
        if df is not None:
            messagebox.showinfo("成功", f"共{len(df)}根桩预测完成")
    
    def _export_all(self):
        df = self.engine.predict_all()
        if df is None:
            messagebox.showerror("错误", "预测失败")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel文件", "*.xlsx")])
        if path:
            df.to_excel(path, index=False)
            messagebox.showinfo("成功", "导出完成")
```

- [ ] **Step 4: 创建 ui/record_tab.py**

```python
# ui/record_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime


class RecordTab:
    def __init__(self, parent, store):
        self.store = store
        self.frame = ttk.Frame(parent, padding=15)
        
        ttk.Label(self.frame, text="单桩打桩记录（自动生成/盖章格式）", font=('微软雅黑', 16, 'bold'), foreground='#2c3e55').pack(pady=(0, 15))
        self.record_text = tk.Text(self.frame, font=("宋体", 12), wrap=tk.WORD, bg="#ffffff", relief=tk.SUNKEN, padx=10, pady=10)
        self.record_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        ttk.Button(self.frame, text="导出打桩记录文件", command=self._export).pack()
    
    def generate(self, pile_result, measured_data):
        res = pile_result
        pno = res["桩号"]
        pile_top = res["桩顶标高"]
        pred_sup_elev = res.get("持力层顶标高", 0)
        design_sup_depth = res.get("持力层进入深度(m)", 0)
        real_sup_depth = res.get("实测持力层深度", 0.0)
        real_sup_elev = measured_data.get(pno, {}).get(self.store.support_layer, {}).get("标高", pred_sup_elev)
        design_length = round(pile_top - pred_sup_elev + design_sup_depth, 2)
        real_length = round(pile_top - real_sup_elev + real_sup_depth, 2)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        
        txt = "=" * 70 + "\n                      桩基施工打桩记录\n" + "=" * 70 + "\n\n"
        txt += f"工程名称：____________________    桩  号：{pno}\n"
        txt += f"桩顶标高：{pile_top} m    桩  径：{res['桩径(mm)']} mm    桩  型：{res['桩型']}\n"
        txt += f"开工时间：{res.get('开工时间', '未录入')}    记录时间：{now}\n\n"
        txt += "---------------- 各土层实测标高 ----------------\n"
        for lay in res["土层排序"]:
            d = measured_data.get(pno, {}).get(lay, {"标高": "未实测", "时间": ""})
            txt += f"{lay:15s}│标高：{d['标高']:>8} m│时间：{d['时间']}\n"
        txt += "------------------------------------------------\n\n"
        txt += f"设计桩长 = {pile_top} - {pred_sup_elev} + {design_sup_depth} = {design_length} m\n"
        txt += f"实际桩长 = {pile_top} - {real_sup_elev:.2f} + {real_sup_depth} = {real_length} m\n\n"
        txt += "══════════════════ 签字盖章区 ══════════════════\n"
        txt += "施工单位：____________________    负责人签字：______________\n"
        txt += "监理单位：____________________    监理签字：________________\n"
        txt += "项目单位：____________________    项目负责人：________________\n"
        txt += f"日    期：{datetime.date.today().strftime('%Y年%m月%d日')}        状态：□ 合格   □ 不合格   □ 复检合格\n"
        txt += "                        （此处加盖项目专用章）\n"
        txt += "=" * 70 + "\n"
        
        self.record_text.delete(1.0, tk.END)
        self.record_text.insert(1.0, txt)
    
    def _export(self):
        t = self.record_text.get(1.0, tk.END)
        if not t.strip():
            messagebox.showwarning("提示", "无记录")
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("文本文件", "*.txt")])
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(t)
            messagebox.showinfo("成功", "打桩记录已导出")
```

- [ ] **Step 5: 创建 ui/log_tab.py**

```python
# ui/log_tab.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import datetime


class LogTab:
    def __init__(self, parent):
        self.frame = ttk.Frame(parent, padding=15)
        
        ttk.Label(self.frame, text="施工日志", font=('微软雅黑', 16, 'bold'), foreground='#2c3e55').pack(pady=(0, 15))
        btn_frame = ttk.Frame(self.frame)
        btn_frame.pack(pady=(0, 10))
        ttk.Button(btn_frame, text="生成当日日志", command=self._gen).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_frame, text="导出日志", command=self._export).pack(side=tk.LEFT)
        
        self.log_text = tk.Text(self.frame, font=('微软雅黑', 11), wrap=tk.WORD, bg="#ffffff", relief=tk.SUNKEN, padx=10, pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)
    
    def generate(self, total_piles, measured_count):
        today = datetime.date.today().strftime("%Y-%m-%d")
        log = f"施工日志 {today}\n\n总桩数：{total_piles}\n已实测：{measured_count}\n已浇筑：{measured_count}\n\n备注：________________________"
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(1.0, log)
    
    def _gen(self):
        self.generate(0, 0)
    
    def _export(self):
        t = self.log_text.get(1.0, tk.END)
        if not t.strip():
            messagebox.showwarning("提示", "无日志")
            return
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("文本文件", "*.txt")])
        if p:
            with open(p, "w", encoding="utf-8") as f:
                f.write(t)
            messagebox.showinfo("成功", "施工日志已导出")
```

- [ ] **Step 6: 验证所有Tab可导入**

Run: `python -c "from ui.data_tab import DataTab; from ui.predict_tab import PredictTab; from ui.record_tab import RecordTab; from ui.log_tab import LogTab; print('All tabs OK')"`
Expected: `All tabs OK`

- [ ] **Step 7: 提交**

```bash
git add ui/
git commit -m "feat: add UI tabs — data, predict, record, log extracted from main file"
```

---

### Task 6: ui/view3d_tab.py + assets/scene.html — WebGL 3D

**Files:**
- Create: `ui/view3d_tab.py`
- Create: `assets/scene.html`

- [ ] **Step 1: 创建 ui/view3d_tab.py**

```python
# ui/view3d_tab.py
import tkinter as tk
from tkinter import ttk
import json
import webview


class View3DTab:
    def __init__(self, parent, store, engine):
        self.store = store
        self.engine = engine
        self.frame = ttk.Frame(parent, padding=15)
        self.webview_window = None
        
        ttk.Label(self.frame, text="3D 桩基土层立体视图", font=('微软雅黑', 16, 'bold'), foreground='#2c3e55').pack(pady=(0, 15))
        
        btn_row = ttk.Frame(self.frame)
        btn_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(btn_row, text="启动 3D 视图", command=self._launch_3d).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_row, text="刷新数据", command=self._refresh_data).pack(side=tk.LEFT, padx=(0, 10))
        
        self.status_var = tk.StringVar(value="点击「启动 3D 视图」打开交互窗口")
        ttk.Label(self.frame, textvariable=self.status_var, foreground='#666').pack()
    
    def _get_scene_data(self):
        geo = self.store.geo_data
        pile = self.store.pile_data
        
        if geo.empty or pile.empty:
            return json.dumps({"error": "请先加载数据"})
        
        layers = self.engine.get_layer_list()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']
        
        boreholes = []
        for hid, g in geo.groupby("孔号"):
            g = g.sort_values("土层顶标高", ascending=False)
            hole_layers = []
            for _, r in g.iterrows():
                color_idx = layers.index(r["土层名称"]) if r["土层名称"] in layers else 0
                hole_layers.append({
                    "name": r["土层名称"],
                    "top": float(r["土层顶标高"]),
                    "bottom": float(r["土层底标高"]),
                    "color": colors[color_idx % len(colors)]
                })
            boreholes.append({
                "id": str(hid),
                "x": float(g["X"].iloc[0]),
                "y": float(g["Y"].iloc[0]),
                "layers": hole_layers
            })
        
        piles = []
        for _, p in pile.iterrows():
            pno = str(p["桩号"])
            if pno in getattr(self, '_cached_predicts', {}):
                res = getattr(self, '_cached_predicts', {})[pno]
            else:
                res = self.engine.predict_one(pno)
                if not hasattr(self, '_cached_predicts'):
                    self._cached_predicts = {}
                self._cached_predicts[pno] = res
            
            if res is None:
                continue
            
            pile_layers = []
            current_z = res["桩顶标高"]
            for lay in res["土层排序"]:
                z = res["土层预测"].get(lay, current_z)
                color_idx = layers.index(lay) if lay in layers else 0
                pile_layers.append({
                    "name": lay,
                    "top": float(current_z),
                    "bottom": float(z),
                    "color": colors[color_idx % len(colors)]
                })
                current_z = z
            
            support_elev = res.get("持力层顶标高", None)
            piles.append({
                "id": pno,
                "x": float(p["X"]),
                "y": float(p["Y"]),
                "diameter": float(p["桩径"]),
                "pile_type": str(p.get("桩型", "未知")),
                "top_elev": float(res["桩顶标高"]),
                "support_elev": float(support_elev) if support_elev and support_elev != "未指定" else None,
                "support_depth": float(res.get("持力层进入深度(m)", 0)),
                "layers": pile_layers
            })
        
        all_z = []
        for b in boreholes:
            for l in b["layers"]:
                all_z.extend([l["top"], l["bottom"]])
        
        return json.dumps({
            "boreholes": boreholes,
            "piles": piles,
            "support_layer": self.store.support_layer,
            "bounds": {
                "x": [float(geo["X"].min()), float(geo["X"].max())],
                "y": [float(geo["Y"].min()), float(geo["Y"].max())],
                "z": [min(all_z) if all_z else -30, max(all_z) if all_z else 5]
            }
        }, ensure_ascii=False)
    
    def _launch_3d(self):
        if self.store.geo_data.empty or self.store.pile_data.empty:
            self.status_var.set("请先加载地勘和桩基数据")
            return
        
        self.status_var.set("3D视图正在加载...")
        
        import os
        html_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "scene.html")
        
        class Api:
            def __init__(self, tab):
                self.tab = tab
            def get_scene_data(self):
                return self.tab._get_scene_data()
            def on_pile_click(self, pile_id):
                print(f"[3D] Pile clicked: {pile_id}")
            def on_borehole_click(self, hole_id):
                print(f"[3D] Borehole clicked: {hole_id}")
        
        api = Api(self)
        self.webview_window = webview.create_window(
            "3D 桩基土层视图",
            html_path,
            js_api=api,
            width=1200,
            height=800,
            resizable=True
        )
        self.status_var.set("3D视图已打开 — 旋转:鼠标左键拖拽 | 缩放:滚轮 | 平移:鼠标右键拖拽")
        webview.start()
    
    def _refresh_data(self):
        if hasattr(self, '_cached_predicts'):
            del self._cached_predicts
        self.status_var.set("数据已刷新，请关闭3D窗口后重新启动")
```

- [ ] **Step 2: 创建 assets/scene.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>3D 桩基土层视图</title>
<style>
  body { margin: 0; overflow: hidden; font-family: 'Microsoft YaHei', sans-serif; }
  #info { position: absolute; top: 20px; left: 20px; color: #333; background: rgba(255,255,255,0.9); padding: 10px 16px; border-radius: 6px; pointer-events: none; font-size: 14px; }
  #tooltip { position: absolute; display: none; background: rgba(0,0,0,0.85); color: #fff; padding: 10px 14px; border-radius: 8px; font-size: 13px; pointer-events: none; max-width: 280px; line-height: 1.5; }
  #panel { position: absolute; top: 20px; right: 20px; background: rgba(255,255,255,0.95); padding: 14px 18px; border-radius: 8px; font-size: 13px; max-width: 300px; display: none; box-shadow: 0 2px 10px rgba(0,0,0,0.15); }
  #panel h3 { margin: 0 0 8px 0; font-size: 15px; }
  #panel p { margin: 4px 0; }
  button { margin: 4px; padding: 6px 12px; border: 1px solid #ccc; border-radius: 4px; background: #fff; cursor: pointer; font-size: 12px; }
  button:hover { background: #eee; }
  #controls { position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%); display: flex; gap: 8px; }
</style>
</head>
<body>
<div id="info">加载中...</div>
<div id="tooltip"></div>
<div id="panel"><h3 id="panel_title"></h3><div id="panel_content"></div></div>
<div id="controls">
  <button onclick="setView('front')">正视</button>
  <button onclick="setView('top')">俯视</button>
  <button onclick="setView('side')">侧视</button>
  <button onclick="resetView()">重置</button>
</div>

<script type="importmap">
{
  "imports": {
    "three": "https://unpkg.com/three@0.160.0/build/three.module.js",
    "three/addons/": "https://unpkg.com/three@0.160.0/examples/jsm/"
  }
}
</script>

<script type="module">
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CSS2DRenderer, CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf0f0f0);
scene.fog = new THREE.Fog(0xf0f0f0, 50, 200);

const camera = new THREE.PerspectiveCamera(50, window.innerWidth / window.innerHeight, 0.5, 500);
camera.position.set(60, 40, 60);

const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
document.body.appendChild(renderer.domElement);

const labelRenderer = new CSS2DRenderer();
labelRenderer.setSize(window.innerWidth, window.innerHeight);
labelRenderer.domElement.style.position = 'absolute';
labelRenderer.domElement.style.top = '0';
labelRenderer.domElement.style.pointerEvents = 'none';
document.body.appendChild(labelRenderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.target.set(30, -5, 30);
controls.update();

const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();
const tooltip = document.getElementById('tooltip');
const panel = document.getElementById('panel');
const info = document.getElementById('info');

let pileMeshes = [];
let boreholeLines = [];
let sceneData = null;

function createBoreholes(data) {
  const group = new THREE.Group();
  boreholeLines = [];
  
  data.boreholes.forEach(bh => {
    bh.layers.forEach((layer, i) => {
      const h = layer.top - layer.bottom;
      if (h <= 0) return;
      const geometry = new THREE.CylinderGeometry(0.15, 0.15, h, 6);
      const material = new THREE.MeshStandardMaterial({ color: layer.color, roughness: 0.6 });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(bh.x, bh.y, (layer.top + layer.bottom) / 2);
      mesh.userData = { type: 'borehole', holeId: bh.id, layerName: layer.name, x: bh.x, y: bh.y, top: layer.top, bottom: layer.bottom };
      group.add(mesh);
      boreholeLines.push(mesh);
    });
    
    const div = document.createElement('div');
    div.textContent = bh.id;
    div.style.cssText = 'font-size:10px;color:#333;background:rgba(255,255,255,0.85);padding:2px 5px;border-radius:3px;';
    const label = new CSS2DObject(div);
    const maxZ = Math.max(...bh.layers.map(l => l.top));
    label.position.set(bh.x, bh.y, maxZ + 1);
    group.add(label);
  });
  
  return group;
}

function createPiles(data) {
  const group = new THREE.Group();
  pileMeshes = [];
  
  data.piles.forEach(pile => {
    pile.layers.forEach(layer => {
      const h = layer.top - layer.bottom;
      if (h <= 0) return;
      const r = pile.diameter / 2000;
      const geometry = new THREE.CylinderGeometry(r, r, h, 20);
      const material = new THREE.MeshStandardMaterial({ color: layer.color, roughness: 0.4, metalness: 0.1 });
      const mesh = new THREE.Mesh(geometry, material);
      mesh.position.set(pile.x, pile.y, (layer.top + layer.bottom) / 2);
      mesh.userData = {
        type: 'pile', pileId: pile.id, diameter: pile.diameter, pileType: pile.pile_type,
        topElev: pile.top_elev, supportElev: pile.support_elev, supportDepth: pile.support_depth,
        x: pile.x, y: pile.y
      };
      group.add(mesh);
      pileMeshes.push(mesh);
    });
    
    const div = document.createElement('div');
    div.textContent = pile.id;
    div.style.cssText = 'font-size:11px;color:#c0392b;background:rgba(255,255,200,0.9);padding:2px 6px;border-radius:3px;font-weight:bold;';
    const label = new CSS2DObject(div);
    label.position.set(pile.x, pile.y, pile.top_elev + 0.8);
    group.add(label);
  });
  
  return group;
}

function createGround(bounds) {
  const w = bounds.x[1] - bounds.x[0];
  const d = bounds.y[1] - bounds.y[0];
  const cx = (bounds.x[0] + bounds.x[1]) / 2;
  const cy = (bounds.y[0] + bounds.y[1]) / 2;
  
  const geometry = new THREE.PlaneGeometry(w * 1.3, d * 1.3);
  const material = new THREE.MeshBasicMaterial({ color: 0xcccccc, side: THREE.DoubleSide, transparent: true, opacity: 0.2 });
  const ground = new THREE.Mesh(geometry, material);
  ground.rotation.x = -Math.PI / 2;
  ground.position.set(cx, cy, bounds.z[0] - 0.5);
  return ground;
}

function createSupportPlane(data) {
  if (!data.support_layer) return new THREE.Group();
  
  const w = data.bounds.x[1] - data.bounds.x[0];
  const d = data.bounds.y[1] - data.bounds.y[0];
  const cx = (data.bounds.x[0] + data.bounds.x[1]) / 2;
  const cy = (data.bounds.y[0] + data.bounds.y[1]) / 2;
  
  let avgZ = data.bounds.z[0];
  let count = 0;
  data.piles.forEach(p => {
    if (p.support_elev != null) { avgZ += p.support_elev; count++; }
  });
  if (count > 0) avgZ /= (count + 1);
  
  const geometry = new THREE.PlaneGeometry(w * 1.1, d * 1.1);
  const material = new THREE.MeshBasicMaterial({ color: 0xff4444, side: THREE.DoubleSide, transparent: true, opacity: 0.15 });
  const plane = new THREE.Mesh(geometry, material);
  plane.rotation.x = -Math.PI / 2;
  plane.position.set(cx, cy, avgZ);
  return plane;
}

function initScene(data) {
  sceneData = data;
  
  scene.children.forEach(c => { if (c.type !== 'Scene' && c.type !== 'Fog') scene.remove(c); });
  
  scene.add(createGround(data.bounds));
  scene.add(createBoreholes(data));
  scene.add(createPiles(data));
  scene.add(createSupportPlane(data));
  
  const light1 = new THREE.DirectionalLight(0xffffff, 1.2);
  light1.position.set(50, 30, 60);
  scene.add(light1);
  
  const light2 = new THREE.AmbientLight(0x606060, 0.6);
  scene.add(light2);
  
  info.textContent = `勘探孔: ${data.boreholes.length} | 桩基: ${data.piles.length} | 持力层: ${data.support_layer || '未指定'}`;
}

function setView(dir) {
  const target = controls.target.clone();
  const dist = 60;
  if (dir === 'front') camera.position.set(target.x, target.y, target.z + dist);
  else if (dir === 'top') camera.position.set(target.x, target.y + dist, target.z + 0.1);
  else if (dir === 'side') camera.position.set(target.x + dist, target.y, target.z);
  controls.update();
}

function resetView() {
  camera.position.set(60, 40, 60);
  controls.target.set(30, -5, 30);
  controls.update();
}

window.addEventListener('mousemove', (e) => {
  mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
  mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
  
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(pileMeshes.concat(boreholeLines));
  
  if (intersects.length > 0) {
    const obj = intersects[0].object;
    if (obj.userData.type === 'pile') {
      const d = obj.userData;
      const pileLength = d.supportElev != null ? (d.topElev - (d.supportElev - d.supportDepth)).toFixed(2) : '未知';
      tooltip.innerHTML = `
        <b>桩号: ${d.pileId}</b><br>
        桩径: ${d.diameter}mm | 桩型: ${d.pileType}<br>
        桩顶标高: ${d.topElev.toFixed(2)}m<br>
        持力层顶标高: ${d.supportElev != null ? d.supportElev.toFixed(2) : '未知'}m<br>
        桩长: ${pileLength}m
      `;
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX + 15) + 'px';
      tooltip.style.top = (e.clientY + 15) + 'px';
    } else if (obj.userData.type === 'borehole') {
      const d = obj.userData;
      tooltip.innerHTML = `<b>勘探孔: ${d.holeId}</b><br>坐标: X=${d.x.toFixed(1)} Y=${d.y.toFixed(1)}`;
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX + 15) + 'px';
      tooltip.style.top = (e.clientY + 15) + 'px';
    }
  } else {
    tooltip.style.display = 'none';
  }
});

window.addEventListener('click', (e) => {
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(pileMeshes.concat(boreholeLines));
  
  if (intersects.length > 0) {
    const obj = intersects[0].object;
    if (obj.userData.type === 'pile') {
      const d = obj.userData;
      document.getElementById('panel_title').textContent = `桩基: ${d.pileId}`;
      document.getElementById('panel_content').innerHTML = `
        <p>桩型: ${d.pileType}</p><p>桩径: ${d.diameter}mm</p>
        <p>桩顶标高: ${d.topElev.toFixed(2)}m</p>
        <p>持力层顶标高: ${d.supportElev != null ? d.supportElev.toFixed(2) + 'm' : '未知'}</p>
        <p>进入持力层: ${d.supportDepth.toFixed(2)}m</p>
      `;
      panel.style.display = 'block';
      if (window.exposed && window.exposed.on_pile_click) {
        window.exposed.on_pile_click(d.pileId);
      }
    }
  } else {
    panel.style.display = 'none';
  }
});

window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
  labelRenderer.setSize(window.innerWidth, window.innerHeight);
});

function loadData() {
  if (window.exposed && window.exposed.get_scene_data) {
    const raw = window.exposed.get_scene_data();
    const data = JSON.parse(raw);
    if (data.error) {
      info.textContent = '错误: ' + data.error;
      return;
    }
    initScene(data);
  } else {
    info.textContent = '未连接到Python后端，显示演示数据';
  }
}

function animate() {
  requestAnimationFrame(animate);
  controls.update();
  renderer.render(scene, camera);
  labelRenderer.render(scene, camera);
}

setTimeout(loadData, 500);
animate();
</script>
</body>
</html>
```

- [ ] **Step 3: 安装 pywebview 依赖**

Run: `pip install pywebview`
Expected: Successfully installed

- [ ] **Step 4: 验证 — Python导入view3d_tab不报错**

Run: `python -c "from ui.view3d_tab import View3DTab; print('View3DTab OK')"`
Expected: `View3DTab OK`

- [ ] **Step 5: 提交**

```bash
git add ui/view3d_tab.py assets/scene.html
git commit -m "feat: add WebGL 3D view — Three.js via pywebview replacing Matplotlib 3D"
```

---

### Task 7: main.py — 组装入口，删除旧文件

**Files:**
- Create: `main.py`
- Delete: `桩基土层预测系统.py`

- [ ] **Step 1: 创建 main.py**

```python
# main.py
import tkinter as tk
from tkinter import ttk
import warnings
import matplotlib.pyplot as plt
warnings.filterwarnings('ignore')

plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = '#f2f2f0'
plt.rcParams['axes.facecolor'] = '#ffffff'

from core.data_layer import DataStore
from core.prediction import PredictEngine
from core.bearing_capacity import BearingCalc
from ui.data_tab import DataTab
from ui.predict_tab import PredictTab
from ui.view3d_tab import View3DTab
from ui.record_tab import RecordTab
from ui.log_tab import LogTab


class PileApp:
    def __init__(self, root):
        self.root = root
        self.root.title("桩基土层标高预测系统 | 工程版")
        self.root.geometry("1920x1080")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._init_style()
        
        self.store = DataStore()
        self.measured_data = self.store.load()
        self.engine = PredictEngine(self.store)
        self.bearing = BearingCalc(self.store, self.engine)
        
        self.notebook = ttk.Notebook(root, padding=10)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.data_tab = DataTab(self.notebook, self.store, self.engine)
        self.predict_tab = PredictTab(self.notebook, self.store, self.engine, self.bearing)
        self.view3d_tab = View3DTab(self.notebook, self.store, self.engine)
        self.record_tab = RecordTab(self.notebook, self.store)
        self.log_tab = LogTab(self.notebook)
        
        self.notebook.add(self.data_tab.frame, text="数据管理")
        self.notebook.add(self.predict_tab.frame, text="预测与实测管理")
        self.notebook.add(self.view3d_tab.frame, text="3D 桩基土层视图")
        self.notebook.add(self.record_tab.frame, text="单桩打桩记录")
        self.notebook.add(self.log_tab.frame, text="施工日志")
        
        self.predict_tab.measured_data = self.measured_data
        self.predict_tab.on_pile_selected_callback = self._on_pile_selected
        
        self._auto_refresh()
    
    def _init_style(self):
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TLabel', font=('微软雅黑', 10), foreground='#2c3e55')
        style.configure('TButton', font=('微软雅黑', 10), padding=6)
        style.configure('TEntry', font=('微软雅黑', 10))
        style.configure('TCombobox', font=('微软雅黑', 10))
        style.configure('Treeview', font=('微软雅黑', 9), rowheight=25)
        style.configure('TLabelframe', font=('微软雅黑', 11, 'bold'))
        style.configure('TLabelframe.Label', font=('微软雅黑', 11, 'bold'), foreground='#2980b9')
    
    def _auto_refresh(self):
        if not self.store.geo_data.empty:
            self.data_tab.support_cb.config(values=self.store.get_layer_list())
        if not self.store.pile_data.empty:
            self.predict_tab.refresh_pile_combobox()
            self.data_tab.refresh_pile_tree()
        self.data_tab.method_cb.set(self.store.interp_method)
    
    def _on_pile_selected(self, pno):
        self.record_tab.generate(self.predict_tab.current_pile_result, self.measured_data)
        self.log_tab.generate(len(self.engine.get_pile_list()), len(self.measured_data))
    
    def _on_close(self):
        self.store.save()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = PileApp(root)
    root.mainloop()
```

- [ ] **Step 2: 删除旧文件**

Run: `rm 桩基土层预测系统.py` (in bash: remove old single file)

- [ ] **Step 3: 启动程序验证**

Run: `python main.py`
Expected: Tkinter窗口正常启动，5个Tab全部显示，3D按钮可用

- [ ] **Step 4: 提交**

```bash
git add main.py
git rm 桩基土层预测系统.py
git commit -m "feat: add main.py entry point, remove old single-file app"
```

---

## 最终验证清单

全部7个Task完成后，运行以下验证：
- [ ] `python main.py` — 程序启动，5个Tab显示正常
- [ ] 数据管理页 — 加载地勘Excel、加载桩基Excel成功
- [ ] 预测页 — 选择桩号可预测，2D图显示正常
- [ ] 3D视图 — 点击启动打开新窗口，Three.js场景渲染勘探孔+桩体，旋转缩放流畅
- [ ] 承载力 — BearingCalc可导入测试参数CSV并计算
- [ ] 打桩记录 — 选择桩后记录自动生成
- [ ] 关闭程序 — 数据自动保存到 project_full_data.json，再打开数据恢复
