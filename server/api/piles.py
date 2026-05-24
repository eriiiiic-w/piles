import tempfile
import os
import pandas as pd
from fastapi import APIRouter, UploadFile, File, Depends, Query
from sqlalchemy.orm import Session
from server.database import get_db
from server.models.pile import Pile

router = APIRouter(prefix="/api/piles", tags=["piles"])


@router.post("/upload")
async def upload_piles(file: UploadFile = File(...), db: Session = Depends(get_db)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        df = pd.read_excel(tmp_path)
        df['X'] = pd.to_numeric(df['X'], errors='coerce')
        df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
        df['桩径'] = pd.to_numeric(df['桩径'], errors='coerce')
        db.query(Pile).delete()
        for _, row in df.iterrows():
            db.add(Pile(
                pile_no=str(row['桩号']),
                x=float(row['X']),
                y=float(row['Y']),
                diameter=float(row['桩径']),
                pile_type=str(row.get('桩型', '未知')),
            ))
        db.commit()
        return {"ok": True, "message": f"导入完成: {len(df)} 根桩"}
    except Exception as e:
        return {"ok": False, "message": f"导入失败: {e}"}
    finally:
        os.unlink(tmp_path)


@router.get("")
def list_piles(search: str = Query(""), db: Session = Depends(get_db)):
    q = db.query(Pile)
    if search:
        q = q.filter(Pile.pile_no.contains(search))
    piles = q.order_by(Pile.pile_no).all()
    return {
        "piles": [{
            "pile_no": p.pile_no, "x": p.x, "y": p.y,
            "diameter": p.diameter, "pile_type": p.pile_type,
        } for p in piles]
    }


@router.get("/{pile_no}")
def get_pile(pile_no: str, db: Session = Depends(get_db)):
    pile = db.query(Pile).filter(Pile.pile_no == pile_no).first()
    if not pile:
        return {"ok": False, "message": "桩号不存在"}
    return {
        "ok": True,
        "pile": {
            "pile_no": pile.pile_no, "x": pile.x, "y": pile.y,
            "diameter": pile.diameter, "pile_type": pile.pile_type,
        }
    }
