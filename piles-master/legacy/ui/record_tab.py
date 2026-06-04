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
