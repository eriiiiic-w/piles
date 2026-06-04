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


def predict_one(geo_df, pile_row, layer_list, interp_method, support_layer, support_depth_type, support_depth_val, layer_groups=None):
    pile_x = float(pile_row['X'])
    pile_y = float(pile_row['Y'])
    pile_diameter = float(pile_row['桩径'])
    pile_type = str(pile_row.get('桩型', '未知'))
    pile_no = str(pile_row['桩号'])

    result = {
        "桩号": pile_no,
        "X坐标": pile_x, "Y坐标": pile_y,
        "桩径": pile_diameter, "桩型": pile_type,
        "土层预测": {}, "土层底标高预测": {},
        "土层排序": list(layer_list),
    }

    interp_fn = krige_interpolate if interp_method == "克里金法" else idw_interpolate

    for layer in layer_list:
        layer_data = layer_groups.get(layer) if layer_groups else geo_df[geo_df['土层名称'] == layer]
        if layer_data is None or len(layer_data) < 2:
            z_pred = round(float(layer_data['土层顶标高'].mean()) if (layer_data is not None and not layer_data.empty) else 10.0, 2)
        else:
            z_pred = round(interp_fn(pile_x, pile_y,
                layer_data['X'].values, layer_data['Y'].values,
                layer_data['土层顶标高'].values), 2)
        result["土层预测"][layer] = z_pred

    for i, layer in enumerate(layer_list):
        if i < len(layer_list) - 1:
            result["土层底标高预测"][layer] = result["土层预测"][layer_list[i + 1]]
        else:
            layer_data = layer_groups.get(layer) if layer_groups else geo_df[geo_df['土层名称'] == layer]
            avg_thick = layer_data['土层厚度'].mean() if (layer_data is not None and not layer_data.empty) else 2.0
            result["土层底标高预测"][layer] = round(result["土层预测"][layer] - float(avg_thick), 2)

    support_depth = (support_depth_val * (pile_diameter / 1000)
                     if support_depth_type == "n倍桩径"
                     else support_depth_val)
    if support_layer in result["土层预测"]:
        result["持力层顶标高"] = result["土层预测"][support_layer]
        result["持力层进入深度"] = round(support_depth, 2)

    return result


def predict_one_fast(geo_df, pile_row, layer_list, support_layer, support_depth_type, support_depth_val, layer_groups=None):
    pile_x = float(pile_row['X'])
    pile_y = float(pile_row['Y'])
    pile_diameter = float(pile_row['桩径'])
    pile_type = str(pile_row.get('桩型', '未知'))
    pile_no = str(pile_row['桩号'])

    result = {
        "桩号": pile_no,
        "X坐标": pile_x, "Y坐标": pile_y,
        "桩径": pile_diameter, "桩型": pile_type,
        "土层预测": {}, "土层底标高预测": {},
        "土层排序": list(layer_list),
    }

    for layer in layer_list:
        layer_data = layer_groups.get(layer) if layer_groups else geo_df[geo_df['土层名称'] == layer]
        if layer_data is None or len(layer_data) < 2:
            z_pred = round(float(layer_data['土层顶标高'].mean()) if (layer_data is not None and not layer_data.empty) else 10.0, 2)
        else:
            z_pred = round(idw_interpolate(pile_x, pile_y,
                layer_data['X'].values, layer_data['Y'].values,
                layer_data['土层顶标高'].values), 2)
        result["土层预测"][layer] = z_pred

    for i, layer in enumerate(layer_list):
        if i < len(layer_list) - 1:
            result["土层底标高预测"][layer] = result["土层预测"][layer_list[i + 1]]
        else:
            layer_data = layer_groups.get(layer) if layer_groups else geo_df[geo_df['土层名称'] == layer]
            avg_thick = layer_data['土层厚度'].mean() if (layer_data is not None and not layer_data.empty) else 2.0
            result["土层底标高预测"][layer] = round(result["土层预测"][layer] - float(avg_thick), 2)

    support_depth = (support_depth_val * (pile_diameter / 1000)
                     if support_depth_type == "n倍桩径"
                     else support_depth_val)
    if support_layer in result["土层预测"]:
        result["持力层顶标高"] = result["土层预测"][support_layer]
        result["持力层进入深度"] = round(support_depth, 2)

    return result


def get_layer_list(geo_df):
    if geo_df.empty:
        return []
    avg_elev = geo_df.groupby('土层名称')['土层顶标高'].mean().sort_values(ascending=False)
    return list(avg_elev.index)


def predict_batch(geo_df, piles_df, layer_list, interp_method, support_layer, support_depth_type, support_depth_val):
    """批量预测全部桩位。每层构建一次Kriging模型，一次性预测全部桩位。"""
    pile_nos = piles_df['桩号'].values
    pile_xs = piles_df['X'].values.astype(float)
    pile_ys = piles_df['Y'].values.astype(float)
    pile_diams = piles_df['桩径'].values.astype(float)
    pile_types = piles_df['桩型'].values

    n_piles = len(pile_nos)
    results = {no: {
        "桩号": str(no), "X坐标": float(x), "Y坐标": float(y),
        "桩径": float(d), "桩型": str(t),
        "土层预测": {}, "土层底标高预测": {}, "土层排序": list(layer_list)
    } for no, x, y, d, t in zip(pile_nos, pile_xs, pile_ys, pile_diams, pile_types)}

    for layer in layer_list:
        layer_data = geo_df[geo_df['土层名称'] == layer]
        if len(layer_data) < 2:
            mean_z = round(float(layer_data['土层顶标高'].mean()) if not layer_data.empty else 10.0, 2)
            z_preds = np.full(n_piles, mean_z)
        elif interp_method == "克里金法":
            try:
                ok = OrdinaryKriging(
                    layer_data['X'].values, layer_data['Y'].values,
                    layer_data['土层顶标高'].values,
                    variogram_model='spherical', enable_plotting=False)
                z_preds, _ = ok.execute('points', pile_xs, pile_ys)
            except Exception:
                z_preds = np.full(n_piles, np.mean(layer_data['土层顶标高'].values))
        else:
            z_preds = np.array([
                idw_interpolate(px, py, layer_data['X'].values, layer_data['Y'].values, layer_data['土层顶标高'].values)
                for px, py in zip(pile_xs, pile_ys)
            ])

        for i, no in enumerate(pile_nos):
            results[no]["土层预测"][layer] = round(float(z_preds[i]), 2)

    for i, layer in enumerate(layer_list):
        layer_data = geo_df[geo_df['土层名称'] == layer]
        if i < len(layer_list) - 1:
            for no in pile_nos:
                results[no]["土层底标高预测"][layer] = results[no]["土层预测"][layer_list[i + 1]]
        else:
            avg_thick = float(layer_data['土层厚度'].mean()) if not layer_data.empty else 2.0
            for no in pile_nos:
                results[no]["土层底标高预测"][layer] = round(results[no]["土层预测"][layer] - avg_thick, 2)

    for no in pile_nos:
        d = results[no]["桩径"]
        support_depth = (support_depth_val * (d / 1000) if support_depth_type == "n倍桩径" else support_depth_val)
        if support_layer in results[no]["土层预测"]:
            results[no]["持力层顶标高"] = results[no]["土层预测"][support_layer]
            results[no]["持力层进入深度"] = round(support_depth, 2)

    return list(results.values())
