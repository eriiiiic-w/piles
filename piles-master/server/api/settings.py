from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.schemas import SettingUpdate, SettingResponse
from server.services.settings_service import get_all_settings, update_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("")
def get_settings(db: Session = Depends(get_db)):
    s = get_all_settings(db)
    return SettingResponse(
        support_layer=s["support_layer"],
        support_depth=float(s["support_depth"]),
        support_depth_type=s["support_depth_type"],
        warning_threshold=float(s["warning_threshold"]),
        alarm_threshold=float(s["alarm_threshold"]),
        interp_method=s["interp_method"],
        pile_top_elev=float(s["pile_top_elev"]),
        safety_factor=float(s["safety_factor"]),
    )


@router.put("")
def put_settings(body: SettingUpdate, db: Session = Depends(get_db)):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    s = update_settings(db, updates)
    return SettingResponse(
        support_layer=s["support_layer"],
        support_depth=float(s["support_depth"]),
        support_depth_type=s["support_depth_type"],
        warning_threshold=float(s["warning_threshold"]),
        alarm_threshold=float(s["alarm_threshold"]),
        interp_method=s["interp_method"],
        pile_top_elev=float(s["pile_top_elev"]),
        safety_factor=float(s["safety_factor"]),
    )
