"""
Vanadhikar AI - Decision Support & Analytics Router (FastAPI)
Aggregates state progress, district KPIs, and triage priority lists.
"""

from fastapi import APIRouter, HTTPException
from database import get_db_connection
from anomaly_engine import FRAAnomalyEngine

router = APIRouter()
engine = FRAAnomalyEngine()


@router.get("/state-overview")
def get_state_overview():
    """State-wise progress dashboard panel."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            d.state,
            COUNT(DISTINCT d.district_code) as district_count,
            COUNT(c.claim_id) as total_claims,
            SUM(CASE WHEN c.status = 'TITLE_ISSUED' THEN 1 ELSE 0 END) as titles_issued,
            SUM(CASE WHEN c.status = 'REJECTED' THEN 1 ELSE 0 END) as rejections,
            SUM(CASE WHEN c.status NOT IN ('TITLE_ISSUED', 'REJECTED') THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN c.claimant_type = 'IFR' THEN 1 ELSE 0 END) as ifr_claims,
            SUM(CASE WHEN c.claimant_type IN ('CFR', 'CFRR') THEN 1 ELSE 0 END) as cfr_claims,
            SUM(CASE WHEN c.is_pvtg = 1 THEN 1 ELSE 0 END) as pvtg_claims,
            SUM(CASE WHEN c.delay_days > 90 THEN 1 ELSE 0 END) as delayed_claims,
            COALESCE(SUM(c.approved_area_ha), 0.0) as forest_land_recognized_ha,
            COALESCE(AVG(c.delay_days), 0.0) as avg_delay_days
        FROM districts d
        LEFT JOIN claims c ON d.district_code = c.district_code
        GROUP BY d.state
        ORDER BY total_claims DESC;
    """)
    rows = cursor.fetchall()
    conn.close()

    summaries = []
    for r in rows:
        s = dict(r)
        tot = s["total_claims"] or 1
        s["conversion_rate"] = round((s["titles_issued"] / tot) * 100, 2)
        s["rejection_rate"] = round((s["rejections"] / tot) * 100, 2)
        s["delay_rate"] = round((s["delayed_claims"] / tot) * 100, 2)
        s["forest_land_recognized_ha"] = round(s["forest_land_recognized_ha"], 2)
        s["avg_delay_days"] = round(s["avg_delay_days"], 1)
        summaries.append(s)

    return {"total_states": len(summaries), "state_progress": summaries}


@router.get("/district-kpis/{district_code}")
def get_district_kpis(district_code: str):
    metrics = engine.compute_district_risk_metrics(district_code)
    if not metrics:
        raise HTTPException(status_code=404, detail="District not found")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT taluk_block,
               COUNT(*) as total,
               SUM(CASE WHEN status = 'TITLE_ISSUED' THEN 1 ELSE 0 END) as issued,
               SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejected,
               SUM(CASE WHEN delay_days > 90 THEN 1 ELSE 0 END) as delayed
        FROM claims
        WHERE district_code = ?
        GROUP BY taluk_block;
    """, (district_code,))
    metrics["taluk_breakdown"] = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT tribe_name, COUNT(*) as count,
               SUM(CASE WHEN status = 'TITLE_ISSUED' THEN 1 ELSE 0 END) as issued
        FROM claims
        WHERE district_code = ?
        GROUP BY tribe_name
        ORDER BY count DESC;
    """, (district_code,))
    metrics["tribe_breakdown"] = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return metrics


@router.get("/triage")
def get_triage_list():
    """Ranked priority list of claims requiring immediate intervention."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT a.anomaly_id, a.claim_id, a.district_code, a.severity, a.risk_score,
               a.title, a.description, a.rule_reference,
               c.claimant_name, c.claimant_type, c.tribe_name, c.state, c.taluk_block,
               c.claimed_area_ha, c.status, c.delay_days
        FROM anomalies a
        JOIN claims c ON a.claim_id = c.claim_id
        WHERE a.status = 'OPEN'
        ORDER BY a.risk_score DESC, c.delay_days DESC
        LIMIT 50;
    """)
    triage = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return {"triage_count": len(triage), "priority_action_list": triage}
