import tkinter as tk
from tkinter import ttk
import json
import os
import tempfile
import webbrowser


class View3DTab:
    def __init__(self, parent, store, engine):
        self.store = store
        self.engine = engine
        self.frame = ttk.Frame(parent, padding=15)

        ttk.Label(self.frame, text="3D 桩基土层立体视图", font=('微软雅黑', 16, 'bold'), foreground='#2c3e55').pack(pady=(0, 15))

        btn_row = ttk.Frame(self.frame)
        btn_row.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(btn_row, text="启动 3D 视图", command=self._launch_3d).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(btn_row, text="刷新数据", command=self._refresh_data).pack(side=tk.LEFT, padx=(0, 10))

        self.status_var = tk.StringVar(value="点击「启动 3D 视图」在浏览器中打开")
        ttk.Label(self.frame, textvariable=self.status_var, foreground='#666').pack()

    def _get_scene_data(self):
        geo = self.store.geo_data
        pile_df = self.store.pile_data

        if geo.empty or pile_df.empty:
            return json.dumps({"error": "请先加载数据"}, ensure_ascii=False)

        layers = self.engine.get_layer_list()
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']

        layer_color = {layers[i]: colors[i % len(colors)] for i in range(len(layers))}
        layer_data_map = {}
        for layer in layers:
            ld = geo[geo['土层名称'] == layer]
            if len(ld) >= 2:
                layer_data_map[layer] = (ld['X'].values, ld['Y'].values, ld['土层顶标高'].values)
            else:
                layer_data_map[layer] = None

        boreholes = []
        all_z = []
        for hid, g in geo.groupby("孔号"):
            g = g.sort_values("土层顶标高", ascending=False)
            hole_layers = []
            for _, r in g.iterrows():
                c = layer_color.get(r["土层名称"], '#888888')
                top = float(r["土层顶标高"])
                bottom = float(r["土层底标高"])
                hole_layers.append({"name": str(r["土层名称"]), "top": top, "bottom": bottom, "color": c})
                all_z.extend([top, bottom])
            boreholes.append({"id": str(hid), "x": float(g["X"].iloc[0]), "y": float(g["Y"].iloc[0]), "layers": hole_layers})

        if not hasattr(self, '_cached_predicts'):
            self._cached_predicts = {}

        piles = []
        for _, p in pile_df.iterrows():
            pno = str(p["桩号"])
            px = float(p["X"])
            py = float(p["Y"])
            pd = float(p["桩径"])
            pt = str(p.get("桩型", "未知"))

            if pno not in self._cached_predicts:
                res = {"桩号": pno, "X坐标": px, "Y坐标": py, "桩径(mm)": pd, "桩型": pt,
                       "土层预测": {}, "土层底标高预测": {}, "土层排序": layers,
                       "桩顶标高": self.store.user_pile_top_elev}
                for layer in layers:
                    ldm = layer_data_map.get(layer)
                    if ldm is None:
                        ld = geo[geo['土层名称'] == layer]
                        z_pred = round(ld['土层顶标高'].mean(), 2) if not ld.empty else 10.0
                    else:
                        xv, yv, val = ldm
                        z_pred = round(float(self.engine.idw_interpolate(px, py, xv, yv, val)), 2)
                    res["土层预测"][layer] = z_pred
                for i, layer in enumerate(layers):
                    if i < len(layers) - 1:
                        res["土层底标高预测"][layer] = res["土层预测"][layers[i + 1]]
                    else:
                        avg_thick = geo[geo['土层名称'] == layer]['土层厚度'].mean()
                        res["土层底标高预测"][layer] = round(res["土层预测"][layer] - avg_thick, 2)
                sup_depth = self.engine.calc_support_depth(pd)
                if self.store.support_layer in res["土层预测"]:
                    res["持力层顶标高"] = res["土层预测"][self.store.support_layer]
                    res["持力层进入深度(m)"] = sup_depth
                self._cached_predicts[pno] = res
            else:
                res = self._cached_predicts[pno]

            pile_layers = []
            current_z = res["桩顶标高"]
            for lay in res["土层排序"]:
                z = res["土层预测"].get(lay, current_z)
                pile_layers.append({"name": lay, "top": float(current_z), "bottom": float(z),
                                    "color": layer_color.get(lay, '#888888')})
                current_z = z

            support_elev = res.get("持力层顶标高", None)
            piles.append({
                "id": pno, "x": px, "y": py, "diameter": pd, "pile_type": pt,
                "top_elev": float(res["桩顶标高"]),
                "support_elev": float(support_elev) if support_elev and support_elev != "未指定" else None,
                "support_depth": float(res.get("持力层进入深度(m)", 0)),
                "layers": pile_layers
            })

        if not all_z:
            all_z = [-30, 5]

        return json.dumps({
            "boreholes": boreholes, "piles": piles,
            "support_layer": self.store.support_layer,
            "bounds": {
                "x": [float(geo["X"].min()), float(geo["X"].max())],
                "y": [float(geo["Y"].min()), float(geo["Y"].max())],
                "z": [min(all_z), max(all_z)]
            }
        }, ensure_ascii=False)

    def _launch_3d(self):
        if self.store.geo_data.empty or self.store.pile_data.empty:
            self.status_var.set("请先加载地勘和桩基数据")
            return

        self.status_var.set("3D数据准备中...")
        self.frame.update_idletasks()

        html_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "scene.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        scene_data = self._get_scene_data()
        html_content = html_content.replace(
            "// DATA_PLACEHOLDER",
            f"const EMBEDDED_DATA = {scene_data};"
        )

        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False, encoding='utf-8')
        tmp.write(html_content)
        tmp.close()

        webbrowser.open('file:///' + tmp.name.replace('\\', '/'))
        self.status_var.set("3D视图已在浏览器中打开 — 旋转:鼠标左键拖拽 | 缩放:滚轮 | 平移:鼠标右键拖拽")

    def _refresh_data(self):
        if hasattr(self, '_cached_predicts'):
            del self._cached_predicts
        self.status_var.set("数据已刷新，请重新点击「启动 3D 视图」")
