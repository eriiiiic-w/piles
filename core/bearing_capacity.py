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


class BearingCalc:
    """JGJ94-2008 单桩竖向承载力计算"""

    def __init__(self, store, engine):
        self.store = store
        self.engine = engine
        self.soil_params = {}

    def load_soil_params(self, file_path):
        try:
            df = pd.read_excel(file_path)
            required = ['土层名称', 'qsik']
            for col in required:
                if col not in df.columns:
                    return False, f"缺少必要列: {col}"
            self.soil_params = {}
            for _, row in df.iterrows():
                sp = SoilParams(
                    layer_name=row['土层名称'],
                    qsik=float(row['qsik']),
                    qpk=float(row.get('qpk', 0))
                )
                self.soil_params[row['土层名称']] = sp
            return True, f"加载 {len(self.soil_params)} 个土层参数"
        except Exception as e:
            return False, f"加载失败: {e}"

    def _get_soil_param(self, layer_name):
        if layer_name in self.soil_params:
            return self.soil_params[layer_name]
        return SoilParams(layer_name=layer_name, qsik=0, qpk=0)

    def calculate(self, pile_no, safety_factor=2.0):
        pred = self.engine.predict_one(pile_no)
        if pred is None:
            return None

        pile_info = self.store.pile_data[self.store.pile_data['桩号'] == pile_no]
        diameter_mm = pile_info['桩径'].values[0]
        diameter_m = diameter_mm / 1000.0

        u = np.pi * diameter_m
        Ap = np.pi * (diameter_m ** 2) / 4.0

        pile_top = pred["桩顶标高"]
        support_elev = pred.get("持力层顶标高", pile_top - 20)
        if isinstance(support_elev, str):
            support_elev = pile_top - 20
        pile_bottom = support_elev - pred.get("持力层进入深度(m)", 0)
        pile_length = pile_top - pile_bottom

        layer_list = pred["土层排序"]
        layers = pred["土层预测"]
        bottoms = pred["土层底标高预测"]

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

            sp = self._get_soil_param(layer_name)
            side_res = u * sp.qsik * thickness
            Qsk += side_res
            details.append(LayerDetail(
                layer_name=layer_name,
                thickness=round(thickness, 2),
                qsik=sp.qsik,
                side_resistance=round(side_res, 2)
            ))

        support_layer = self.store.support_layer
        sp_end = self._get_soil_param(support_layer)
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

    def export_calc_sheet(self, result):
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
