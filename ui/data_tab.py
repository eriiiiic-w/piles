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
