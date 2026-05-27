"""一次性迁移脚本：从旧 project_full_data.json 迁移数据到 SQLite"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.database import switch_database, get_db, init_db
from server.models.geo import GeoLayer
from server.models.pile import Pile
from server.models.settings import Setting

OLD_JSON = os.path.join(os.path.dirname(os.path.dirname(__file__)), "project_full_data.json")


def migrate():
    if not os.path.exists(OLD_JSON):
        print(f"未找到 {OLD_JSON}，跳过迁移")
        return

    with open(OLD_JSON, "r", encoding="utf-8") as f:
        data = json.load(f)

    switch_database(os.path.join(os.path.dirname(os.path.dirname(__file__)), "pile_app.db"))
    db = next(get_db())

    count_geo = 0
    for record in data.get("geo_data", []):
        db.add(GeoLayer(
            hole_id=str(record.get("孔号", "")),
            x=float(record.get("X", 0)),
            y=float(record.get("Y", 0)),
            layer_name=str(record.get("土层名称", "")),
            top_elev=float(record.get("土层顶标高", 0)),
            thickness=float(record.get("土层厚度", 2.0)),
            bottom_elev=float(record.get("土层底标高", 0)),
        ))
        count_geo += 1

    count_pile = 0
    for record in data.get("pile_data", []):
        db.add(Pile(
            pile_no=str(record.get("桩号", "")),
            x=float(record.get("X", 0)),
            y=float(record.get("Y", 0)),
            diameter=float(record.get("桩径", 0)),
            pile_type=str(record.get("桩型", "未知")),
        ))
        count_pile += 1

    setting_keys = [
        "support_layer", "support_depth", "support_depth_type",
        "warning_threshold", "alarm_threshold", "interp_method", "pile_top_elev"
    ]
    for key in setting_keys:
        val = data.get(key)
        if val is not None:
            db.add(Setting(key=key, value=str(val)))

    db.commit()
    geo_total = db.query(GeoLayer).count()
    pile_total = db.query(Pile).count()
    print(f"迁移完成: {geo_total} 条地勘数据, {pile_total} 根桩")
    db.close()


if __name__ == "__main__":
    migrate()
