import numpy as np
import pandas as pd
from pykrige import OrdinaryKriging


def idw_interpolate(x, y, xv, yv, val):
    distances = np.sqrt((xv - x)**2 + (yv - y)**2)
    if np.any(distances == 0):
        return float(val[np.argmin(distances)])
    weights = 1 / (distances ** 2)
    return float(np.sum(weights * val) / np.sum(weights))


def krige_interpolate(x, y, xv, yv, val):
    try:
        ok = OrdinaryKriging(xv, yv, val, variogram_model='spherical', enable_plotting=False)
        z, _ = ok.execute('points', np.array([x]), np.array([y]))
        return float(z[0])
    except Exception:
        return float(np.mean(val))


def predict_one(geo_df, pile_row, layer_list, interp_method, support_layer, support_depth_type, support_depth_val):
    """预测单桩各土层标高。geo_df: DataFrame with 孔号,X,Y,土层名称,土层顶标高,土层厚度,土层底标高. pile_row: dict with 桩号,X,Y,桩径,桩型. Returns dict."""
    pile_x = float(pile_row['X'])
    pile_y = float(pile_row['Y'])
    pile_diameter = float(pile_row['桩径'])
    pile_type = str(pile_row.get('桩型', '未知'))
    pile_no = str(pile_row['桩号'])

    result = {
        "桩号": pile_no,
        "X坐标": pile_x, "Y坐标": pile_y,
        "桩径(mm)": pile_diameter, "桩型": pile_type,
        "土层预测": {}, "土层底标高预测": {},
        "土层排序": list(layer_list),
    }

    interp_fn = krige_interpolate if interp_method == "克里金法" else idw_interpolate

    for layer in layer_list:
        layer_data = geo_df[geo_df['土层名称'] == layer]
        if len(layer_data) < 2:
            z_pred = round(float(layer_data['土层顶标高'].mean()) if not layer_data.empty else 10.0, 2)
        else:
            z_pred = round(interp_fn(pile_x, pile_y,
                layer_data['X'].values, layer_data['Y'].values,
                layer_data['土层顶标高'].values), 2)
        result["土层预测"][layer] = z_pred

    for i, layer in enumerate(layer_list):
        if i < len(layer_list) - 1:
            result["土层底标高预测"][layer] = result["土层预测"][layer_list[i + 1]]
        else:
            avg_thick = geo_df[geo_df['土层名称'] == layer]['土层厚度'].mean()
            result["土层底标高预测"][layer] = round(result["土层预测"][layer] - float(avg_thick), 2)

    support_depth = (support_depth_val * (pile_diameter / 1000)
                     if support_depth_type == "n倍桩径"
                     else support_depth_val)
    if support_layer in result["土层预测"]:
        result["持力层顶标高"] = result["土层预测"][support_layer]
        result["持力层进入深度(m)"] = round(support_depth, 2)

    return result


def predict_one_fast(geo_df, pile_row, layer_list, support_layer, support_depth_type, support_depth_val):
    """IDW快速预测，供3D场景使用。强制使用IDW。"""
    pile_x = float(pile_row['X'])
    pile_y = float(pile_row['Y'])
    pile_diameter = float(pile_row['桩径'])
    pile_type = str(pile_row.get('桩型', '未知'))
    pile_no = str(pile_row['桩号'])

    result = {
        "桩号": pile_no,
        "X坐标": pile_x, "Y坐标": pile_y,
        "桩径(mm)": pile_diameter, "桩型": pile_type,
        "土层预测": {}, "土层底标高预测": {},
        "土层排序": list(layer_list),
    }

    for layer in layer_list:
        layer_data = geo_df[geo_df['土层名称'] == layer]
        if len(layer_data) < 2:
            z_pred = round(float(layer_data['土层顶标高'].mean()) if not layer_data.empty else 10.0, 2)
        else:
            z_pred = round(idw_interpolate(pile_x, pile_y,
                layer_data['X'].values, layer_data['Y'].values,
                layer_data['土层顶标高'].values), 2)
        result["土层预测"][layer] = z_pred

    for i, layer in enumerate(layer_list):
        if i < len(layer_list) - 1:
            result["土层底标高预测"][layer] = result["土层预测"][layer_list[i + 1]]
        else:
            avg_thick = geo_df[geo_df['土层名称'] == layer]['土层厚度'].mean()
            result["土层底标高预测"][layer] = round(result["土层预测"][layer] - float(avg_thick), 2)

    support_depth = (support_depth_val * (pile_diameter / 1000)
                     if support_depth_type == "n倍桩径"
                     else support_depth_val)
    if support_layer in result["土层预测"]:
        result["持力层顶标高"] = result["土层预测"][support_layer]
        result["持力层进入深度(m)"] = round(support_depth, 2)

    return result


def get_layer_list(geo_df):
    if geo_df.empty:
        return []
    avg_elev = geo_df.groupby('土层名称')['土层顶标高'].mean().sort_values(ascending=False)
    return list(avg_elev.index)
