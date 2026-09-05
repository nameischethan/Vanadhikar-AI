"""
Vanadhikar AI - GIS Router (FastAPI)
Serves GeoJSON data for districts, forest compartments, and claim spatial locations.
"""

from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import json
from database import get_db_connection
from anomaly_engine import FRAAnomalyEngine

router = APIRouter()
engine = FRAAnomalyEngine()


@router.get("/districts")
def get_districts(state: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM districts"
    args = []
    if state:
        query += " WHERE state = ?"
        args.append(state)
    cursor.execute(query, args)
    rows = cursor.fetchall()

    features = []
    for r in rows:
        d = dict(r)
        geom = json.loads(d["boundary_geojson"])
        metrics = engine.compute_district_risk_metrics(d["district_code"])
        features.append({
            "type": "Feature",
            "id": d["district_code"],
            "geometry": geom,
            "properties": {
                "district_code": d["district_code"],
                "district_name": d["district_name"],
                "state": d["state"],
                "tribal_population_pct": d["tribal_population_pct"],
                "forest_cover_sqkm": d["forest_cover_sqkm"],
                "center": [d["center_lat"], d["center_lng"]],
                "metrics": metrics
            }
        })
    conn.close()
    return {"type": "FeatureCollection", "features": features}


@router.get("/claims")
def get_claims(
    state: Optional[str] = None,
    district_code: Optional[str] = None,
    status: Optional[str] = None,
    claimant_type: Optional[str] = None,
    is_pvtg: Optional[int] = None,
    anomaly_only: bool = False,
    limit: int = Query(default=600, le=2000),
    offset: int = 0
):
    conn = get_db_connection()
    cursor = conn.cursor()
    filters = []
    args = []
    if state:
        filters.append("state = ?")
        args.append(state)
    if district_code:
        filters.append("district_code = ?")
        args.append(district_code)
    if status:
        filters.append("status = ?")
        args.append(status)
    if claimant_type:
        filters.append("claimant_type = ?")
        args.append(claimant_type)
    if is_pvtg is not None:
        filters.append("is_pvtg = ?")
        args.append(is_pvtg)
    if anomaly_only:
        filters.append("(delay_days > 90 OR (claimant_type = 'IFR' AND claimed_area_ha > 4.0) OR land_mismatch_flag = 1)")

    where = " WHERE " + " AND ".join(filters) if filters else ""
    sql = f"SELECT * FROM claims {where} ORDER BY delay_days DESC LIMIT ? OFFSET ?;"
    args.extend([limit, offset])

    cursor.execute(sql, args)
    rows = cursor.fetchall()
    features = []
    for r in rows:
        c = dict(r)
        geom = json.loads(c["geometry_geojson"])
        has_anom = (c["delay_days"] > 90 or (c["claimant_type"] == "IFR" and c["claimed_area_ha"] > 4.0) or c["land_mismatch_flag"] == 1)
        features.append({
            "type": "Feature",
            "id": c["claim_id"],
            "geometry": geom,
            "properties": {
                "claim_id": c["claim_id"],
                "claimant_name": c["claimant_name"],
                "claimant_type": c["claimant_type"],
                "tribe_name": c["tribe_name"],
                "is_pvtg": bool(c["is_pvtg"]),
                "state": c["state"],
                "district_code": c["district_code"],
                "taluk_block": c["taluk_block"],
                "village": c["village"],
                "status": c["status"],
                "claimed_area_ha": c["claimed_area_ha"],
                "approved_area_ha": c["approved_area_ha"],
                "delay_days": c["delay_days"],
                "has_anomaly": has_anom,
                "land_mismatch": bool(c["land_mismatch_flag"])
            }
        })
    conn.close()
    return {"type": "FeatureCollection", "features": features}


@router.get("/forest-cover")
def get_forest_cover(district_code: Optional[str] = None):
    conn = get_db_connection()
    cursor = conn.cursor()
    query = "SELECT * FROM forest_compartments"
    args = []
    if district_code:
        query += " WHERE district_code = ?"
        args.append(district_code)
    cursor.execute(query, args)
    rows = cursor.fetchall()
    features = []
    for r in rows:
        fc = dict(r)
        geom = json.loads(fc["boundary_geojson"])
        features.append({
            "type": "Feature",
            "id": fc["compartment_id"],
            "geometry": geom,
            "properties": {
                "compartment_id": fc["compartment_id"],
                "district_code": fc["district_code"],
                "compartment_name": fc["compartment_name"],
                "forest_type": fc["forest_type"],
                "recorded_area_ha": fc["recorded_area_ha"],
                "canopy_density_pct": fc["canopy_density_pct"]
            }
        })
    conn.close()
    return {"type": "FeatureCollection", "features": features}


@router.get("/claim-details/{claim_id}")
def get_claim_details(claim_id: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Claim not found")
    claim = dict(row)
    cursor.execute("SELECT * FROM anomalies WHERE claim_id = ?", (claim_id,))
    claim["anomalies"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return claim
