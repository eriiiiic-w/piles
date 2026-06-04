import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Depends
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session
from server.database import get_db
from server.models.pile import Pile
from server.models.soil_params import SoilParam
from server.core.bearing_capacity import calculate, load_soil_params, SoilParams
from server.services.predict_service import predict_single
from server.services.settings_service import get_all_settings

router = APIRouter(prefix="/api/bearing", tags=["bearing"])


@router.post("/params")
async def upload_params(file: UploadFile = File(...), db: Session = Depends(get_db)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        params, msg = load_soil_params(tmp_path)
        if params is None:
            return {"ok": False, "message": msg}
        for name, sp in params.items():
            existing = db.query(SoilParam).filter(SoilParam.layer_name == name).first()
            if existing:
                existing.qsik = sp.qsik
                existing.qpk = sp.qpk
            else:
                db.add(SoilParam(layer_name=name, qsik=sp.qsik, qpk=sp.qpk))
        db.commit()
        return {"ok": True, "message": msg}
    finally:
        os.unlink(tmp_path)


class SoilParamUpdate(BaseModel):
    layer_name: str
    qsik: Optional[float] = None
    qpk: Optional[float] = None


@router.put("/params")
def update_param(body: SoilParamUpdate, db: Session = Depends(get_db)):
    """手动录入/更新单个土层承载力参数（与原始GUI逐层输入一致）"""
    existing = db.query(SoilParam).filter(SoilParam.layer_name == body.layer_name).first()
    if existing:
        if body.qsik is not None:
            existing.qsik = body.qsik
        if body.qpk is not None:
            existing.qpk = body.qpk
    else:
        db.add(SoilParam(
            layer_name=body.layer_name,
            qsik=body.qsik or 0,
            qpk=body.qpk or 0,
        ))
    db.commit()
    return {"ok": True, "message": f"参数已保存: {body.layer_name}"}


@router.get("/params")
def get_params(db: Session = Depends(get_db)):
    """获取所有已保存的土层承载力参数"""
    rows = db.query(SoilParam).all()
    return {
        "ok": True,
        "params": {r.layer_name: {"qsik": r.qsik, "qpk": r.qpk} for r in rows}
    }


@router.post("/calc/{pile_no}")
def calc_bearing(pile_no: str, db: Session = Depends(get_db)):
    pile = db.query(Pile).filter(Pile.pile_no == pile_no).first()
    if not pile:
        return {"ok": False, "message": "桩号不存在"}
    pred = predict_single(db, pile_no)
    if not pred:
        return {"ok": False, "message": "请先预测该桩"}

    # 从数据库加载岩土参数
    soil_rows = db.query(SoilParam).all()
    soil_params_map = {}
    for s in soil_rows:
        soil_params_map[s.layer_name] = SoilParams(
            layer_name=s.layer_name,
            qsik=s.qsik,
            qpk=s.qpk,
        )

    # 从设置获取持力层名称和安全系数（修复：原代码传入标高值导致qpk查不到）
    settings = get_all_settings(db)
    support_layer = settings["support_layer"]  # 持力层名称，如"中风化岩"
    safety_factor = float(settings.get("safety_factor", 2.0))

    result = calculate(
        pile_row={"桩号": pile.pile_no, "桩径": pile.diameter},
        prediction_result=pred,
        soil_params=soil_params_map,
        support_layer=support_layer,
        safety_factor=safety_factor,
    )
    if result is None:
        return {"ok": False, "message": "计算失败"}
    return {
        "ok": True,
        "result": {
            "pile_no": result.pile_no,
            "diameter_mm": result.pile_diameter_mm,
            "length_m": result.pile_length_m,
            "Qsk": result.Qsk,
            "Qpk": result.Qpk,
            "Quk": result.Quk,
            "Ra": result.Ra,
            "missing_layers": result.missing_layers,
            "details": [{
                "layer": d.layer_name,
                "thickness": d.thickness,
                "qsik": d.qsik,
                "resistance": d.side_resistance,
            } for d in result.layer_details],
        }
    }


@router.post("/calc-all")
def calc_all_bearing(db: Session = Depends(get_db)):
    """批量计算全部桩位承载力（与原始 calculate_all_bearing_capacity 一致）"""
    piles = db.query(Pile).order_by(Pile.pile_no).all()
    if not piles:
        return {"ok": False, "message": "请先导入桩基数据"}

    settings = get_all_settings(db)
    support_layer = settings["support_layer"]
    safety_factor = float(settings.get("safety_factor", 2.0))

    soil_rows = db.query(SoilParam).all()
    soil_params_map = {}
    for s in soil_rows:
        soil_params_map[s.layer_name] = SoilParams(
            layer_name=s.layer_name,
            qsik=s.qsik,
            qpk=s.qpk,
        )

    results = []
    warnings = []
    missing_set = set()

    for p in piles:
        pred = predict_single(db, p.pile_no)
        if not pred:
            continue
        result = calculate(
            pile_row={"桩号": p.pile_no, "桩径": p.diameter},
            prediction_result=pred,
            soil_params=soil_params_map,
            support_layer=support_layer,
            safety_factor=safety_factor,
        )
        if result is None:
            continue
        results.append({
            "pile_no": result.pile_no,
            "diameter_mm": result.pile_diameter_mm,
            "length_m": result.pile_length_m,
            "Qsk": result.Qsk,
            "Qpk": result.Qpk,
            "Quk": result.Quk,
            "Ra": result.Ra,
            "missing_layers": result.missing_layers,
        })
        if result.missing_layers:
            warnings.append(f"{p.pile_no}: 缺参数土层 {', '.join(result.missing_layers)}")
            for m in result.missing_layers:
                missing_set.add(m)

    return {
        "ok": True,
        "count": len(results),
        "results": results,
        "warnings": warnings,
        "missing_layers": list(missing_set),
    }
