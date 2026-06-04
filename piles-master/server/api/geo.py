import tempfile
import os
from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.services.geo_service import import_geo_excel, get_layer_names
from server.models.geo import GeoLayer

router = APIRouter(prefix="/api/geo", tags=["geo"])


@router.post("/upload")
async def upload_geo(file: UploadFile = File(...), db: Session = Depends(get_db)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    try:
        ok, msg = import_geo_excel(db, tmp_path)
        return {"ok": ok, "message": msg}
    finally:
        os.unlink(tmp_path)


@router.get("/layers")
def list_layers(db: Session = Depends(get_db)):
    return {"layers": get_layer_names(db)}


@router.get("/holes")
def list_holes(db: Session = Depends(get_db)):
    holes = db.query(GeoLayer.hole_id, GeoLayer.x, GeoLayer.y).distinct().all()
    return {"holes": [{"hole_id": h[0], "x": h[1], "y": h[2]} for h in holes]}
