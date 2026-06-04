from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.services import predict_service

router = APIRouter(prefix="/api/predict", tags=["predict"])


@router.post("/single/{pile_no}")
def run_single(pile_no: str, db: Session = Depends(get_db)):
    result = predict_service.predict_single(db, pile_no)
    if result is None:
        return {"ok": False, "message": "预测失败，请确认数据已加载且桩号存在"}
    predict_service.cache_prediction(db, result, "按需")
    return {"ok": True, "result": result}


@router.post("/all")
def run_all(db: Session = Depends(get_db)):
    results = predict_service.predict_all(db)
    return {"ok": True, "count": len(results), "results": results}


@router.get("/scene-data")
def get_scene(db: Session = Depends(get_db)):
    return predict_service.get_scene_data(db)
