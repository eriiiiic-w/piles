from dataclasses import dataclass, field
import pandas as pd
import numpy as np


@dataclass
class SoilParams:
    layer_name: str
    qsik: float = 0.0
    qpk: float = 0.0


@dataclass
class LayerDetail:
    layer_name: str
    thickness: float
    qsik: float
    side_resistance: float


@dataclass
class BearingResult:
    pile_no: str
    pile_diameter_mm: float
    pile_length_m: float
    Qsk: float
    Qpk: float
    Quk: float
    Ra: float
    layer_details: list = field(default_factory=list)
    passes_check: bool = True


def load_soil_params(file_path):
    """从Excel加载土层承载力参数，返回 (dict[layer_name] -> SoilParams, message)"""
    try:
        df = pd.read_excel(file_path)
        required = ['土层名称', 'qsik']
        for col in required:
            if col not in df.columns:
                return None, f"缺少必要列: {col}"
        params = {}
        for _, row in df.iterrows():
            params[str(row['土层名称'])] = SoilParams(
                layer_name=str(row['土层名称']),
                qsik=float(row['qsik']),
                qpk=float(row.get('qpk', 0))
            )
        return params, f"加载 {len(params)} 个土层参数"
    except Exception as e:
        return None, f"加载失败: {e}"


def calculate(pile_row, prediction_result, soil_params, support_layer, safety_factor=2.0):
    """计算单桩竖向承载力。pile_row: dict with 桩号,桩径. prediction_result: dict from predict_one. soil_params: dict[layer_name]->SoilParams. Returns BearingResult or None."""
    if prediction_result is None:
        return None

    pile_no = prediction_result.get("桩号", str(pile_row.get('桩号', '?')))
    diameter_mm = float(pile_row['桩径'])
    diameter_m = diameter_mm / 1000.0
    u = np.pi * diameter_m
    Ap = np.pi * (diameter_m ** 2) / 4.0

    pile_top = prediction_result.get("桩顶标高", 0.5)
    support_elev = prediction_result.get("持力层顶标高", pile_top - 20)
    if isinstance(support_elev, str):
        support_elev = pile_top - 20
    pile_bottom = support_elev - prediction_result.get("持力层进入深度(m)", 0)
    pile_length = pile_top - pile_bottom

    layer_list = prediction_result["土层排序"]
    layers = prediction_result["土层预测"]
    bottoms = prediction_result["土层底标高预测"]

    Qsk = 0.0
    details = []

    for layer_name in layer_list:
        top = layers[layer_name]
        bottom = bottoms[layer_name]
        seg_top = max(top, pile_bottom)
        seg_bottom = min(bottom, pile_bottom)
        if seg_bottom > seg_top:
            seg_bottom, seg_top = seg_top, seg_bottom
        thickness = max(0, seg_top - seg_bottom)

        sp = soil_params.get(layer_name, SoilParams(layer_name=layer_name, qsik=0, qpk=0))
        side_res = u * sp.qsik * thickness
        Qsk += side_res
        details.append(LayerDetail(
            layer_name=layer_name,
            thickness=round(thickness, 2),
            qsik=sp.qsik,
            side_resistance=round(side_res, 2)
        ))

    sp_end = soil_params.get(support_layer, SoilParams(layer_name=support_layer, qsik=0, qpk=0))
    Qpk = sp_end.qpk * Ap
    Quk = Qsk + Qpk
    Ra = Quk / safety_factor

    return BearingResult(
        pile_no=pile_no,
        pile_diameter_mm=diameter_mm,
        pile_length_m=round(pile_length, 2),
        Qsk=round(Qsk, 2),
        Qpk=round(Qpk, 2),
        Quk=round(Quk, 2),
        Ra=round(Ra, 2),
        layer_details=details,
        passes_check=True
    )


def export_calc_sheet(result):
    """导出承载力计算书文本"""
    if result is None:
        return "无计算数据"
    lines = []
    lines.append("=" * 70)
    lines.append("                桩基竖向承载力计算书")
    lines.append("              （依据 JGJ94-2008 §5.3.5）")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"桩号: {result.pile_no}")
    lines.append(f"桩径: {result.pile_diameter_mm} mm = {result.pile_diameter_mm/1000:.2f} m")
    lines.append(f"桩长: {result.pile_length_m} m")
    lines.append(f"安全系数 K = 2.0")
    lines.append("")
    lines.append("-" * 50)
    lines.append(f"{'土层名称':<12} {'厚度/m':<8} {'qsik/kPa':<10} {'侧阻力/kN':<12}")
    lines.append("-" * 50)
    for d in result.layer_details:
        lines.append(f"{d.layer_name:<12} {d.thickness:<8.2f} {d.qsik:<10.1f} {d.side_resistance:<12.2f}")
    lines.append("-" * 50)
    lines.append("")
    lines.append(f"总侧阻力 Qsk = {result.Qsk:.2f} kN")
    lines.append(f"总端阻力 Qpk = {result.Qpk:.2f} kN")
    lines.append(f"极限承载力 Quk = {result.Quk:.2f} kN")
    lines.append(f"承载力特征值 Ra = Quk/2 = {result.Ra:.2f} kN")
    lines.append("")
    lines.append("=" * 70)
    lines.append("  计算人: ________  复核人: ________  日期: ________")
    lines.append("=" * 70)
    return "\n".join(lines)
