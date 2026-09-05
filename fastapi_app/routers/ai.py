"""
Vanadhikar AI - AI Decision Support & LLM Router (FastAPI)
Generates AI briefings citing FRA 2006 legal provisions and claim diagnostics.
"""

from fastapi import APIRouter, HTTPException
from ai_summary_engine import AIDecisionSupportEngine
from anomaly_engine import FRAAnomalyEngine

router = APIRouter()
ai_engine = AIDecisionSupportEngine()
anomaly_engine = FRAAnomalyEngine()


@router.post("/district-brief/{district_code}")
def generate_district_brief(district_code: str):
    metrics = anomaly_engine.compute_district_risk_metrics(district_code)
    if not metrics:
        raise HTTPException(status_code=404, detail="District not found")
    briefing = ai_engine.generate_district_briefing(district_code, metrics)
    return briefing


@router.post("/analyze-claim/{claim_id}")
def analyze_claim(claim_id: str):
    diag = ai_engine.generate_claim_diagnostic(claim_id)
    if "error" in diag:
        raise HTTPException(status_code=404, detail=diag["error"])
    return diag
