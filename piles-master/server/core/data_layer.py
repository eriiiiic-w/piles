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
