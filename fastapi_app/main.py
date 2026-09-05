"""
Vanadhikar AI - Production FastAPI Application
Modern async REST API with automatic OpenAPI interactive docs, Pydantic validation, and CORS.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
import os
import sys

# Add parent directory to path so database and engines can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi_app.routers import gis, anomalies, analytics, ai
from database import DB_FILE, init_db
from seed_data import seed_database

app = FastAPI(
    title="Vanadhikar AI API",
    description="AI-powered Decision Support System for Forest Rights Act (FRA) Monitoring",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for Frontend GIS Maps (Leaflet.js / Mapbox)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include sub-routers
app.include_router(gis.router, prefix="/api/gis", tags=["WebGIS & Spatial Data"])
app.include_router(anomalies.router, prefix="/api/anomalies", tags=["AI Anomaly Detection"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Decision Support & Analytics"])
app.include_router(ai.router, prefix="/api/ai", tags=["AI Decision Briefings & LLM"])


@app.on_event("startup")
def on_startup():
    if not DB_FILE.exists():
        seed_database()


@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "system": "Vanadhikar AI (FastAPI Engine)",
        "version": "1.0.0"
    }


@app.get("/", response_class=HTMLResponse, tags=["WebGIS UI"])
def get_map_view():
    """Serves the interactive Leaflet WebGIS interface."""
    from server import VanadhikarAPIHandler
    # Return same HTML interface
    import inspect
    handler = VanadhikarAPIHandler.__new__(VanadhikarAPIHandler)
    # Read HTML content from server.py directly or redirect
    return RedirectResponse(url="/docs")
