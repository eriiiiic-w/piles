import os
import sys
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="桩基土层预测系统", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup():
    from server.api.project import _init_first_project
    _init_first_project()


# Register all API routers
from server.api.project import router as project_router
from server.api.settings import router as settings_router
from server.api.geo import router as geo_router
from server.api.piles import router as piles_router
from server.api.predict import router as predict_router
from server.api.measured import router as measured_router
from server.api.bearing import router as bearing_router
from server.api.export import router as export_router

app.include_router(project_router)
app.include_router(settings_router)
app.include_router(geo_router)
app.include_router(piles_router)
app.include_router(predict_router)
app.include_router(measured_router)
app.include_router(bearing_router)
app.include_router(export_router)

# Serve React static files (must be last, mounts at /)
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client", "dist")
if os.path.exists(STATIC_DIR):
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
