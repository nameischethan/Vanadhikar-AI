"""
Vanadhikar AI - Anomalies Router (FastAPI)
Handles AI anomaly scanning, filtering, and resolution management.
"""

from fastapi import APIRouter, Query
from typing import Optional
from database import get_db_connection
from anomaly_engine import FRAAnomalyEngine

router = APIRouter()
engine = FRAAnomalyEngine()


@router.get("/")
def list_anomalies(
    district_code: Optional[str] = None,
    severity: Optional[str] = None,
    anomaly_type: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(default=200, le=1000)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    filters = []
    args = []
    if district_code:
        filters.append("district_code = ?")
        args.append(district_code)
    if severity:
        filters.append("severity = ?")
        args.append(severity.upper())
    if anomaly_type:
        filters.append("anomaly_type = ?")
        args.append(anomaly_type)
    if status:
        filters.append("status = ?")
        args.append(status.upper())

    where = " WHERE " + " AND ".join(filters) if filters else ""
    sql = f"SELECT * FROM anomalies {where} ORDER BY risk_score DESC LIMIT ?;"
    args.append(limit)

    cursor.execute(sql, args)
    anomalies = [dict(r) for r in cursor.fetchall()]

    cursor.execute("SELECT severity, COUNT(*) as count FROM anomalies GROUP BY severity;")
    severity_breakdown = {r["severity"]: r["count"] for r in cursor.fetchall()}

    conn.close()
    return {
        "total": len(anomalies),
        "severity_breakdown": severity_breakdown,
        "anomalies": anomalies
    }


@router.post("/scan")
def trigger_scan():
    """Triggers an on-demand AI scan across all claims in the database."""
    results = engine.run_full_scan()
    return {"status": "success", "scan_results": results}
