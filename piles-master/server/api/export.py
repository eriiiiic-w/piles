import io
import pandas as pd
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from server.database import get_db
from server.models.geo import GeoLayer
from server.services.predict_service import predict_all

router = APIRouter(prefix="/api/export", tags=["export"])


@router.get("/predictions")
def export_predictions(db: Session = Depends(get_db)):
    results = predict_all(db)
    rows = []
    for r in results:
        flat = {
            "桩号": r["桩号"], "X": r["X坐标"], "Y": r["Y坐标"],
            "桩径": r["桩径"], "桩型": r["桩型"],
            "持力层顶标高": r.get("持力层顶标高", ""), "桩顶标高": r.get("桩顶标高", 0.5),
        }
        for k, v in r["土层预测"].items():
            flat[f"{k}顶标高"] = v
        rows.append(flat)
    df = pd.DataFrame(rows)
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=predictions.xlsx"}
    )


@router.get("/measured-holes")
def export_measured_holes(db: Session = Depends(get_db)):
    rows = db.query(GeoLayer).filter(GeoLayer.hole_id.like("实测桩_%")).all()
    if not rows:
        return {"ok": False, "message": "暂无实测数据"}
    df = pd.DataFrame([{
        "孔号": r.hole_id, "X": r.x, "Y": r.y,
        "土层名称": r.layer_name, "土层顶标高": r.top_elev,
        "土层厚度": r.thickness, "土层底标高": r.bottom_elev,
    } for r in rows])
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=measured_holes.xlsx"}
    )
