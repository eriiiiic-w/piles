import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.schemas import MeasuredCreate
from server.models.measured import Measured

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
    db.commit()
    return {"ok": True, "message": "实测数据已保存"}


@router.get("/{pile_no}")
def get_measured(pile_no: str, db: Session = Depends(get_db)):
    rows = db.query(Measured).filter(Measured.pile_no == pile_no).all()
    return {
        "pile_no": pile_no,
        "layers": {r.layer_name: {"measured_elev": r.measured_elev, "recorded_at": r.recorded_at} for r in rows}
    }
