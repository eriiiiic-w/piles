import numpy as np
import pandas as pd
from pykrige import OrdinaryKriging


class PredictEngine:
    """克里金/IDW土层插值预测引擎"""

    def __init__(self, store):
        self.store = store

    def _get_geo(self):
        return self.store.geo_data

    def _get_pile(self):
        return self.store.pile_data

    def idw_interpolate(self, x, y, xv, yv, val):
        distances = np.sqrt((xv - x)**2 + (yv - y)**2)
        if np.any(distances == 0):
            return float(val[np.argmin(distances)])
        weights = 1 / (distances ** 2)
        return float(np.sum(weights * val) / np.sum(weights))

    def krige_interpolate(self, x, y, xv, yv, val):
        try:
            ok = OrdinaryKriging(xv, yv, val, variogram_model='spherical', enable_plotting=False)
            z, _ = ok.execute('points', np.array([x]), np.array([y]))
            return float(z[0])
        except Exception:
            return float(np.mean(val))

    def predict_one(self, pile_no):
        geo = self._get_geo()
        pile = self._get_pile()
        if geo.empty or pile.empty:
            return None

        pile_info = pile[pile['桩号'] == pile_no]
        if pile_info.empty:
            return None

        pile_x = pile_info['X'].values[0]
        pile_y = pile_info['Y'].values[0]
        pile_diameter = pile_info['桩径'].values[0]
        pile_type = pile_info['桩型'].values[0] if '桩型' in pile_info.columns else '未知'
        layer_list = self.get_layer_list()

        result = {
            "桩号": pile_no,
            "X坐标": pile_x, "Y坐标": pile_y,
            "桩径(mm)": pile_diameter, "桩型": pile_type,
            "土层预测": {}, "土层底标高预测": {},
            "土层排序": layer_list,
            "桩顶标高": self.store.user_pile_top_elev
        }

        for layer in layer_list:
            layer_data = geo[geo['土层名称'] == layer]
            if len(layer_data) < 2:
                z_pred = round(layer_data['土层顶标高'].mean() if not layer_data.empty else 10.0, 2)
            else:
                xv = layer_data['X'].values
                yv = layer_data['Y'].values
                val = layer_data['土层顶标高'].values
                if self.store.interp_method == "克里金法":
                    z_pred = round(self.krige_interpolate(pile_x, pile_y, xv, yv, val), 2)
                else:
                    z_pred = round(self.idw_interpolate(pile_x, pile_y, xv, yv, val), 2)
            result["土层预测"][layer] = z_pred

        for i, layer in enumerate(layer_list):
            if i < len(layer_list) - 1:
                result["土层底标高预测"][layer] = result["土层预测"][layer_list[i + 1]]
            else:
                avg_thick = geo[geo['土层名称'] == layer]['土层厚度'].mean()
                result["土层底标高预测"][layer] = round(result["土层预测"][layer] - avg_thick, 2)

        support_depth = self.calc_support_depth(pile_diameter)
        if self.store.support_layer in result["土层预测"]:
            result["持力层顶标高"] = result["土层预测"][self.store.support_layer]
            result["持力层进入深度(m)"] = support_depth

        return result

    def predict_all(self):
        geo = self._get_geo()
        pile = self._get_pile()
        if geo.empty or pile.empty:
            return None

        rows = []
        for pno in self.get_pile_list():
            res = self.predict_one(pno)
            if res:
                flat = {
                    "桩号": res["桩号"], "X": res["X坐标"], "Y": res["Y坐标"],
                    "桩径": res["桩径(mm)"], "桩型": res["桩型"],
                    "持力层顶标高": res.get("持力层顶标高", ""), "桩顶标高": res["桩顶标高"]
                }
                for k, v in res["土层预测"].items():
                    flat[f"{k}顶标高"] = v
                rows.append(flat)
        return pd.DataFrame(rows)

    def predict_one_fast(self, pile_no):
        """仅用IDW的快速预测，用于3D可视化场景数据生成"""
        geo = self._get_geo()
        pile = self._get_pile()
        if geo.empty or pile.empty:
            return None

        pile_info = pile[pile['桩号'] == pile_no]
        if pile_info.empty:
            return None

        pile_x = pile_info['X'].values[0]
        pile_y = pile_info['Y'].values[0]
        pile_diameter = pile_info['桩径'].values[0]
        pile_type = pile_info['桩型'].values[0] if '桩型' in pile_info.columns else '未知'
        layer_list = self.get_layer_list()

        result = {
            "桩号": pile_no,
            "X坐标": pile_x, "Y坐标": pile_y,
            "桩径(mm)": pile_diameter, "桩型": pile_type,
            "土层预测": {}, "土层底标高预测": {},
            "土层排序": layer_list,
            "桩顶标高": self.store.user_pile_top_elev
        }

        for layer in layer_list:
            layer_data = geo[geo['土层名称'] == layer]
            if len(layer_data) < 2:
                z_pred = round(layer_data['土层顶标高'].mean() if not layer_data.empty else 10.0, 2)
            else:
                z_pred = round(self.idw_interpolate(pile_x, pile_y,
                    layer_data['X'].values, layer_data['Y'].values,
                    layer_data['土层顶标高'].values), 2)
            result["土层预测"][layer] = z_pred

        for i, layer in enumerate(layer_list):
            if i < len(layer_list) - 1:
                result["土层底标高预测"][layer] = result["土层预测"][layer_list[i + 1]]
            else:
                avg_thick = geo[geo['土层名称'] == layer]['土层厚度'].mean()
                result["土层底标高预测"][layer] = round(result["土层预测"][layer] - avg_thick, 2)

        support_depth = self.calc_support_depth(pile_diameter)
        if self.store.support_layer in result["土层预测"]:
            result["持力层顶标高"] = result["土层预测"][self.store.support_layer]
            result["持力层进入深度(m)"] = support_depth

        return result

    def get_layer_list(self):
        return self.store.get_layer_list()

    def get_pile_list(self):
        return self.store.get_pile_list()

    def calc_support_depth(self, pile_diameter_mm):
        if self.store.support_depth_type == "n倍桩径":
            return self.store.support_depth * (pile_diameter_mm / 1000)
        return self.store.support_depth
