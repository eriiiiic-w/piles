from sqlalchemy.orm import Session
from server.models.settings import Setting

DEFAULTS = {
    "support_layer": "",
    "support_depth": "1.5",
    "support_depth_type": "直接输入",
    "warning_threshold": "0.3",
    "alarm_threshold": "0.5",
    "interp_method": "克里金法",
    "pile_top_elev": "0.5",
}


def get_all_settings(db: Session) -> dict:
    rows = db.query(Setting).all()
    result = {}
    for key in DEFAULTS:
        result[key] = DEFAULTS[key]
    for row in rows:
        result[row.key] = row.value
    return result


def update_settings(db: Session, updates: dict) -> dict:
    for key, val in updates.items():
        if val is None:
            continue
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = str(val)
        else:
            db.add(Setting(key=key, value=str(val)))
    db.commit()
    return get_all_settings(db)
