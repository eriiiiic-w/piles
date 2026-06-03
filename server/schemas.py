from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class SettingUpdate(BaseModel):
    support_layer: Optional[str] = None
    support_depth: Optional[float] = None
    support_depth_type: Optional[str] = None
    warning_threshold: Optional[float] = None
    alarm_threshold: Optional[float] = None
    interp_method: Optional[str] = None
    pile_top_elev: Optional[float] = None
    safety_factor: Optional[float] = None


class SettingResponse(BaseModel):
    support_layer: str = ""
    support_depth: float = 1.5
    support_depth_type: str = "直接输入"
    warning_threshold: float = 0.3
    alarm_threshold: float = 0.5
    interp_method: str = "克里金法"
    pile_top_elev: float = 0.5
    safety_factor: float = 2.0


class MeasuredCreate(BaseModel):
    pile_no: str
    layer_name: str
    measured_elev: float
    actual_depth: Optional[float] = None


class MeasuredResponse(BaseModel):
    layer_name: str
    measured_elev: float
    recorded_at: str


class PredictionResponse(BaseModel):
    桩号: str
    X坐标: float
    Y坐标: float
    桩径: float
    桩型: str
    土层预测: Dict[str, float]
    土层底标高预测: Dict[str, float]
    土层排序: List[str]
    持力层顶标高: Optional[float] = None
    持力层进入深度: Optional[float] = None
    桩顶标高: float = 0.5


class ProjectSummary(BaseModel):
    geo_loaded: bool = False
    pile_loaded: bool = False
    geo_holes_count: int = 0
    geo_layers_count: int = 0
    piles_count: int = 0
    support_layer: str = ""
    interp_method: str = ""


class SoilSegmentItem(BaseModel):
    name: str
    top: float
    bottom: float
    color: str
    is_bearing: bool = False

class ScenePileItem(BaseModel):
    id: str
    x: float
    y: float
    diameter: float
    pile_type: str
    top_elev: float
    bottom_elev: Optional[float] = None
    bearing_elev: Optional[float] = None
    soil_segments: List[SoilSegmentItem] = []


class SoilPlaneItem(BaseModel):
    name: str
    elevation: float
    color: str


class SceneDataResponse(BaseModel):
    piles: List[ScenePileItem]
    support_layer: str
    bounds: Dict[str, List[float]]
    soil_planes: List[SoilPlaneItem] = []


class ProjectInfo(BaseModel):
    id: str
    name: str
    created_at: str


class ProjectListResponse(BaseModel):
    projects: List[ProjectInfo]
    active_id: Optional[str] = None


class CreateProjectRequest(BaseModel):
    name: str
