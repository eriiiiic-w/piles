import datetime
from sqlalchemy.orm import Session
from server.core.prediction import predict_one as do_predict, predict_one_fast as do_predict_fast
from server.core.prediction import get_layer_list as core_get_layer_list
from server.core.prediction import predict_batch
from server.models.prediction import Prediction
from server.models.pile import Pile
from server.services.geo_service import get_geo_as_dataframe, get_layer_names
from server.services.settings_service import get_all_settings


def predict_single(db: Session, pile_no: str) -> dict | None:
    pile = db.query(Pile).filter(Pile.pile_no == pile_no).first()
    if not pile:
        return None
    geo_df = get_geo_as_dataframe(db)
    if geo_df.empty:
        return None
    s = get_all_settings(db)
    layer_list = get_layer_names(db)
    layer_groups = {layer: geo_df[geo_df['土层名称'] == layer] for layer in layer_list}
    pile_row = {"桩号": pile.pile_no, "X": pile.x, "Y": pile.y, "桩径": pile.diameter, "桩型": pile.pile_type}
    result = do_predict(geo_df, pile_row, layer_list,
                        s["interp_method"], s["support_layer"],
                        s["support_depth_type"], float(s["support_depth"]),
                        layer_groups=layer_groups)
    result["桩顶标高"] = float(s.get("pile_top_elev", 0.5))
    return result


def predict_single_fast(db: Session, pile_no: str) -> dict | None:
    pile = db.query(Pile).filter(Pile.pile_no == pile_no).first()
    if not pile:
        return None
    geo_df = get_geo_as_dataframe(db)
    if geo_df.empty:
        return None
    s = get_all_settings(db)
    layer_list = get_layer_names(db)
    layer_groups = {layer: geo_df[geo_df['土层名称'] == layer] for layer in layer_list}
    pile_row = {"桩号": pile.pile_no, "X": pile.x, "Y": pile.y, "桩径": pile.diameter, "桩型": pile.pile_type}
    result = do_predict_fast(geo_df, pile_row, layer_list,
                             s["support_layer"],
                             s["support_depth_type"], float(s["support_depth"]),
                             layer_groups=layer_groups)
    result["桩顶标高"] = float(s.get("pile_top_elev", 0.5))
    return result


def cache_prediction(db: Session, result: dict, method: str):
    now = datetime.datetime.now().isoformat()
    pile_no = result["桩号"]
    for layer_name in result["土层排序"]:
        db.query(Prediction).filter(
            Prediction.pile_no == pile_no,
            Prediction.layer_name == layer_name
        ).delete()
        db.add(Prediction(
            pile_no=pile_no,
            layer_name=layer_name,
            top_elev_pred=result["土层预测"].get(layer_name),
            bottom_elev_pred=result["土层底标高预测"].get(layer_name),
            method=method,
            created_at=now,
        ))
    db.commit()


def cache_predictions_bulk(db: Session, results: list[dict], method: str):
    """批量写入预测缓存 — 单事务，避免逐桩commit导致的SQLite锁竞争"""
    now = datetime.datetime.now().isoformat()
    pile_nos = [r["桩号"] for r in results]
    db.query(Prediction).filter(Prediction.pile_no.in_(pile_nos)).delete(synchronize_session=False)
    objects = []
    for result in results:
        for layer_name in result["土层排序"]:
            objects.append(Prediction(
                pile_no=result["桩号"],
                layer_name=layer_name,
                top_elev_pred=result["土层预测"].get(layer_name),
                bottom_elev_pred=result["土层底标高预测"].get(layer_name),
                method=method,
                created_at=now,
            ))
    db.bulk_save_objects(objects)
    db.commit()


def predict_all(db: Session) -> list[dict]:
    piles = db.query(Pile).order_by(Pile.pile_no).all()
    if not piles:
        return []
    s = get_all_settings(db)
    geo_df = get_geo_as_dataframe(db)
    layer_list = get_layer_names(db)

    import pandas as pd
    piles_df = pd.DataFrame([{
        "桩号": p.pile_no, "X": p.x, "Y": p.y, "桩径": p.diameter, "桩型": p.pile_type
    } for p in piles])

    results = predict_batch(
        geo_df, piles_df, layer_list,
        s["interp_method"], s["support_layer"],
        s["support_depth_type"], float(s["support_depth"])
    )

    pile_top_elev = float(s.get("pile_top_elev", 0.5))
    for r in results:
        r["桩顶标高"] = pile_top_elev

    cache_predictions_bulk(db, results, s["interp_method"])
    return results


def get_scene_data(db: Session) -> dict:
    piles = db.query(Pile).order_by(Pile.pile_no).all()
    geo_df = get_geo_as_dataframe(db)
    s = get_all_settings(db)
    layer_list = get_layer_names(db)
    support_layer = s["support_layer"]
    pile_items = []

    SOIL_COLORS = [
        "#7ec87b", "#8db76d", "#a3a85d", "#b89952", "#c4894a",
        "#cf7a48", "#d46a4a", "#d45a4e", "#cf4e55", "#c4455e",
        "#b34067", "#9e3e6e", "#863d71", "#6f3c70", "#5a3a6a",
    ]
    BEARING_COLOR = "#ff6b35"
    layer_color_map = {}
    if layer_list:
        for i, name in enumerate(layer_list):
            if name == support_layer:
                layer_color_map[name] = BEARING_COLOR
            else:
                layer_color_map[name] = SOIL_COLORS[i % len(SOIL_COLORS)]

    z_min, z_max = 0, 10
    if not geo_df.empty:
        z_vals = geo_df['土层顶标高'].dropna()
        z_min = float(z_vals.min())
        z_max = float(z_vals.max())
        layer_groups = {layer: geo_df[geo_df['土层名称'] == layer] for layer in layer_list}
    else:
        layer_groups = {}

    pile_top_elev = float(s.get("pile_top_elev", 0.5))

    for p in piles:
        pile_row = {"桩号": p.pile_no, "X": p.x, "Y": p.y, "桩径": p.diameter, "桩型": p.pile_type}
        result = do_predict_fast(geo_df, pile_row, layer_list,
                                 support_layer,
                                 s["support_depth_type"], float(s["support_depth"]),
                                 layer_groups=layer_groups)
        bottom_elev = None
        bearing_elev = None
        if result and result.get("持力层顶标高") is not None:
            bearing_elev = result["持力层顶标高"]
            sup_depth_raw = result.get("持力层进入深度", 0)
            bottom_elev = round(bearing_elev - sup_depth_raw, 2)

        soil_segments = []
        if result and bottom_elev is not None:
            pile_bottom = bottom_elev
            for layer_name in layer_list:
                layer_top = result["土层预测"].get(layer_name)
                layer_bottom = result["土层底标高预测"].get(layer_name)
                if layer_top is None or layer_bottom is None:
                    continue
                seg_top = min(pile_top_elev, layer_top)
                seg_bottom = max(pile_bottom, layer_bottom)
                seg_height = seg_top - seg_bottom
                if seg_height < 0.15:
                    continue
                soil_segments.append({
                    "name": layer_name,
                    "top": round(seg_top, 2),
                    "bottom": round(seg_bottom, 2),
                    "color": layer_color_map.get(layer_name, "#95a5a6"),
                    "is_bearing": layer_name == support_layer,
                })

        pile_items.append({
            "id": p.pile_no,
            "x": p.x,
            "y": p.y,
            "diameter": p.diameter,
            "pile_type": p.pile_type,
            "top_elev": pile_top_elev,
            "bottom_elev": bottom_elev,
            "bearing_elev": bearing_elev,
            "soil_segments": soil_segments,
        })

    if not geo_df.empty:
        bx_min, bx_max = float(geo_df["X"].min()), float(geo_df["X"].max())
        by_min, by_max = float(geo_df["Y"].min()), float(geo_df["Y"].max())
    else:
        bx_min, bx_max, by_min, by_max = 0, 100, 0, 100

    if piles:
        px_vals = [p.x for p in piles]
        py_vals = [p.y for p in piles]
        bx_min = min(bx_min, min(px_vals))
        bx_max = max(bx_max, max(px_vals))
        by_min = min(by_min, min(py_vals))
        by_max = max(by_max, max(py_vals))

    return {
        "piles": pile_items,
        "support_layer": support_layer,
        "bounds": {
            "x": [bx_min, bx_max],
            "y": [by_min, by_max],
            "z": [z_min, z_max],
        },
        "soil_planes": [],
    }
