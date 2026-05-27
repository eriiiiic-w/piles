"""
根据地勘 CSV 与桩位 CSV，保留「与至少一根桩水平距离不超过阈值」的勘探孔全部土层行，输出 实际勘探孔.csv。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import cKDTree


def read_csv_robust(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="筛选与打桩孔位置相近的勘探孔，生成实际勘探孔.csv"
    )
    parser.add_argument(
        "--geo",
        type=Path,
        default=Path("地勘报告修改版.csv"),
        help="原始地勘 CSV",
    )
    parser.add_argument(
        "--piles",
        type=Path,
        default=Path("西地块地下室桩基施工图 (灌注桩)(1)(1).csv"),
        help="桩基 CSV（含 X,Y）",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("实际勘探孔.csv"),
        help="输出 CSV 路径",
    )
    parser.add_argument(
        "--max-distance-m",
        type=float,
        default=80.0,
        help="勘探孔代表点到最近桩心的平面距离上限（米），默认 80",
    )
    parser.add_argument(
        "--skip-origin",
        action="store_true",
        help="不参与距离判定的占位孔：剔除坐标 (0,0) 的孔号",
    )
    args = parser.parse_args()

    if not args.geo.is_file():
        print(f"找不到: {args.geo}", file=sys.stderr)
        sys.exit(1)
    if not args.piles.is_file():
        print(f"找不到: {args.piles}", file=sys.stderr)
        sys.exit(1)

    geo = read_csv_robust(args.geo)
    piles = read_csv_robust(args.piles)
    for col in ("孔号", "X", "Y"):
        if col not in geo.columns:
            print(f"地勘表缺少列 {col}", file=sys.stderr)
            sys.exit(1)
    if "X" not in piles.columns or "Y" not in piles.columns:
        print("桩基表缺少 X 或 Y", file=sys.stderr)
        sys.exit(1)

    geo = geo.copy()
    geo["X"] = pd.to_numeric(geo["X"], errors="coerce")
    geo["Y"] = pd.to_numeric(geo["Y"], errors="coerce")
    geo = geo.dropna(subset=["孔号", "X", "Y"])

    rep = geo.groupby("孔号", as_index=False).agg({"X": "first", "Y": "first"})
    if args.skip_origin:
        rep = rep[~((rep["X"] == 0) & (rep["Y"] == 0))]

    px = pd.to_numeric(piles["X"], errors="coerce")
    py = pd.to_numeric(piles["Y"], errors="coerce")
    mask_p = px.notna() & py.notna()
    px = px[mask_p].to_numpy(dtype=float)
    py = py[mask_p].to_numpy(dtype=float)
    if len(px) == 0:
        print("无有效桩坐标", file=sys.stderr)
        sys.exit(1)

    tree = cKDTree(np.column_stack((px, py)))
    dist, _ = tree.query(rep[["X", "Y"]].to_numpy(dtype=float))
    keep_ids = set(rep.loc[dist <= args.max_distance_m, "孔号"].astype(str))
    out = geo[geo["孔号"].astype(str).isin(keep_ids)].copy()

    n_holes = rep["孔号"].nunique()
    n_keep = len(keep_ids)
    print(
        f"阈值 {args.max_distance_m:g} m：保留 {n_keep}/{n_holes} 个勘探孔，"
        f"共 {len(out)} 行土层记录 → {args.out}",
        file=sys.stderr,
    )

    out.to_csv(args.out, index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
