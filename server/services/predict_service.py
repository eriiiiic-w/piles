import datetime
from sqlalchemy.orm import Session
from server.core.prediction import predict_one as do_predict, predict_one_fast as do_predict_fast
from server.core.prediction import get_layer_list as core_get_layer_list
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
    pile_row = {"桩号": pile.pile_no, "X": pile.x, "Y": pile.y, "桩径": pile.diameter, "桩型": pile.pile_type}
    result = do_predict(geo_df, pile_row, layer_list,
                        s["interp_method"], s["support_layer"],
                        s["support_depth_type"], float(s["support_depth"]))
    result["桩顶标高"] = float(s.get("pile_top_elev", 0.5))
    # Normalize key names to match frontend schema
    if "持力层进入深度(m)" in result:
        result["持力层进入深度"] = result.pop("持力层进入深度(m)")
    if "桩径(mm)" in result:
        result["桩径"] = result.pop("桩径(mm)")
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
    pile_row = {"桩号": pile.pile_no, "X": pile.x, "Y": pile.y, "桩径": pile.diameter, "桩型": pile.pile_type}
    result = do_predict_fast(geo_df, pile_row, layer_list,
                             s["support_layer"],
                             s["support_depth_type"], float(s["support_depth"]))
    result["桩顶标高"] = float(s.get("pile_top_elev", 0.5))
    if "持力层进入深度(m)" in result:
        result["持力层进入深度"] = result.pop("持力层进入深度(m)")
    if "桩径(mm)" in result:
        result["桩径"] = result.pop("桩径(mm)")
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


def predict_all(db: Session) -> list[dict]:
    piles = db.query(Pile).order_by(Pile.pile_no).all()
    s = get_all_settings(db)
    geo_df = get_geo_as_dataframe(db)
    layer_list = get_layer_names(db)
    results = []
    for p in piles:
        pile_row = {"桩号": p.pile_no, "X": p.x, "Y": p.y, "桩径": p.diameter, "桩型": p.pile_type}
        r = do_predict(geo_df, pile_row, layer_list,
                       s["interp_method"], s["support_layer"],
                       s["support_depth_type"], float(s["support_depth"]))
        r["桩顶标高"] = float(s.get("pile_top_elev", 0.5))
        if "持力层进入深度(m)" in r:
            r["持力层进入深度"] = r.pop("持力层进入深度(m)")
        if "桩径(mm)" in r:
            r["桩径"] = r.pop("桩径(mm)")
        results.append(r)
        cache_prediction(db, r, s["interp_method"])
    return results


def get_scene_data(db: Session) -> dict:
    piles = db.query(Pile).order_by(Pile.pile_no).all()
    geo_df = get_geo_as_dataframe(db)
    s = get_all_settings(db)
    layer_list = get_layer_names(db)
    support_layer = s["support_layer"]
    pile_items = []

    z_min, z_max = 0, 10
    if not geo_df.empty:
        z_vals = geo_df['土层顶标高'].dropna()
        z_min = float(z_vals.min())
        z_max = float(z_vals.max())
        layer_groups = {layer: geo_df[geo_df['土层名称'] == layer] for layer in layer_list}
    else:
        layer_groups = {}

    for p in piles:
        pile_row = {"桩号": p.pile_no, "X": p.x, "Y": p.y, "桩径": p.diameter, "桩型": p.pile_type}
        result = do_predict_fast(geo_df, pile_row, layer_list,
                                 support_layer,
                                 s["support_depth_type"], float(s["support_depth"]),
                                 layer_groups=layer_groups)
        bottom_elev = None
        if result and result.get("持力层顶标高") is not None:
            sup_elev = result["持力层顶标高"]
            sup_depth_raw = result.get("持力层进入深度(m)", 0)
            bottom_elev = round(sup_elev - sup_depth_raw, 2)

        pile_items.append({
            "id": p.pile_no,
            "x": p.x,
            "y": p.y,
            "diameter": p.diameter,
            "pile_type": p.pile_type,
            "top_elev": float(s.get("pile_top_elev", 0.5)),
            "bottom_elev": bottom_elev,
        })

    # Compute soil planes: average elevation per layer
    SOIL_COLORS = [
        "#c8b68e", "#b5a67c", "#a2b578", "#8f9e74", "#7c8e70",
        "#d4c5a0", "#bfb386", "#aaa16c", "#958f52", "#807d38",
        "#e8dcc8", "#d5c9b3", "#c2b69e", "#afa389", "#9c9074",
    ]
    soil_planes = []
    if not geo_df.empty:
        layer_names = core_get_layer_list(geo_df)
        for i, layer in enumerate(layer_names):
            avg_elev = float(geo_df[geo_df['土层名称'] == layer]['土层顶标高'].mean())
            color = SOIL_COLORS[i % len(SOIL_COLORS)]
            soil_planes.append({"name": layer, "elevation": round(avg_elev, 2), "color": color})

    return {
        "piles": pile_items,
        "support_layer": support_layer,
        "bounds": {
            "x": [float(geo_df["X"].min()), float(geo_df["X"].max())] if not geo_df.empty else [0, 100],
            "y": [float(geo_df["Y"].min()), float(geo_df["Y"].max())] if not geo_df.empty else [0, 100],
            "z": [z_min, z_max],
        },
        "soil_planes": soil_planes,
    }
