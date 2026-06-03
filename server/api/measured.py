import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.schemas import MeasuredCreate
from server.models.measured import Measured
from server.models.geo import GeoLayer
from server.models.pile import Pile

router = APIRouter(prefix="/api/measured", tags=["measured"])


@router.post("")
def save_measured(body: MeasuredCreate, db: Session = Depends(get_db)):
    existing = db.query(Measured).filter(
        Measured.pile_no == body.pile_no,
        Measured.layer_name == body.layer_name
    ).first()
    now = datetime.datetime.now().isoformat()
    if existing:
        existing.measured_elev = body.measured_elev
        existing.actual_depth = body.actual_depth
        existing.recorded_at = now
    else:
        db.add(Measured(
            pile_no=body.pile_no,
            layer_name=body.layer_name,
            measured_elev=body.measured_elev,
            actual_depth=body.actual_depth,
            recorded_at=now,
        ))
    db.flush()

    # ——— 与原始 add_measured_pile_as_geo_hole 一致：实测数据反馈为虚拟勘探孔 ———
    # 获取该桩坐标
    pile = db.query(Pile).filter(Pile.pile_no == body.pile_no).first()
    if pile:
        virtual_hole_id = f"实测桩_{body.pile_no}"
        # 获取该桩所有已实测土层（用于重建完整的虚拟勘探孔）
        all_measured = db.query(Measured).filter(Measured.pile_no == body.pile_no).all()
        measured_layers = {m.layer_name: m.measured_elev for m in all_measured}
        # 删除旧虚拟勘探孔数据，避免重复
        db.query(GeoLayer).filter(GeoLayer.hole_id == virtual_hole_id).delete()
        # 为每个实测土层创建虚拟勘探孔记录
        for layer_name, top_elev in measured_layers.items():
            db.add(GeoLayer(
                hole_id=virtual_hole_id,
                x=pile.x,
                y=pile.y,
                layer_name=layer_name,
                top_elev=top_elev,
                thickness=2.0,
                bottom_elev=top_elev - 2.0,
            ))

    db.commit()
    return {"ok": True, "message": "实测数据已保存"}


@router.get("/{pile_no}")
def get_measured(pile_no: str, db: Session = Depends(get_db)):
    rows = db.query(Measured).filter(Measured.pile_no == pile_no).all()
    return {
        "pile_no": pile_no,
        "layers": {r.layer_name: {"measured_elev": r.measured_elev, "recorded_at": r.recorded_at} for r in rows}
    }
