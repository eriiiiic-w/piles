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
