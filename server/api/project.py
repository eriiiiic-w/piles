from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from server.database import get_db
from server.models.geo import GeoLayer
from server.models.pile import Pile
from server.schemas import ProjectSummary
from server.services.settings_service import get_all_settings

router = APIRouter(prefix="/api", tags=["project"])


@router.get("/project", response_model=ProjectSummary)
def get_project(db: Session = Depends(get_db)):
    s = get_all_settings(db)
    geo_count = db.query(GeoLayer).count()
    pile_count = db.query(Pile).count()
    hole_count = db.query(GeoLayer.hole_id).distinct().count()
    return ProjectSummary(
        geo_loaded=geo_count > 0,
        pile_loaded=pile_count > 0,
        geo_holes_count=hole_count,
        geo_layers_count=geo_count,
        piles_count=pile_count,
        support_layer=s.get("support_layer", ""),
        interp_method=s.get("interp_method", ""),
    )
