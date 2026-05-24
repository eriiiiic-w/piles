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

        piles = []
        for _, p in pile_df.iterrows():
            piles.append({
                "id": str(p["桩号"]),
                "x": float(p["X"]),
                "y": float(p["Y"]),
                "diameter": float(p["桩径"]),
                "pile_type": str(p.get("桩型", "未知")),
                "top_elev": self.store.user_pile_top_elev,
                "bottom_elev": None
            })

        z_vals = geo['土层顶标高'].dropna()
        z_min = float(z_vals.min()) if len(z_vals) > 0 else -30
        z_max = float(z_vals.max()) if len(z_vals) > 0 else 5

        return json.dumps({
            "piles": piles,
            "support_layer": self.store.support_layer,
            "bounds": {
                "x": [float(geo["X"].min()), float(geo["X"].max())],
                "y": [float(geo["Y"].min()), float(geo["Y"].max())],
                "z": [z_min, z_max]
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
