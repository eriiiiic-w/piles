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
