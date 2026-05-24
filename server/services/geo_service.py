import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from server.models.geo import GeoLayer


def calc_bottom_elev(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for hole_id, hole_data in df.groupby('孔号'):
        hole_data = hole_data.sort_values('土层顶标高', ascending=False).reset_index(drop=True)
        for i in range(len(hole_data)):
            row = hole_data.iloc[i].to_dict()
            if pd.notna(row.get('土层厚度')) and row['土层厚度'] > 0:
                row['土层底标高'] = row['土层顶标高'] - row['土层厚度']
            else:
                row['土层厚度'] = 2.0
                row['土层底标高'] = row['土层顶标高'] - 2.0
            rows.append(row)
    return pd.DataFrame(rows)


def import_geo_excel(db: Session, file_path: str) -> tuple:
    try:
        df = pd.read_excel(file_path).fillna("无")
        df['X'] = pd.to_numeric(df['X'], errors='coerce')
        df['Y'] = pd.to_numeric(df['Y'], errors='coerce')
        df['土层顶标高'] = pd.to_numeric(df['土层顶标高'], errors='coerce')
        df['土层厚度'] = pd.to_numeric(df['土层厚度'], errors='coerce')
        df = df.dropna(subset=['X', 'Y', '土层顶标高'])
        df = calc_bottom_elev(df)

        db.query(GeoLayer).delete()
        for _, row in df.iterrows():
            db.add(GeoLayer(
                hole_id=str(row['孔号']),
                x=float(row['X']),
                y=float(row['Y']),
                layer_name=str(row['土层名称']),
                top_elev=float(row['土层顶标高']),
                thickness=float(row['土层厚度']),
                bottom_elev=float(row['土层底标高']),
            ))
        db.commit()
        return True, f"导入完成: {len(df)} 条分层, {df['孔号'].nunique()} 个勘探孔"
    except Exception as e:
        return False, f"导入失败: {e}"


def get_geo_as_dataframe(db: Session) -> pd.DataFrame:
    rows = db.query(GeoLayer).all()
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame([{
        '孔号': r.hole_id, 'X': r.x, 'Y': r.y,
        '土层名称': r.layer_name, '土层顶标高': r.top_elev,
        '土层厚度': r.thickness, '土层底标高': r.bottom_elev
    } for r in rows])


def get_layer_names(db: Session) -> list:
    geo_df = get_geo_as_dataframe(db)
    if geo_df.empty:
        return []
    avg = geo_df.groupby('土层名称')['土层顶标高'].mean().sort_values(ascending=False)
    return list(avg.index)
