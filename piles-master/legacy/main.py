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
