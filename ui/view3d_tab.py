import tkinter as tk
from tkinter import ttk
import json
import os
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
            return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

        layers = self.engine.get_layer_list()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

        boreholes = []
        for hid, g in geo.groupby("孔号"):
            g = g.sort_values("土层顶标高", ascending=False)
            hole_layers = []
            for _, r in g.iterrows():
                color_idx = layers.index(r["土层名称"]) if r["土层名称"] in layers else 0
                hole_layers.append({
                    "name": str(r["土层名称"]),
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

        if not hasattr(self, '_cached_predicts'):
            self._cached_predicts = {}

        piles = []
        for _, p in pile.iterrows():
            pno = str(p["桩号"])
            if pno not in self._cached_predicts:
                self._cached_predicts[pno] = self.engine.predict_one(pno)
            res = self._cached_predicts[pno]
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

        html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "scene.html")

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
