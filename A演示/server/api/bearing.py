import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.models.pile import Pile
from server.models.soil_params import SoilParam
from server.core.bearing_capacity import calculate, load_soil_params, SoilParams
from server.services.predict_service import predict_single

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


@router.post("/calc/{pile_no}")
def calc_bearing(pile_no: str, db: Session = Depends(get_db)):
    pile = db.query(Pile).filter(Pile.pile_no == pile_no).first()
    if not pile:
        return {"ok": False, "message": "桩号不存在"}
    pred = predict_single(db, pile_no)
    if not pred:
        return {"ok": False, "message": "请先预测该桩"}
    soil_rows = db.query(SoilParam).all()
    soil_params_map = {}
    for s in soil_rows:
        soil_params_map[s.layer_name] = SoilParams(
            layer_name=s.layer_name,
            qsik=s.qsik,
            qpk=s.qpk,
        )
    result = calculate(
        pile_row={"桩号": pile.pile_no, "桩径": pile.diameter},
        prediction_result=pred,
        soil_params=soil_params_map,
        support_layer=pred.get("持力层顶标高", ""),
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
            "details": [{
                "layer": d.layer_name,
                "thickness": d.thickness,
                "qsik": d.qsik,
                "resistance": d.side_resistance,
            } for d in result.layer_details],
        }
    }
