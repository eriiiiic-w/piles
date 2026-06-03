import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
from pykrige import OrdinaryKriging
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D
import os
import datetime
import json
import warnings
import matplotlib.colors as mcolors
warnings.filterwarnings('ignore')

# 全局样式设置
plt.rcParams['font.sans-serif'] = ['SimHei']
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['figure.facecolor'] = '#f0f2f6'
plt.rcParams['axes.facecolor'] = '#ffffff'

# =========================== 全局数据持久化（彻底修复：开机自动加载所有数据） ===========================
SAVE_FILE = "project_full_data.json"

def save_system_data(predictor, measured_data):
    data = {
        "geo_data": predictor.geo_data.to_dict("records") if not predictor.geo_data.empty else [],
        "pile_data": predictor.pile_data.to_dict("records") if not predictor.pile_data.empty else [],
        "measured_data": measured_data,
        "support_layer": predictor.support_layer,
        "support_depth": predictor.support_depth,
        "support_depth_type": predictor.support_depth_type,
        "user_pile_top_elev": predictor.user_pile_top_elev,
        "warning_threshold": predictor.warning_threshold,
        "alarm_threshold": predictor.alarm_threshold,
        "interp_method": predictor.interp_method,
        "layer_friction": predictor.layer_friction,
        "end_resistance": predictor.end_resistance,
        "safety_factor": predictor.safety_factor
    }
    with open(SAVE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_system_data(predictor):
    if not os.path.exists(SAVE_FILE):
        return {}
    with open(SAVE_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if data.get("geo_data"):
        predictor.geo_data = pd.DataFrame(data["geo_data"])
    if data.get("pile_data"):
        predictor.pile_data = pd.DataFrame(data["pile_data"])
    
    predictor.support_layer = data.get("support_layer", "")
    predictor.support_depth = data.get("support_depth", 1.5)
    predictor.support_depth_type = data.get("support_depth_type", "直接输入")
    predictor.user_pile_top_elev = data.get("user_pile_top_elev", 0.5)
    predictor.warning_threshold = data.get("warning_threshold", 0.3)
    predictor.alarm_threshold = data.get("alarm_threshold", 0.5)
    predictor.interp_method = data.get("interp_method", "克里金法")
    predictor.layer_friction = data.get("layer_friction", {})
    predictor.end_resistance = data.get("end_resistance", {})
    predictor.safety_factor = data.get("safety_factor", 2.0)
    
    return data.get("measured_data", {})

# =========================== 核心预测类（完全恢复原预测算法+保留IDW+其他功能） ===========================
class LayerElevationPredictor:
    def __init__(self):
        self.geo_data = pd.DataFrame()
        self.pile_data = pd.DataFrame()
        self.support_layer = ""
        self.support_depth = 1.5
        self.support_depth_type = "直接输入"
        self.user_pile_top_elev = 0.5
        self.warning_threshold = 0.3
        self.alarm_threshold = 0.5
        self.interp_method = "克里金法"  # 保留算法选择
        # ====== 承载力预测参数 ======
        self.layer_friction = {}   # 各土层侧摩阻力特征值 {土层名称: qsik值}
        self.end_resistance = {}   # 各土层端阻力特征值 {土层名称: qpk值}
        self.safety_factor = 2.0   # 安全系数

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

    def _calc_geo_bottom_elev(self, geo_df):
        adjusted_df = []
        for 孔号, 孔数据 in geo_df.groupby('孔号'):
            孔数据 = 孔数据.sort_values('土层顶标高', ascending=False).reset_index(drop=True)
            for i in range(len(孔数据)):
                土层 = 孔数据.iloc[i]
                if pd.notna(土层['土层厚度']) and 土层['土层厚度'] > 0:
                    土层['土层底标高'] = 土层['土层顶标高'] - 土层['土层厚度']
                else:
                    土层['土层厚度'] = 2.0
                    土层['土层底标高'] = 土层['土层顶标高'] - 2.0
                adjusted_df.append(土层)
        return pd.DataFrame(adjusted_df)

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

    def export_measured_geo_holes(self):
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
        土层平均标高 = self.geo_data.groupby('土层名称')['土层顶标高'].mean().sort_values(ascending=False)
        return list(土层平均标高.index)

    def get_pile_list(self):
        if self.pile_data.empty:
            return []
        return list(self.pile_data['桩号'].unique())

    # 保留IDW反距离加权算法（原版本新增功能，非核心预测逻辑）
    def idw_interpolate(self, x, y, xv, yv, val):
        distances = np.sqrt((xv - x)**2 + (yv - y)**2)
        if np.any(distances == 0):
            return float(val[np.argmin(distances)])
        weights = 1 / (distances ** 2)
        return float(np.sum(weights * val) / np.sum(weights))

    # ====================================== 【核心原算法】桩位土层顶标高原预测算法 ======================================
    def predict_pile_layers(self, pile_no):
        if self.geo_data.empty or self.pile_data.empty:
            return None, "请先加载地勘和桩基数据"
        pile_info = self.pile_data[self.pile_data['桩号'] == pile_no]
        if pile_info.empty:
            return None, f"未找到桩号{pile_no}的信息"

        pile_x = pile_info['X'].values[0]
        pile_y = pile_info['Y'].values[0]
        pile_diameter = pile_info['桩径'].values[0]
        pile_type = pile_info['桩型'].values[0] if '桩型' in pile_info.columns else '未知'
        layer_list = self.get_layer_list()

        predict_result = {
            "桩号": pile_no,
            "X坐标": pile_x, "Y坐标": pile_y,
            "桩径(mm)": pile_diameter,
            "桩型": pile_type,
            "土层预测": {},
            "土层底标高预测": {},
            "土层排序": layer_list,
            "桩顶标高": self.user_pile_top_elev
        }

        # 【完全恢复原逻辑】单土层顶标高预测 - 克里金法原执行方式/均值兜底，与原始版本完全一致
        for layer in layer_list:
            layer_data = self.geo_data[self.geo_data['土层名称'] == layer]
            if len(layer_data) < 2:
                # 数据量不足时取均值，原逻辑
                z_pred = round(layer_data['土层顶标高'].mean() if not layer_data.empty else 10.0, 2)
            else:
                try:
                    if self.interp_method == "克里金法":
                        # 【原算法核心】克里金法原始执行参数，未做任何修改
                        ok = OrdinaryKriging(layer_data['X'].values, layer_data['Y'].values, layer_data['土层顶标高'].values,
                                             variogram_model='spherical', enable_plotting=False)
                        z, _ = ok.execute('points', np.array([pile_x]), np.array([pile_y]))
                        z_pred = round(z[0], 2)
                    else:
                        # 保留IDW算法，原版本新增功能
                        z_pred = self.idw_interpolate(pile_x, pile_y, layer_data['X'].values,
                                                      layer_data['Y'].values, layer_data['土层顶标高'].values)
                        z_pred = round(z_pred, 2)
                except Exception as e:
                    # 异常时取均值兜底，原逻辑
                    z_pred = round(layer_data['土层顶标高'].mean(), 2)
            predict_result["土层预测"][layer] = z_pred

        # 【完全恢复原逻辑】土层底标高预测，与原始版本完全一致
        for i, layer in enumerate(layer_list):
            if i < len(layer_list)-1:
                predict_result["土层底标高预测"][layer] = predict_result["土层预测"][layer_list[i+1]]
            else:
                avg_thick = self.geo_data[self.geo_data['土层名称']==layer]['土层厚度'].mean()
                predict_result["土层底标高预测"][layer] = round(predict_result["土层预测"][layer] - avg_thick, 2)

        # 【完全恢复原逻辑】持力层深度计算，与原始版本完全一致
        support_depth = self.calculate_support_depth(pile_diameter)
        if self.support_layer in predict_result["土层预测"]:
            support_elev = predict_result["土层预测"][self.support_layer]
            predict_result["持力层顶标高"] = support_elev
            predict_result["持力层进入深度(m)"] = support_depth
        else:
            predict_result["持力层顶标高"] = "未指定"
            predict_result["持力层进入深度(m)"] = support_depth

        return predict_result, "单桩预测完成"
    # ====================================== 【核心原算法结束】 ======================================

    def calculate_support_depth(self, d):
        if self.support_depth_type == "n倍桩径":
            return self.support_depth * (d / 1000)
        return self.support_depth

    # ====================== 承载力预测（新增功能） ======================
    def get_pile_segment_thicknesses(self, pile_result):
        """计算桩在各土层中的穿越厚度（li）"""
        layer_list = pile_result["土层排序"]
        pile_top = pile_result["桩顶标高"]
        support_layer = pile_result.get("持力层顶标高", 0)
        support_depth = pile_result.get("持力层进入深度(m)", 0)
        if isinstance(support_layer, str):
            return {}, "未设置持力层"
        pile_bottom = support_layer - support_depth

        thicknesses = {}
        for layer in layer_list:
            lay_top = pile_result["土层预测"].get(layer, 0)
            lay_bottom = pile_result["土层底标高预测"].get(layer, lay_top - 2.0)
            overlap_top = min(pile_top, lay_top)
            overlap_bottom = max(pile_bottom, lay_bottom)
            thick = max(0, round(overlap_top - overlap_bottom, 2))
            if thick > 0:
                thicknesses[layer] = thick
        return thicknesses, ""

    def calculate_pile_bearing_capacity(self, pile_no):
        """计算单桩竖向承载力特征值 Ra"""
        # 先获取该桩的土层预测
        pile_result, msg = self.predict_pile_layers(pile_no)
        if pile_result is None:
            return None, msg

        # 获取桩穿越各土层的厚度
        thicknesses, err = self.get_pile_segment_thicknesses(pile_result)
        if err:
            return None, err

        d = pile_result["桩径(mm)"] / 1000  # 桩径转米
        u = round(np.pi * d, 3)              # 桩周长
        Ap = round(np.pi * d * d / 4, 4)     # 桩端面积

        Qsk = 0  # 总侧阻力
        missing_layers = []
        for layer, thick in thicknesses.items():
            qsik = self.layer_friction.get(layer, 0)
            if qsik <= 0:
                missing_layers.append(layer)
            Qsk += qsik * thick
        Qsk = round(Qsk * u, 2)

        # 端阻力
        support_layer = pile_result.get("持力层顶标高", "未指定")
        if isinstance(support_layer, str):
            qpk = 0
        else:
            # 找到实际持力层名称
            sup_name = self.support_layer
            qpk = self.end_resistance.get(sup_name, 0)
        Qpk = round(qpk * Ap, 2)

        Quk = Qsk + Qpk  # 极限承载力
        Ra = round(Quk / self.safety_factor, 2)  # 特征值

        result = {
            "桩号": pile_no,
            "桩径(m)": d,
            "桩周长u(m)": u,
            "桩端面积Ap(m²)": Ap,
            "侧摩阻力Qsk(kN)": Qsk,
            "端阻力Qpk(kN)": Qpk,
            "极限承载力Quk(kN)": Quk,
            "安全系数K": self.safety_factor,
            "承载力特征值Ra(kN)": Ra,
            "各土层穿越厚度(m)": thicknesses,
            "缺失参数土层": missing_layers
        }
        return result, "" if not missing_layers else f"以下土层未设置侧摩阻力：{', '.join(missing_layers)}"

    def calculate_all_bearing_capacity(self):
        """批量计算所有桩承载力"""
        results = []
        warnings = []
        for pno in self.get_pile_list():
            res, msg = self.calculate_pile_bearing_capacity(pno)
            if res:
                results.append(res)
                if msg:
                    warnings.append(msg)
        return results, warnings

    # 【恢复原逻辑】批量预测，与原始版本完全一致
    def predict_all_piles(self):
        if self.geo_data.empty or self.pile_data.empty:
            return None, "请先加载数据"
        all_res = []
        for p in self.get_pile_list():
            res,_ = self.predict_pile_layers(p)
            if res:
                flat = {"桩号":res["桩号"],"X":res["X坐标"],"Y":res["Y坐标"],"桩径":res["桩径(mm)"],"桩型":res["桩型"],
                        "持力层顶标高":res["持力层顶标高"],"桩顶标高":res["桩顶标高"]}
                for k in res["土层预测"]:
                    flat[f"{k}顶标高"] = res["土层预测"][k]
                all_res.append(flat)
        return pd.DataFrame(all_res), f"共{len(all_res)}根桩预测完成"

# =========================== 主界面（仅修改标签显示视角，其余全不变） ===========================
class PilePredictionGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("桩基土层标高预测系统 | 工程版")
        self.root.geometry("1920x1080")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TLabel', font=('微软雅黑', 10), foreground='#2c3e50')
        self.style.configure('TButton', font=('微软雅黑', 10), padding=6)
        self.style.configure('TEntry', font=('微软雅黑', 10))
        self.style.configure('TCombobox', font=('微软雅黑', 10))
        self.style.configure('Treeview', font=('微软雅黑', 9), rowheight=25)
        self.style.configure('TLabelframe', font=('微软雅黑', 11, 'bold'))
        self.style.configure('TLabelframe.Label', font=('微软雅黑', 11, 'bold'), foreground='#2980b9')

        self.predictor = LayerElevationPredictor()
        self.measured_data = load_system_data(self.predictor)
        self.pile_original_predicts = {}  # 保存首次预测结果，确保实测后数据不变
        self.current_pile_result = None
        
        self.notebook = ttk.Notebook(root, padding=10)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.tab_data = ttk.Frame(self.notebook, padding=15)
        self.tab_predict = ttk.Frame(self.notebook, padding=15)
        self.tab_3d = ttk.Frame(self.notebook, padding=15)
        self.tab_record = ttk.Frame(self.notebook, padding=15)
        self.tab_log = ttk.Frame(self.notebook, padding=15)
        self.tab_bearing = ttk.Frame(self.notebook, padding=15)
        self.notebook.add(self.tab_data, text="📊 数据管理")
        self.notebook.add(self.tab_predict, text="🔍 预测与实测管理")
        self.notebook.add(self.tab_3d, text="🌍 3D 桩基土层视图")
        self.notebook.add(self.tab_record, text="📝 单桩打桩记录")
        self.notebook.add(self.tab_log, text="📋 施工日志")
        self.notebook.add(self.tab_bearing, text="🔩 承载力预测")

        self.init_data_tab()
        self.init_predict_tab()
        self.init_3d_tab()
        self.init_record_tab()
        self.init_log_tab()
        self.init_bearing_tab()
        
        # 启动自动刷新界面（修复开机不加载）
        self.auto_refresh_at_start()
        
        # 存储3D点击提示框和标签
        self.annotation_3d = None
        self.point_labels = {}  # 存储桩号/勘探孔号标签

    def auto_refresh_at_start(self):
        if not self.predictor.geo_data.empty:
            self.support_cb.config(values=self.predictor.get_layer_list())
        if not self.predictor.pile_data.empty:
            self.refresh_pile_combobox()
            self.refresh_bearing_combobox()
            for _, r in self.predictor.pile_data.iterrows():
                self.pile_tree.insert("", "end", values=(r["桩号"], r["X"], r["Y"], r["桩径"], r.get("桩型", "未知")))
        self.method_cb.set(self.predictor.interp_method)
        self.status.set("系统已加载全部历史数据")

    def on_close(self):
        save_system_data(self.predictor, self.measured_data)
        self.root.destroy()

    # ====================== 数据管理（完全不变） ======================
    def init_data_tab(self):
        ttk.Label(self.tab_data, text="数据管理中心", font=('微软雅黑', 16, 'bold'), foreground='#2c3e50').pack(pady=(0, 15))
        geo_frame = ttk.LabelFrame(self.tab_data, text="地勘数据管理", padding=12)
        geo_frame.pack(fill=tk.X, pady=(0, 10))
        geo_row = ttk.Frame(geo_frame)
        geo_row.pack(fill=tk.X)
        ttk.Button(geo_row, text="选择地勘文件", command=self.select_geo).pack(side=tk.LEFT, padx=(0, 10))
        self.geo_path = tk.StringVar()
        ttk.Entry(geo_row, textvariable=self.geo_path, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(geo_row, text="加载地勘", command=self.load_geo).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(geo_row, text="导出实测勘探孔Excel", command=self.export_measured_holes).pack(side=tk.LEFT)

        pile_frame = ttk.LabelFrame(self.tab_data, text="桩基数据管理", padding=12)
        pile_frame.pack(fill=tk.X, pady=(0, 10))
        pile_row = ttk.Frame(pile_frame)
        pile_row.pack(fill=tk.X)
        ttk.Button(pile_row, text="选择桩基文件", command=self.select_pile).pack(side=tk.LEFT, padx=(0, 10))
        self.pile_path = tk.StringVar()
        ttk.Entry(pile_row, textvariable=self.pile_path, width=50).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(pile_row, text="加载桩基", command=self.load_pile).pack(side=tk.LEFT)

        self.pile_tree = ttk.Treeview(pile_frame, columns=("桩号","X","Y","桩径","桩型"), show="headings", height=6)
        for c in self.pile_tree["columns"]:
            self.pile_tree.heading(c, text=c)
            self.pile_tree.column(c, width=120, anchor=tk.CENTER)
        self.pile_tree.pack(fill=tk.X, pady=(10, 0))

        set_frame = ttk.LabelFrame(self.tab_data, text="持力层与预警阈值设置", padding=12)
        set_frame.pack(fill=tk.X, pady=(0,10))
        set_row = ttk.Frame(set_frame)
        set_row.pack(fill=tk.X)
        ttk.Label(set_row, text="持力层：").pack(side=tk.LEFT, padx=(0,5))
        self.support_var = tk.StringVar(value=self.predictor.support_layer)
        self.support_cb = ttk.Combobox(set_row, textvariable=self.support_var, width=15)
        self.support_cb.pack(side=tk.LEFT, padx=(0,15))
        ttk.Label(set_row, text="深度方式：").pack(side=tk.LEFT, padx=(0,5))
        self.depth_mode = tk.StringVar(value=self.predictor.support_depth_type)
        ttk.Combobox(set_row, textvariable=self.depth_mode, values=["直接输入","n倍桩径"], width=10).pack(side=tk.LEFT, padx=(0,15))
        ttk.Label(set_row, text="深度：").pack(side=tk.LEFT, padx=(0,5))
        self.depth_val = tk.DoubleVar(value=self.predictor.support_depth)
        ttk.Entry(set_row, textvariable=self.depth_val, width=8).pack(side=tk.LEFT, padx=(0,15))
        ttk.Label(set_row, text="预警：").pack(side=tk.LEFT, padx=(0,5))
        self.warn_val = tk.DoubleVar(value=self.predictor.warning_threshold)
        ttk.Entry(set_row, textvariable=self.warn_val, width=5).pack(side=tk.LEFT, padx=(0,15))
        ttk.Label(set_row, text="报警：").pack(side=tk.LEFT, padx=(0,5))
        self.alarm_val = tk.DoubleVar(value=self.predictor.alarm_threshold)
        ttk.Entry(set_row, textvariable=self.alarm_val, width=5).pack(side=tk.LEFT, padx=(0,15))
        ttk.Button(set_row, text="确认设置", command=self.set_support).pack(side=tk.LEFT)

        # 保留插值算法选择
        method_frame = ttk.LabelFrame(self.tab_data, text="土层插值算法", padding=12)
        method_frame.pack(fill=tk.X)
        method_row = ttk.Frame(method_frame)
        method_row.pack(fill=tk.X)
        ttk.Label(method_row, text="选择算法：").pack(side=tk.LEFT, padx=(0,5))
        self.method_var = tk.StringVar(value=self.predictor.interp_method)
        self.method_cb = ttk.Combobox(method_row, textvariable=self.method_var, values=["克里金法", "IDW反距离加权"], width=15)
        self.method_cb.pack(side=tk.LEFT, padx=(0,10))
        ttk.Button(method_row, text="应用算法", command=self.set_interp_method).pack(side=tk.LEFT)

        self.status = tk.StringVar(value="系统就绪 | 数据自动保存已启用")
        status_bar = ttk.Label(self.tab_data, textvariable=self.status, relief=tk.SUNKEN, anchor=tk.W, padding=8)
        status_bar.pack(fill=tk.X, pady=(15, 0))

    def set_interp_method(self):
        self.predictor.interp_method = self.method_var.get()
        messagebox.showinfo("成功", f"已切换为：{self.predictor.interp_method}")

    def export_measured_holes(self):
        df, msg = self.predictor.export_measured_geo_holes()
        if df is None:
            messagebox.showwarning("提示", msg)
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel文件", "*.xlsx")])
        if path:
            df.to_excel(path, index=False)
            messagebox.showinfo("成功", f"导出完成")

    def select_geo(self):
        p = filedialog.askopenfilename(filetypes=[("Excel","*.xlsx")])
        if p:self.geo_path.set(p)
    def load_geo(self):
        ok,m = self.predictor.load_geo_data(self.geo_path.get())
        messagebox.showinfo("提示",m)
        self.support_cb.config(values=self.predictor.get_layer_list())
    def select_pile(self):
        p = filedialog.askopenfilename(filetypes=[("Excel","*.xlsx")])
        if p:self.pile_path.set(p)
    def load_pile(self):
        ok,m = self.predictor.load_pile_data(self.pile_path.get())
        self.pile_tree.delete(*self.pile_tree.get_children())
        for _,r in self.predictor.pile_data.iterrows():
            self.pile_tree.insert("","end",values=(r["桩号"],r["X"],r["Y"],r["桩径"],r.get("桩型","未知")))
        self.refresh_pile_combobox()
        self.refresh_bearing_combobox()
        messagebox.showinfo("提示",m)
    def set_support(self):
        self.predictor.support_layer = self.support_var.get()
        self.predictor.support_depth_type = self.depth_mode.get()
        self.predictor.support_depth = self.depth_val.get()
        self.predictor.warning_threshold = self.warn_val.get()
        self.predictor.alarm_threshold = self.alarm_val.get()
        messagebox.showinfo("成功","持力层、深度及预警阈值已设置")

    # ====================== 预测与实测管理（完全不变） ======================
    def init_predict_tab(self):
        ttk.Label(self.tab_predict, text="预测与实测管理", font=('微软雅黑', 16, 'bold'), foreground='#2c3e50').pack(pady=(0, 15))
        top = ttk.Frame(self.tab_predict)
        top.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(top, text="桩号：").pack(side=tk.LEFT, padx=(0, 5))
        self.pile_cb_var = tk.StringVar()
        self.pile_cb = ttk.Combobox(top, textvariable=self.pile_cb_var, width=15)
        self.pile_cb.pack(side=tk.LEFT, padx=(0, 15))
        self.pile_cb.bind("<<ComboboxSelected>>",self.on_pile_select)

        ttk.Button(top, text="全部桩基预测", command=self.predict_all).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(top, text="导出全部预测Excel", command=self.export_all_predict).pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(top, text="桩顶标高(m)：").pack(side=tk.LEFT, padx=(0, 5))
        self.pile_top_elev_var = tk.DoubleVar(value=0.5)
        ttk.Entry(top, textvariable=self.pile_top_elev_var, width=10).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(top, text="确认桩顶标高", command=self.set_pile_top_elev).pack(side=tk.LEFT)

        main = ttk.Frame(self.tab_predict)
        main.pack(fill=tk.BOTH, expand=True)
        left = ttk.LabelFrame(main, text="土层标高数据", padding=10)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        self.tree = ttk.Treeview(left, columns=("土层","预测顶标高","实测顶标高","误差","录入时间"), show="headings", height=12)
        cols = [("土层",150),("预测顶标高",130),("实测顶标高",130),("误差",90),("录入时间",190)]
        for c,w in cols:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor=tk.CENTER)
        self.tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        input_f = ttk.LabelFrame(left, text="实测数据录入", padding=10)
        input_f.pack(fill=tk.X)
        input_row = ttk.Frame(input_f)
        input_row.pack(fill=tk.X)
        ttk.Label(input_row, text="实测顶标高：").pack(side=tk.LEFT, padx=(0, 5))
        self.meas_val = tk.StringVar()
        ttk.Entry(input_row, textvariable=self.meas_val, width=10).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Label(input_row, text="实测进入持力层深度：").pack(side=tk.LEFT, padx=(0, 5))
        self.real_support_depth = tk.StringVar()
        ttk.Entry(input_row, textvariable=self.real_support_depth, width=10).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(input_row, text="确认录入", command=self.save_meas).pack(side=tk.LEFT)

        right = ttk.LabelFrame(main, text="土层与桩身示意图（预测/实测）", padding=10)
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        self.fig,self.ax = plt.subplots(figsize=(10, 12))
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def refresh_pile_combobox(self):
        self.pile_cb.config(values=self.predictor.get_pile_list())

    def set_pile_top_elev(self):
        val = self.pile_top_elev_var.get()
        self.predictor.user_pile_top_elev = val
        if self.current_pile_result:
            self.current_pile_result["桩顶标高"] = val
            self.auto_generate_record()
        messagebox.showinfo("成功",f"桩顶标高已设置为：{val} m")

    def export_all_predict(self):
        df, msg = self.predictor.predict_all_piles()
        if df is None:
            messagebox.showerror("错误", msg)
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel文件", "*.xlsx")])
        if path:
            df.to_excel(path, index=False)
            messagebox.showinfo("成功","导出完成")

    # 保留修复：实测数据录入后，重新点击桩号预测值/实测值/误差不变
    def on_pile_select(self,*args):
        pno = self.pile_cb_var.get()
        if not pno:
            return
        
        # 仅首次预测生成数据，后续直接复用，确保预测值不变
        if pno not in self.pile_original_predicts:
            res, m = self.predictor.predict_pile_layers(pno)
            if not res:
                messagebox.showerror("错误", m)
                return
            self.pile_original_predicts[pno] = res
        
        # 始终使用首次预测的原算法结果
        self.current_pile_result = self.pile_original_predicts[pno]
        
        self.tree.delete(*self.tree.get_children())
        meas = self.measured_data.get(pno, {})
        
        for lay in self.current_pile_result["土层排序"]:
            pred = self.current_pile_result["土层预测"][lay]
            m_val = meas.get(lay, {}).get("标高", "")
            m_time = meas.get(lay, {}).get("时间", "")
            err = round(float(m_val) - pred, 2) if m_val != "" else ""
            self.tree.insert("", "end", values=(lay, pred, m_val, err, m_time))
        
        self.pile_cb.config(foreground="red" if pno in self.measured_data else "black")
        self.draw_plot()
        self.auto_generate_record()

    def predict_all(self):
        df,m = self.predictor.predict_all_piles()
        messagebox.showinfo("成功", m)

    # ====================== 2D绘图（完全不变） ======================
    def draw_plot(self):
        self.ax.clear()
        res = self.current_pile_result
        pile_no = res["桩号"]
        layer_list = res["土层排序"]
        bar_width = 0.35
        x_pos = np.arange(len(layer_list))
        pile_x = len(layer_list) + 0.5

        pred_top_elevs = [res["土层预测"][layer] for layer in layer_list]
        pred_bottom_elevs = [res["土层底标高预测"][layer] for layer in layer_list]
        meas_top_elevs = []
        meas_bottom_elevs = []
        for i, layer in enumerate(layer_list):
            meas_data = self.measured_data.get(pile_no, {}).get(layer, {})
            meas_top = meas_data.get("标高")
            if meas_top is None:
                meas_top_elevs.append(None)
                meas_bottom_elevs.append(None)
            else:
                meas_top_elevs.append(meas_top)
                if i < len(layer_list)-1:
                    next_meas = self.measured_data.get(pile_no, {}).get(layer_list[i+1], {}).get("标高")
                    meas_bottom = next_meas if next_meas else meas_top - (pred_top_elevs[i]-pred_bottom_elevs[i])
                else:
                    meas_bottom = meas_top - (pred_top_elevs[i]-pred_bottom_elevs[i])
                meas_bottom_elevs.append(round(meas_bottom,2))

        for i in range(len(layer_list)):
            h = pred_top_elevs[i] - pred_bottom_elevs[i]
            self.ax.bar(x_pos[i]-bar_width/2, h, bar_width, bottom=pred_bottom_elevs[i],
                        color='#3498db', alpha=0.7, edgecolor='#2980b9', label='预测土层'if i==0 else "")
            self.ax.text(x_pos[i]-bar_width/2, pred_top_elevs[i]+0.1, f'{pred_top_elevs[i]:.2f}', ha='center', fontsize=9, color='#2980b9')

        for i in range(len(layer_list)):
            if meas_top_elevs[i] is not None:
                h = meas_top_elevs[i] - meas_bottom_elevs[i]
                self.ax.bar(x_pos[i]+bar_width/2, h, bar_width, bottom=meas_bottom_elevs[i],
                            color='#e74c3c', alpha=0.7, edgecolor='#c0392b', label='实测土层'if i==0 else "")
                self.ax.text(x_pos[i]+bar_width/2, meas_top_elevs[i]+0.1, f'{meas_top_elevs[i]:.2f}', ha='center', fontsize=9, color='#c0392b')

        pile_top = res["桩顶标高"]
        sup_elev = res.get("持力层顶标高",0)
        sup_depth = res.get("持力层进入深度(m)",0)
        pile_bottom = sup_elev - sup_depth
        self.ax.plot([pile_x,pile_x],[pile_top,pile_bottom],color="#e67e22",lw=12,label="桩体")
        self.ax.text(pile_x+0.2,pile_top,f"桩顶\n{pile_top:.1f}",color="#d35400",fontweight='bold')
        self.ax.text(pile_x+0.2,pile_bottom,f"桩底\n{pile_bottom:.1f}",color="#d35400",fontweight='bold')

        if self.predictor.support_layer in layer_list:
            idx = layer_list.index(self.predictor.support_layer)
            self.ax.annotate('持力层',xy=(x_pos[idx],pred_top_elevs[idx]),xytext=(x_pos[idx]+0.5,pred_top_elevs[idx]+1),
                              arrowprops=dict(arrowstyle='->',color='#f39c12',lw=2),fontsize=11,color='#f39c12',fontweight='bold')

        self.ax.set_ylim(min(pred_bottom_elevs)-2, max(pred_top_elevs)+3)
        self.ax.set_ylabel("标高(m)", fontsize=11)
        self.ax.set_title(f"{pile_no} 土层与桩身示意图",fontsize=14, pad=20)
        self.ax.set_xticks(np.append(x_pos,pile_x))
        self.ax.set_xticklabels(layer_list+["桩体"],rotation=45,ha="right")
        self.ax.legend(loc='upper right', fontsize=10)
        self.ax.grid(alpha=0.3)
        self.canvas.draw()

    # ====================== 3D视图（仅修改【标签显示视角】，其余全不变） ======================
    def init_3d_tab(self):
        ttk.Label(self.tab_3d, text="3D 桩基土层立体视图（米制单位｜可缩放旋转）", font=('微软雅黑', 16, 'bold'), foreground='#2c3e50').pack(pady=(0, 15))
        
        # 视角控制按钮框架
        view_frame = ttk.Frame(self.tab_3d)
        view_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(view_frame, text="📐 正视视角", command=self.view_front).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(view_frame, text="📥 俯视视角", command=self.view_top).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(view_frame, text="📋 侧视视角", command=self.view_side).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(view_frame, text="🔄 刷新 3D 视图", command=self.draw_3d).pack(side=tk.LEFT, padx=(0, 10))
        
        frame = ttk.Frame(self.tab_3d)
        frame.pack(fill=tk.BOTH, expand=True)
        self.fig_3d = plt.figure(figsize=(12,8), facecolor='#ffffff')
        self.ax_3d = self.fig_3d.add_subplot(111, projection='3d')
        self.canvas_3d = FigureCanvasTkAgg(self.fig_3d, master=frame)
        self.canvas_3d.get_tk_widget().pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 绑定鼠标点击和滚轮缩放事件
        self.fig_3d.canvas.mpl_connect('button_press_event', self.on_3d_click)
        self.fig_3d.canvas.mpl_connect('scroll_event', self.on_3d_scroll)

    def on_3d_scroll(self, event):
        s = 1.1 if event.button=='up' else 0.9
        self.ax_3d.set_xlim(np.array(self.ax_3d.get_xlim())*s)
        self.ax_3d.set_ylim(np.array(self.ax_3d.get_ylim())*s)
        self.ax_3d.set_zlim(np.array(self.ax_3d.get_zlim())*s)
        self.canvas_3d.draw()

    # 【修改】正视视角 - 隐藏标签
    def view_front(self):
        self.ax_3d.view_init(elev=10, azim=-90)
        self.hide_point_labels()
        self.canvas_3d.draw()

    # 【核心修改】俯视视角 - 显示桩号/勘探孔号标签（原正视图逻辑移至此）
    def view_top(self):
        self.ax_3d.view_init(elev=90, azim=0)
        self.show_point_labels()
        self.canvas_3d.draw()

    # 【修改】侧视视角 - 隐藏标签
    def view_side(self):
        self.ax_3d.view_init(elev=10, azim=0)
        self.hide_point_labels()
        self.canvas_3d.draw()

    # 显示桩号和勘探孔号标签（逻辑完全不变，仅由俯视图触发）
    def show_point_labels(self):
        self.hide_point_labels()
        geo = self.predictor.geo_data
        pile = self.predictor.pile_data
        
        # 勘探孔号标签：黑色白框，最高土层上方显示
        for hid, g in geo.groupby("孔号"):
            x, y = g["X"].iloc[0], g["Y"].iloc[0]
            z = g["土层顶标高"].max() + 0.5
            label = self.ax_3d.text(x, y, z, hid, fontsize=8, ha='center', va='bottom', 
                                   color='black', fontweight='bold', bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.7))
            self.point_labels[f"geo_{hid}"] = label
        
        # 桩号标签：红色黄框，桩顶上方显示，高亮突出
        for _, p in pile.iterrows():
            no = str(p["桩号"])
            x, y = p["X"], p["Y"]
            z = self.pile_original_predicts[no]["桩顶标高"] + 0.5 if no in self.pile_original_predicts else self.predictor.user_pile_top_elev + 0.5
            label = self.ax_3d.text(x, y, z, no, fontsize=9, ha='center', va='bottom', 
                                   color='red', fontweight='bold', bbox=dict(boxstyle="round,pad=0.3", fc="yellow", ec="red", alpha=0.8))
            self.point_labels[f"pile_{no}"] = label

    # 隐藏所有点标签（逻辑完全不变）
    def hide_point_labels(self):
        for label in self.point_labels.values():
            label.remove()
        self.point_labels.clear()

    # 3D鼠标点击显示详细信息（逻辑完全不变）
    def on_3d_click(self, event):
        if event.inaxes != self.ax_3d:
            return
        x_click = event.xdata
        y_click = event.ydata
        if x_click is None or y_click is None:
            return
        
        # 清除原有提示框
        if self.annotation_3d:
            self.annotation_3d.remove()
            self.annotation_3d = None
        
        # 查找最近的勘探孔/桩基
        min_dist = float('inf')
        closest_type = None
        closest_id = None
        closest_info = ""
        
        # 检查勘探孔
        geo = self.predictor.geo_data
        for hid, g in geo.groupby("孔号"):
            x, y = g["X"].iloc[0], g["Y"].iloc[0]
            dist = np.sqrt((x - x_click)**2 + (y - y_click)**2)
            if dist < min_dist and dist < 2:
                min_dist = dist
                closest_type = "勘探孔"
                closest_id = hid
                layers_info = []
                for _, r in g.sort_values("土层顶标高", ascending=False).iterrows():
                    layers_info.append(f"{r['土层名称']}: 顶{r['土层顶标高']:.2f}m 底{r['土层底标高']:.2f}m")
                closest_info = f"勘探孔：{hid}\n坐标：X={x:.2f} Y={y:.2f}\n土层信息：\n" + "\n".join(layers_info[:3])
        
        # 检查桩基
        if min_dist > 1:
            pile = self.predictor.pile_data
            for _, p in pile.iterrows():
                no = str(p["桩号"])
                x, y = p["X"], p["Y"]
                dist = np.sqrt((x - x_click)**2 + (y - y_click)**2)
                if dist < min_dist and dist < 2:
                    min_dist = dist
                    closest_type = "桩基"
                    closest_id = no
                    if no in self.pile_original_predicts:
                        res = self.pile_original_predicts[no]
                        support_elev = res.get("持力层顶标高", "未知")
                        pile_length = res.get("桩顶标高", 0) - (support_elev - res.get("持力层进入深度(m)", 0)) if support_elev != "未知" else "未知"
                        closest_info = f"桩基：{no}\n坐标：X={x:.2f} Y={y:.2f}\n桩径：{p['桩径']}mm 桩型：{p.get('桩型', '未知')}\n桩顶标高：{res.get('桩顶标高', 0):.2f}m\n持力层顶标高：{support_elev}\n设计桩长：{pile_length:.2f}m" if pile_length != "未知" else f"桩基：{no}\n坐标：X={x:.2f} Y={y:.2f}\n桩径：{p['桩径']}mm 桩型：{p.get('桩型', '未知')}\n桩顶标高：{res.get('桩顶标高', 0):.2f}m\n持力层未指定"
                    else:
                        closest_info = f"桩基：{no}\n坐标：X={x:.2f} Y={y:.2f}\n桩径：{p['桩径']}mm\n未预测数据"
        
        # 显示信息提示框
        if closest_id:
            self.annotation_3d = self.ax_3d.annotate(
                closest_info,
                xy=(x_click, y_click),
                xytext=(x_click+2, y_click+2),
                bbox=dict(boxstyle="round,pad=0.5", fc="white", ec="blue", alpha=0.9),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.1", color="blue"),
                fontsize=9,
                ha="left",
                va="bottom"
            )
            self.canvas_3d.draw()

    # 3D绘图（仅修改标签触发判断，其余完全不变：勘探孔细线lw=1、同土层同色）
    def draw_3d(self):
        self.ax_3d.clear()
        geo = self.predictor.geo_data
        pile = self.predictor.pile_data
        if geo.empty or pile.empty:
            self.ax_3d.text2D(0.5,0.5,"请先加载地勘与桩基数据",transform=self.ax_3d.transAxes,ha="center",fontsize=12)
            self.canvas_3d.draw()
            return

        layers = self.predictor.get_layer_list()
        colors = list(mcolors.TABLEAU_COLORS.values())
        layer_color = {layers[i]:colors[i%len(colors)] for i in range(len(layers))}

        # 勘探孔：线条变细lw=1，同土层同色，与桩基明显区别
        for hid, g in geo.groupby("孔号"):
            g = g.sort_values("土层顶标高", ascending=False)
            x, y = g["X"].iloc[0], g["Y"].iloc[0]
            for _, r in g.iterrows():
                c = layer_color[r["土层名称"]]
                self.ax_3d.plot([x,x],[y,y],[r["土层顶标高"],r["土层底标高"]], color=c, lw=1, alpha=0.8)

        # 桩基：彩色圆柱面渲染，同土层同色
        for _, p in pile.iterrows():
            no = str(p["桩号"])
            x, y, r = p["X"], p["Y"], p["桩径"]/2000
            if no not in self.pile_original_predicts:
                res,_ = self.predictor.predict_pile_layers(no)
                self.pile_original_predicts[no] = res
            else:
                res = self.pile_original_predicts[no]
            
            current_z = res["桩顶标高"]
            for lay in res["土层排序"]:
                if lay not in layer_color: continue
                z = res["土层预测"][lay]
                c = layer_color[lay]
                theta = np.linspace(0, 2*np.pi, 30)
                X = x + r*np.cos(theta)
                Y = y + r*np.sin(theta)
                self.ax_3d.plot_surface(np.array([X,X]), np.array([Y,Y]), np.array([np.full_like(theta,current_z), np.full_like(theta,z)]),
                                        color=c, alpha=0.7)
                current_z = z

        self.ax_3d.set_box_aspect([1,1,0.8])
        self.ax_3d.set_xlabel("X (m)")
        self.ax_3d.set_ylabel("Y (m)")
        self.ax_3d.set_zlabel("Z (m)")
        self.ax_3d.set_title("3D 地层视图｜勘探孔=分层细线｜桩基=彩色圆柱", fontsize=14)
        
        # 【核心修改】仅俯视图（仰角90°）自动显示标签，其余视角隐藏
        elev, azim = self.ax_3d.elev, self.ax_3d.azim
        if abs(elev - 90) < 5 and abs(azim - 0) < 5:
            self.show_point_labels()
        else:
            self.hide_point_labels()
        
        self.canvas_3d.draw()

    # ====================== 保存实测（完全不变） ======================
    def save_meas(self):
        if not self.current_pile_result:
            return
        pno = self.current_pile_result["桩号"]
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("提示","请选择土层")
            return
        lay = self.tree.item(sel[0])["values"][0]
        try:
            val = float(self.meas_val.get())
        except:
            messagebox.showerror("错误","请输入有效数值")
            return
        if pno not in self.measured_data:
            self.measured_data[pno] = {}
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.measured_data[pno][lay] = {"标高": val, "时间": now}
        if "开工时间" not in self.current_pile_result:
            self.current_pile_result["开工时间"] = now
        if lay == self.predictor.support_layer:
            try:
                real_d = float(self.real_support_depth.get())
                self.current_pile_result["实测持力层深度"] = real_d
            except:
                pass
        measured_dict = {l: self.measured_data[pno][l]["标高"] for l in self.measured_data[pno]}
        px = self.current_pile_result["X坐标"]
        py = self.current_pile_result["Y坐标"]
        self.predictor.add_measured_pile_as_geo_hole(px, py, measured_dict, pno)
        self.on_pile_select()
        self.check_support_layer_warning(pno, lay, round(val - self.current_pile_result["土层预测"][lay], 2))

    def check_support_layer_warning(self, pile_no, layer, error):
        if layer != self.predictor.support_layer:
            return
        w = self.predictor.warning_threshold
        a = self.predictor.alarm_threshold
        ae = abs(error)
        if ae >= a:
            messagebox.showerror("报警",f"持力层误差超标：{error:.2f}m\n阈值：{a}m")
        elif ae >= w:
            messagebox.showwarning("预警",f"持力层误差超限：{error:.2f}m\n阈值：{w}m")

    # ====================== 打桩记录（完全不变） ======================
    def init_record_tab(self):
        ttk.Label(self.tab_record, text="单桩打桩记录（自动生成/盖章格式）", font=('微软雅黑', 16, 'bold'), foreground='#2c3e50').pack(pady=(0, 15))
        self.record_text = tk.Text(self.tab_record, font=("宋体", 12), wrap=tk.WORD, bg="#ffffff", relief=tk.SUNKEN, padx=10, pady=10)
        self.record_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        ttk.Button(self.tab_record, text="📥 导出打桩记录文件", command=self.export_record).pack()

    def auto_generate_record(self):
        if not self.current_pile_result:return
        res = self.current_pile_result
        pno = res["桩号"]
        pile_top = res["桩顶标高"]
        pred_sup_elev = res.get("持力层顶标高",0)
        design_sup_depth = res.get("持力层进入深度(m)",0)
        real_sup_depth = res.get("实测持力层深度",0.0)
        real_sup_elev = self.measured_data.get(pno,{}).get(self.predictor.support_layer,{}).get("标高",pred_sup_elev)
        design_length = round(pile_top - pred_sup_elev + design_sup_depth,2)
        real_length = round(pile_top - real_sup_elev + real_sup_depth,2)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        txt = "="*70 + "\n                      桩基施工打桩记录\n" + "="*70 + "\n\n"
        txt += f"工程名称：____________________    桩  号：{pno}\n"
        txt += f"桩顶标高：{pile_top} m    桩  径：{res['桩径(mm)']} mm    桩  型：{res['桩型']}\n"
        txt += f"开工时间：{res.get('开工时间','未录入')}    记录时间：{now}\n\n"
        txt += "---------------- 各土层实测标高 ----------------\n"
        for lay in res["土层排序"]:
            d = self.measured_data.get(pno,{}).get(lay,{"标高":"未实测","时间":""})
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
        txt += "="*70 + "\n"
        self.record_text.delete(1.0,tk.END)
        self.record_text.insert(1.0,txt)

    def export_record(self):
        t = self.record_text.get(1.0,tk.END)
        if not t.strip():messagebox.showwarning("提示","无记录");return
        p = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("文本文件","*.txt")])
        if p:
            with open(p,"w",encoding="utf-8")as f:f.write(t)
            messagebox.showinfo("成功","打桩记录（盖章版）已导出")

    # ====================== 施工日志（完全不变） ======================
    def init_log_tab(self):
        ttk.Label(self.tab_log, text="施工日志", font=('微软雅黑', 16, 'bold'), foreground='#2c3e50').pack(pady=(0, 15))
        f=ttk.Frame(self.tab_log)
        f.pack(pady=(0, 10))
        ttk.Button(f, text="📝 生成当日日志", command=self.gen_log).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(f, text="📥 导出日志", command=self.export_log).pack(side=tk.LEFT)
        self.log_text=tk.Text(self.tab_log, font=('微软雅黑', 11), wrap=tk.WORD, bg="#ffffff", relief=tk.SUNKEN, padx=10, pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def gen_log(self):
        today = datetime.date.today().strftime("%Y-%m-%d")
        total=len(self.predictor.get_pile_list())
        done=len(self.measured_data)
        log=f"施工日志 {today}\n\n总桩数：{total}\n已实测：{done}\n已浇筑：{done}\n\n备注：________________________"
        self.log_text.delete(1.0,tk.END)
        self.log_text.insert(1.0,log)

    def export_log(self):
        t=self.log_text.get(1.0,tk.END)
        if not t.strip():messagebox.showwarning("提示","无日志");return
        p=filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("文本文件","*.txt")])
        if p:
            with open(p,"w",encoding="utf-8")as f:f.write(t)
            messagebox.showinfo("成功","施工日志已导出")

    # ====================== 承载力预测标签页 ======================
    def init_bearing_tab(self):
        ttk.Label(self.tab_bearing, text="单桩竖向承载力预测", font=('微软雅黑', 16, 'bold'), foreground='#2c3e50').pack(pady=(0, 10))

        # 上半部分：参数设置
        param_frame = ttk.LabelFrame(self.tab_bearing, text="岩土参数设置", padding=12)
        param_frame.pack(fill=tk.X, pady=(0, 10))

        # 参数输入表格
        table_frame = ttk.Frame(param_frame)
        table_frame.pack(fill=tk.X, pady=(0, 8))

        # 表头
        for j, t in enumerate(["土层名称", "侧摩阻力qsik (kPa)", "端阻力qpk (kPa)", "说明"]):
            ttk.Label(table_frame, text=t, font=('微软雅黑', 10, 'bold'),
                      foreground='#2980b9', width=25 if j < 3 else 15).grid(row=0, column=j, padx=5, pady=2, sticky='w')

        self.friction_widgets = {}  # {土层名称: (qsik_entry, qpk_entry)}
        self.bearing_param_frame = ttk.Frame(param_frame)
        self.bearing_param_frame.pack(fill=tk.X)

        # 承载参数输入容器（放在一个可滚动的框架里）
        self.bearing_canvas = tk.Canvas(self.bearing_param_frame, height=200, bg='#f8f9fa')
        scrollbar = ttk.Scrollbar(self.bearing_param_frame, orient='vertical', command=self.bearing_canvas.yview)
        self.bearing_scroll_frame = ttk.Frame(self.bearing_canvas)
        self.bearing_scroll_frame.bind('<Configure>', lambda e: self.bearing_canvas.configure(scrollregion=self.bearing_canvas.bbox('all')))
        self.bearing_canvas.create_window((0, 0), window=self.bearing_scroll_frame, anchor='nw')
        self.bearing_canvas.configure(yscrollcommand=scrollbar.set)
        self.bearing_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        ttk.Button(param_frame, text="🔄 加载土层参数表格", command=self.load_layer_params).pack(pady=(5, 0))

        # 安全系数
        safe_frame = ttk.Frame(param_frame)
        safe_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(safe_frame, text="安全系数 K：").pack(side=tk.LEFT, padx=(0, 5))
        self.safety_var = tk.DoubleVar(value=self.predictor.safety_factor)
        ttk.Entry(safe_frame, textvariable=self.safety_var, width=8).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(safe_frame, text="✅ 保存参数", command=self.save_bearing_params).pack(side=tk.LEFT, padx=(0, 15))

        # 第2行：操作按钮
        btn_frame = ttk.LabelFrame(self.tab_bearing, text="计算操作", padding=12)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        btn_row = ttk.Frame(btn_frame)
        btn_row.pack(fill=tk.X)
        ttk.Label(btn_row, text="桩号：").pack(side=tk.LEFT, padx=(0, 5))
        self.bearing_pile_var = tk.StringVar()
        self.bearing_pile_cb = ttk.Combobox(btn_row, textvariable=self.bearing_pile_var, width=15)
        self.bearing_pile_cb.pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(btn_row, text="🔩 单桩承载力计算", command=self.calc_single_bearing).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(btn_row, text="📊 批量计算所有桩", command=self.calc_all_bearing).pack(side=tk.LEFT, padx=(0, 15))
        ttk.Button(btn_row, text="📥 导出承载力Excel", command=self.export_bearing_excel).pack(side=tk.LEFT)

        # 第3行：结果显示
        result_frame = ttk.LabelFrame(self.tab_bearing, text="计算结果", padding=12)
        result_frame.pack(fill=tk.BOTH, expand=True)

        # 结果显示树形表格
        self.bearing_tree = ttk.Treeview(result_frame,
            columns=("桩号", "桩径(m)", "侧阻力Qsk(kN)", "端阻力Qpk(kN)", "极限Quk(kN)", "安全系数K", "特征值Ra(kN)"),
            show="headings", height=10)
        for c, w in [("桩号", 100), ("桩径(m)", 80), ("侧阻力Qsk(kN)", 120),
                      ("端阻力Qpk(kN)", 120), ("极限Quk(kN)", 110), ("安全系数K", 80), ("特征值Ra(kN)", 110)]:
            self.bearing_tree.heading(c, text=c)
            self.bearing_tree.column(c, width=w, anchor=tk.CENTER)
        self.bearing_tree.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # 点击行显示详情
        self.bearing_tree.bind("<<TreeviewSelect>>", self.show_bearing_detail)

        # 状态栏
        self.bearing_status = tk.StringVar(value="请先加载地勘和桩基数据，然后设置岩土参数")
        ttk.Label(self.tab_bearing, textvariable=self.bearing_status, relief=tk.SUNKEN,
                  anchor=tk.W, padding=8, font=('微软雅黑', 9)).pack(fill=tk.X, pady=(5, 0))

        # 初始化下拉框
        self.refresh_bearing_combobox()

    def refresh_bearing_combobox(self):
        piles = self.predictor.get_pile_list()
        self.bearing_pile_cb.config(values=piles)
        if piles:
            self.bearing_pile_cb.set(piles[0])

    def load_layer_params(self):
        """加载土层列表，生成参数输入行"""
        layers = self.predictor.get_layer_list()
        if not layers:
            messagebox.showwarning("提示", "请先加载地勘数据")
            return

        # 清空旧控件
        for w in self.bearing_scroll_frame.winfo_children():
            w.destroy()
        self.friction_widgets.clear()

        for i, layer in enumerate(layers):
            row = ttk.Frame(self.bearing_scroll_frame)
            row.pack(fill=tk.X, pady=1)

            ttk.Label(row, text=layer, width=25, anchor='w').pack(side=tk.LEFT, padx=(5, 5))

            qsik_var = tk.DoubleVar(value=self.predictor.layer_friction.get(layer, 0))
            qsik_entry = ttk.Entry(row, textvariable=qsik_var, width=12)
            qsik_entry.pack(side=tk.LEFT, padx=(5, 15))

            qpk_var = tk.DoubleVar(value=self.predictor.end_resistance.get(layer, 0))
            qpk_entry = ttk.Entry(row, textvariable=qpk_var, width=12)
            qpk_entry.pack(side=tk.LEFT, padx=(5, 15))

            # 标记是否为持力层
            is_support = "☆ 持力层" if layer == self.predictor.support_layer else ""
            ttk.Label(row, text=is_support, width=15, foreground='#e67e22').pack(side=tk.LEFT, padx=(5, 5))

            self.friction_widgets[layer] = (qsik_var, qpk_var)

        self.bearing_status.set(f"已加载 {len(layers)} 个土层参数输入行，请填写并保存")
        messagebox.showinfo("提示", f"已加载{len(layers)}个土层，请填写侧摩阻力qsik和端阻力qpk，然后点击'保存参数'")

    def save_bearing_params(self):
        """保存岩土参数"""
        self.predictor.safety_factor = self.safety_var.get()
        for layer, (qsik_var, qpk_var) in self.friction_widgets.items():
            qsik = qsik_var.get()
            if qsik > 0:
                self.predictor.layer_friction[layer] = qsik
            qpk = qpk_var.get()
            if qpk > 0:
                self.predictor.end_resistance[layer] = qpk
        self.bearing_status.set("✅ 岩土参数已保存，安全系数 K = {:.1f}".format(self.predictor.safety_factor))
        messagebox.showinfo("成功", "岩土参数已保存！")

    def calc_single_bearing(self):
        """计算单桩承载力"""
        pile_no = self.bearing_pile_var.get()
        if not pile_no:
            messagebox.showwarning("提示", "请选择桩号")
            return
        result, msg = self.predictor.calculate_pile_bearing_capacity(pile_no)
        if result is None:
            messagebox.showerror("错误", msg)
            return

        # 更新树形表格（先清空格，再显示）
        self.bearing_tree.delete(*self.bearing_tree.get_children())
        self.bearing_tree.insert("", "end", values=(
            result["桩号"], result["桩径(m)"], result["侧摩阻力Qsk(kN)"],
            result["端阻力Qpk(kN)"], result["极限承载力Quk(kN)"],
            result["安全系数K"], result["承载力特征值Ra(kN)"]
        ))
        self.bearing_status.set(f"✅ {pile_no} 承载力计算完成！特征值 Ra = {result['承载力特征值Ra(kN)']} kN")

        # 显示详情弹窗
        detail = (
            f"═══ {pile_no} 承载力计算详情 ═══\n\n"
            f"桩径 d = {result['桩径(m)']} m\n"
            f"桩周长 u = {result['桩周长u(m)']} m\n"
            f"桩端面积 Ap = {result['桩端面积Ap(m²)']} m²\n"
            f"安全系数 K = {result['安全系数K']}\n\n"
            f"各土层穿越厚度：\n"
        )
        for layer, thick in result["各土层穿越厚度(m)"].items():
            qsik = self.predictor.layer_friction.get(layer, 0)
            detail += f"  {layer}: {thick} m  (qsik={qsik} kPa)\n"
        detail += f"\n总侧阻力 Qsk = {result['侧摩阻力Qsk(kN)']} kN\n"
        detail += f"端阻力 Qpk = {result['端阻力Qpk(kN)']} kN\n"
        detail += f"极限承载力 Quk = {result['极限承载力Quk(kN)']} kN\n"
        detail += f"\n▶ 承载力特征值 Ra = {result['承载力特征值Ra(kN)']} kN ◀"

        if result["缺失参数土层"]:
            detail += f"\n\n⚠️ 提示：以下土层未设置侧摩阻力(按0计算)：{', '.join(result['缺失参数土层'])}"

        messagebox.showinfo("承载力计算结果", detail)

    def calc_all_bearing(self):
        """批量计算所有桩承载力"""
        results, warnings = self.predictor.calculate_all_bearing_capacity()
        if not results:
            messagebox.showwarning("提示", "没有计算结果，请先加载数据")
            return

        self.bearing_tree.delete(*self.bearing_tree.get_children())
        for r in results:
            self.bearing_tree.insert("", "end", values=(
                r["桩号"], r["桩径(m)"], r["侧摩阻力Qsk(kN)"],
                r["端阻力Qpk(kN)"], r["极限承载力Quk(kN)"],
                r["安全系数K"], r["承载力特征值Ra(kN)"]
            ))

        # 统计信息
        ras = [r["承载力特征值Ra(kN)"] for r in results]
        status = f"✅ 共计算 {len(results)} 根桩 | Ra范围: {min(ras):.1f} ~ {max(ras):.1f} kN"
        if warnings:
            status += f" | ⚠️ {len(warnings)} 条警告"
        self.bearing_status.set(status)

        # 提醒缺失参数
        missing = set()
        for r in results:
            for m in r["缺失参数土层"]:
                missing.add(m)
        if missing:
            msg = f"批量计算完成！\n共{len(results)}根桩\n\n⚠️ 提示：以下土层未设置侧摩阻力(按0计算)：\n{', '.join(missing)}\n\n建议去参数设置中填写完整参数以提高计算精度。"
            messagebox.showinfo("批量计算结果", msg)
        else:
            msg = f"批量计算完成！\n共{len(results)}根桩\n\nRa范围: {min(ras):.1f} ~ {max(ras):.1f} kN\n平均Ra: {sum(ras)/len(ras):.1f} kN"
            messagebox.showinfo("批量计算结果", msg)

    def show_bearing_detail(self, event):
        """点击结果行显示详细计算信息"""
        sel = self.bearing_tree.selection()
        if not sel:
            return
        item = self.bearing_tree.item(sel[0])
        pile_no = item["values"][0]

        result, msg = self.predictor.calculate_pile_bearing_capacity(pile_no)
        if result is None:
            return

        detail = (
            f"═══ {pile_no} 承载力计算详情 ═══\n\n"
            f"桩径 d = {result['桩径(m)']} m\n"
            f"桩周长 u = {result['桩周长u(m)']} m\n"
            f"桩端面积 Ap = {result['桩端面积Ap(m²)']} m²\n"
            f"安全系数 K = {result['安全系数K']}\n\n"
            f"各土层穿越厚度：\n"
        )
        for layer, thick in result["各土层穿越厚度(m)"].items():
            qsik = self.predictor.layer_friction.get(layer, 0)
            qpk = self.predictor.end_resistance.get(layer, 0)
            end_mark = f" (qpk={qpk} kPa)" if qpk > 0 else ""
            detail += f"  {layer}: {thick} m, qsik={qsik} kPa{end_mark}\n"
        detail += f"\n总侧阻力 Qsk = {result['侧摩阻力Qsk(kN)']} kN"
        detail += f"\n端阻力 Qpk = {result['端阻力Qpk(kN)']} kN"
        detail += f"\n极限承载力 Quk = {result['极限承载力Quk(kN)']} kN"
        detail += f"\n\n▶ 承载力特征值 Ra = {result['承载力特征值Ra(kN)']} kN ◀"

        if result["缺失参数土层"]:
            detail += f"\n\n⚠️ 未设置侧摩阻力的土层：{', '.join(result['缺失参数土层'])}"

        messagebox.showinfo(f"{pile_no} 承载力详情", detail)

    def export_bearing_excel(self):
        """导出承载力结果到Excel"""
        items = self.bearing_tree.get_children()
        if not items:
            messagebox.showwarning("提示", "没有数据可导出，请先计算")
            return
        data = []
        for item in items:
            vals = self.bearing_tree.item(item)["values"]
            data.append({
                "桩号": vals[0], "桩径(m)": vals[1],
                "侧阻力Qsk(kN)": vals[2], "端阻力Qpk(kN)": vals[3],
                "极限承载力Quk(kN)": vals[4], "安全系数K": vals[5],
                "承载力特征值Ra(kN)": vals[6]
            })
        df = pd.DataFrame(data)
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel文件", "*.xlsx")])
        if path:
            df.to_excel(path, index=False)
            messagebox.showinfo("成功", f"承载力结果已导出！共{len(data)}根桩")

if __name__ == "__main__":

    root = tk.Tk()
    app = PilePredictionGUI(root)
    root.mainloop()
