import os
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from server.database import get_db, switch_database, get_active_db_path, dispose_engine, PROJECTS_DIR
from server.models.geo import GeoLayer
from server.models.pile import Pile
from server.schemas import ProjectSummary, ProjectInfo, ProjectListResponse, CreateProjectRequest
from server.services.settings_service import get_all_settings

router = APIRouter(prefix="/api", tags=["project"])

INDEX_PATH = os.path.join(PROJECTS_DIR, "_index.json")


def _read_index() -> list[dict]:
    if not os.path.exists(INDEX_PATH):
        return []
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_index(data: list[dict]):
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _init_first_project():
    """Create a default project if no projects exist. Does NOT auto-activate."""
    index = _read_index()
    if index:
        return  # projects exist, user will choose one to activate
    pid = str(uuid.uuid4())[:8]
    proj = {"id": pid, "name": "默认项目", "created_at": datetime.now().isoformat()}
    index.append(proj)
    _write_index(index)
    # Create empty db file but don't activate it
    target = os.path.join(PROJECTS_DIR, f"{pid}.db")
    switch_database(target)  # briefly switch to create tables, then switch away
    switch_database(":memory:")  # go back to in-memory so no data shows


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


@router.get("/projects", response_model=ProjectListResponse)
def list_projects():
    index = _read_index()
    projects = [ProjectInfo(**p) for p in index]
    return ProjectListResponse(projects=projects, active_id=_active_project_id(index))


def _active_project_id(index: list[dict]) -> str | None:
    active_path = get_active_db_path()
    if not active_path:
        return None
    for p in index:
        if active_path.endswith(f"{p['id']}.db"):
            return p["id"]
    return None


@router.post("/projects", response_model=ProjectInfo)
def create_project(req: CreateProjectRequest):
    pid = str(uuid.uuid4())[:8]
    proj = {"id": pid, "name": req.name, "created_at": datetime.now().isoformat()}
    index = _read_index()
    index.append(proj)
    _write_index(index)
    db_path = os.path.join(PROJECTS_DIR, f"{pid}.db")
    switch_database(db_path)
    return ProjectInfo(**proj)


@router.put("/projects/{project_id}/activate")
def activate_project(project_id: str):
    index = _read_index()
    for p in index:
        if p["id"] == project_id:
            db_path = os.path.join(PROJECTS_DIR, f"{project_id}.db")
            switch_database(db_path)
            return {"ok": True, "active_id": project_id}
    raise HTTPException(404, "项目不存在")


@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    index = _read_index()
    db_path = os.path.join(PROJECTS_DIR, f"{project_id}.db")
    active_path = get_active_db_path()

    # Switch away + dispose engine before deleting to release Windows file handles
    if active_path and os.path.normpath(active_path) == os.path.normpath(db_path):
        remaining = [p for p in index if p["id"] != project_id]
        if remaining:
            new_path = os.path.join(PROJECTS_DIR, f"{remaining[0]['id']}.db")
            switch_database(new_path)
        else:
            switch_database(":memory:")

    index = [p for p in index if p["id"] != project_id]
    _write_index(index)
    dispose_engine()
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except OSError:
            pass
    return {"ok": True}
