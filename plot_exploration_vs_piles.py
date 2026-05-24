"""
在同一坐标系平面图中叠加勘探孔与打桩孔位置，双色区分并标注编号。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def read_csv_robust(path: Path) -> pd.DataFrame:
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    return pd.read_csv(path)


def load_exploration_holes(
    path: Path, skip_origin: bool
) -> pd.DataFrame:
    df = read_csv_robust(path)
    if "孔号" not in df.columns or "X" not in df.columns or "Y" not in df.columns:
        raise ValueError(f"地勘 CSV 需含列 孔号、X、Y，当前列：{list(df.columns)}")
    df = df.copy()
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    df = df.dropna(subset=["X", "Y", "孔号"])
    holes = df.groupby("孔号", as_index=False).agg({"X": "first", "Y": "first"})
    if skip_origin:
        holes = holes[~((holes["X"] == 0) & (holes["Y"] == 0))]
    return holes


def load_piles(path: Path) -> pd.DataFrame:
    df = read_csv_robust(path)
    if "桩号" not in df.columns or "X" not in df.columns or "Y" not in df.columns:
        raise ValueError(f"桩基 CSV 需含列 桩号、X、Y，当前列：{list(df.columns)}")
    df = df.copy()
    df["X"] = pd.to_numeric(df["X"], errors="coerce")
    df["Y"] = pd.to_numeric(df["Y"], errors="coerce")
    df = df.dropna(subset=["X", "Y", "桩号"])
    return df


def _pile_scatter_sizes(piles: pd.DataFrame) -> np.ndarray:
    """按桩径(mm)给出散点面积 s（略作缩放，避免大圆再次挤在一起）。"""
    if "桩径" in piles.columns:
        diam = pd.to_numeric(piles["桩径"], errors="coerce").fillna(600.0).to_numpy()
    else:
        diam = np.full(len(piles), 600.0)
    # 600mm 基桩约对应 s≈14；略上调上限使大图下仍可见
    return np.clip((diam / 600.0) ** 2 * 12 + 8, 8, 28)


def plot_overlay(
    holes: pd.DataFrame,
    piles: pd.DataFrame,
    *,
    show_labels: bool,
    out_path: Path | None,
    figsize: tuple[float, float],
    dpi: int,
    pile_style: str,
) -> None:
    fig, ax = plt.subplots(figsize=figsize, dpi=dpi)
    color_geo = "#1f77b4"
    color_pile = "#d62728"

    ax.scatter(
        holes["X"],
        holes["Y"],
        c=color_geo,
        s=42,
        zorder=3,
        label="勘探孔",
        edgecolors="white",
        linewidths=0.45,
    )

    pile_s = _pile_scatter_sizes(piles)
    if pile_style == "hollow":
        ax.scatter(
            piles["X"],
            piles["Y"],
            s=pile_s,
            facecolors="none",
            edgecolors=color_pile,
            linewidths=0.95,
            zorder=2,
            label="打桩孔（灌注桩）",
        )
    else:
        ax.scatter(
            piles["X"],
            piles["Y"],
            s=pile_s,
            c=color_pile,
            zorder=2,
            label="打桩孔（灌注桩）",
            edgecolors="#1a1a1a",
            linewidths=0.35,
            alpha=0.88,
        )

    if show_labels:
        fs_geo = 6
        fs_pile = 5
        for _, r in holes.iterrows():
            ax.annotate(
                str(r["孔号"]),
                (r["X"], r["Y"]),
                textcoords="offset points",
                xytext=(3, 3),
                fontsize=fs_geo,
                color=color_geo,
                alpha=0.9,
            )
        for _, r in piles.iterrows():
            ax.annotate(
                str(r["桩号"]),
                (r["X"], r["Y"]),
                textcoords="offset points",
                xytext=(3, -8),
                fontsize=fs_pile,
                color=color_pile,
                alpha=0.85,
            )

    ax.set_aspect("equal", adjustable="box")
    ax.margins(x=0.012, y=0.012)
    ax.grid(True, linestyle="--", alpha=0.3)
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title("勘探孔与打桩孔平面位置叠加")
    ax.legend(loc="upper right", framealpha=0.92)
    fig.tight_layout()

    if out_path is not None:
        fig.savefig(out_path, bbox_inches="tight")
        print(f"已保存: {out_path.resolve()}", file=sys.stderr)

    plt.show()
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="在同一坐标系下绘制勘探孔与打桩孔平面图（双色区分）。"
    )
    parser.add_argument(
        "--geo",
        type=Path,
        default=Path("地勘报告修改版.csv"),
        help="地勘 CSV 路径（含 孔号,X,Y）",
    )
    parser.add_argument(
        "--piles",
        type=Path,
        default=Path("西地块地下室桩基施工图 (灌注桩)(1)(1).csv"),
        help="桩基 CSV 路径（含 桩号,X,Y）",
    )
    parser.add_argument(
        "--skip-origin",
        action="store_true",
        help="剔除坐标为 (0,0) 的勘探孔（常见占位）",
    )
    parser.add_argument(
        "--no-labels",
        action="store_true",
        help="不绘制孔号/桩号文字标注",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="输出图片路径（如 overlay.png 或 overlay.pdf）",
    )
    parser.add_argument(
        "--figsize",
        type=float,
        nargs=2,
        default=(18.0, 14.0),
        metavar=("W", "H"),
        help="画布尺寸（英寸），默认 18 14，便于看清密集桩位",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=140,
        help="分辨率，默认 140（导出 PNG 时更细）",
    )
    parser.add_argument(
        "--pile-style",
        choices=("hollow", "filled"),
        default="hollow",
        help="桩位样式：hollow=空心圆（重叠处仍易分辨），filled=实心",
    )
    parser.add_argument(
        "--crop",
        type=float,
        nargs=4,
        metavar=("XMIN", "XMAX", "YMIN", "YMAX"),
        default=None,
        help="仅绘制该矩形范围内的孔（用于放大查看局部密集区）",
    )
    args = parser.parse_args()

    if not args.geo.is_file():
        print(f"找不到地勘文件: {args.geo}", file=sys.stderr)
        sys.exit(1)
    if not args.piles.is_file():
        print(f"找不到桩基文件: {args.piles}", file=sys.stderr)
        sys.exit(1)

    holes = load_exploration_holes(args.geo, skip_origin=args.skip_origin)
    piles = load_piles(args.piles)
    if args.crop is not None:
        xmin, xmax, ymin, ymax = args.crop
        if xmin >= xmax or ymin >= ymax:
            print("错误: --crop 需满足 xmin<xmax 且 ymin<ymax", file=sys.stderr)
            sys.exit(1)
        holes = holes[
            (holes["X"] >= xmin)
            & (holes["X"] <= xmax)
            & (holes["Y"] >= ymin)
            & (holes["Y"] <= ymax)
        ].copy()
        piles = piles[
            (piles["X"] >= xmin)
            & (piles["X"] <= xmax)
            & (piles["Y"] >= ymin)
            & (piles["Y"] <= ymax)
        ].copy()
        if holes.empty and piles.empty:
            print("警告: 裁剪范围内无数据点", file=sys.stderr)

    plot_overlay(
        holes,
        piles,
        show_labels=not args.no_labels,
        out_path=args.out,
        figsize=(args.figsize[0], args.figsize[1]),
        dpi=args.dpi,
        pile_style=args.pile_style,
    )


if __name__ == "__main__":
    main()
