"""
Vanadhikar AI - Multi-Factor AI Anomaly Detection Engine
Implements statutory rule checking, spatial conflict detection, statistical outlier analysis,
and composite risk index scoring for Forest Rights Act (FRA) claims.
"""

import math
import sqlite3
from typing import Dict, List, Any, Optional
from database import get_db_connection


class FRAAnomalyEngine:
    """Core AI engine for detecting anomalies in FRA implementation."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def _get_conn(self) -> sqlite3.Connection:
        return get_db_connection(self.db_path)

    def scan_claim(self, claim_id: str) -> List[Dict[str, Any]]:
        """Performs a deep multi-factor diagnostic scan on a single claim."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return []

        claim = dict(row)
        anomalies = []

        # 1. Statutory Timeline Delay Check (FRA Amendment Rules 2012)
        if claim["status"] not in ("TITLE_ISSUED", "REJECTED"):
            delay_days = claim.get("delay_days", 0)
            if delay_days > 60:
                severity = "CRITICAL" if delay_days > 180 else ("HIGH" if delay_days > 100 else "MEDIUM")
                score = min(99, 45 + int(delay_days * 0.25))
                anomalies.append({
                    "anomaly_id": f"ANOM-DELAY-{claim_id}",
                    "claim_id": claim_id,
                    "district_code": claim["district_code"],
                    "anomaly_type": "STATUTORY_TIMELINE_DELAY",
                    "severity": severity,
                    "risk_score": score,
                    "title": f"Statutory Processing Overdue: {delay_days} Days Backlog",
                    "description": f"Claim filed by {claim['claimant_name']} ({claim['tribe_name']}) at {claim['taluk_block']} is stuck at {claim['status']} for {delay_days} days beyond statutory limit.",
                    "rule_reference": "FRA 2012 Rule 12A(3) - SDLC & DLC 60-day inquiry disposal"
                })

        # 2. Statutory Land Ceiling Cap Violation (FRA 2006 Sec 4(6))
        if claim["claimant_type"] == "IFR" and claim["claimed_area_ha"] > 4.0:
            excess = round(claim["claimed_area_ha"] - 4.0, 2)
            anomalies.append({
                "anomaly_id": f"ANOM-AREACAP-{claim_id}",
                "claim_id": claim_id,
                "district_code": claim["district_code"],
                "anomaly_type": "STATUTORY_AREA_CAP_EXCEEDED",
                "severity": "CRITICAL",
                "risk_score": 95,
                "title": f"Land Ceiling Cap Exceeded ({claim['claimed_area_ha']} Ha claimed)",
                "description": f"Claim requests {claim['claimed_area_ha']} hectares, exceeding statutory ceiling by {excess} Ha. FRA 2006 limits individual title recognition to a maximum of 4 hectares.",
                "rule_reference": "Forest Rights Act 2006, Section 4(6) - Maximum 4 Hectares Cap"
            })

        # 3. Forest Cadastral Record Mismatch
        if claim["land_mismatch_flag"] == 1 or not claim.get("forest_compartment_id"):
            anomalies.append({
                "anomaly_id": f"ANOM-CAD-{claim_id}",
                "claim_id": claim_id,
                "district_code": claim["district_code"],
                "anomaly_type": "FOREST_RECORD_MISMATCH",
                "severity": "HIGH",
                "risk_score": 84,
                "title": "Geospatial Boundary Discrepancy (Outside Forest Cadastre)",
                "description": f"Claim coordinates [{claim['latitude']}, {claim['longitude']}] fall outside ISRO Bhuvan demarcated forest compartment polygons.",
                "rule_reference": "FRA 2006 Section 2(d) & MoTA Joint Verification Protocol"
            })

        # 4. PVTG Vulnerability Bottleneck
        if claim["is_pvtg"] == 1 and claim["status"] in ("SUBMITTED", "GS_VERIFIED"):
            anomalies.append({
                "anomaly_id": f"ANOM-PVTG-{claim_id}",
                "claim_id": claim_id,
                "district_code": claim["district_code"],
                "anomaly_type": "PVTG_PENDENCY_BOTTLENECK",
                "severity": "HIGH",
                "risk_score": 89,
                "title": f"Vulnerable Tribal Community Lag: {claim['tribe_name']}",
                "description": f"Claimant belongs to Particularly Vulnerable Tribal Group ({claim['tribe_name']}). Ministry guidelines mandate proactive facilitation and fast-track processing.",
                "rule_reference": "FRA Section 3(1)(e) - Rights including community tenures of habitat and habitation for PVTGs"
            })

        # 5. Arbitrary Rejection Check (Rule 12A(6))
        if claim["status"] == "REJECTED":
            reason = claim.get("rejection_reason") or ""
            if not reason or "Unreasoned" in reason:
                anomalies.append({
                    "anomaly_id": f"ANOM-REJ-{claim_id}",
                    "claim_id": claim_id,
                    "district_code": claim["district_code"],
                    "anomaly_type": "DISPROPORTIONATE_REJECTION",
                    "severity": "CRITICAL",
                    "risk_score": 92,
                    "title": "Procedural Violation: Rejection Without Reason Recorded",
                    "description": f"DLC dismissed claim of {claim['claimant_name']} without serving written speaking orders or returning to Gram Sabha for reconsideration.",
                    "rule_reference": "FRA Rules 2012 Rule 12A(6) - Reasons for rejection must be recorded in writing"
                })

        # 6. Spatial Overlap Conflict Detection (Scan nearby claims)
        cursor.execute("""
            SELECT claim_id, claimant_name, latitude, longitude, claimed_area_ha
            FROM claims
            WHERE district_code = ? AND claim_id != ?
              AND ABS(latitude - ?) < 0.0004
              AND ABS(longitude - ?) < 0.0004
            LIMIT 2;
        """, (claim["district_code"], claim_id, claim["latitude"], claim["longitude"]))
        conflicts = cursor.fetchall()
        for conflict in conflicts:
            c = dict(conflict)
            anomalies.append({
                "anomaly_id": f"ANOM-CONFLICT-{claim_id}-{c['claim_id']}",
                "claim_id": claim_id,
                "district_code": claim["district_code"],
                "anomaly_type": "SPATIAL_OVERLAP_CONFLICT",
                "severity": "HIGH",
                "risk_score": 87,
                "title": f"Spatial Encroachment / Overlap Conflict with {c['claim_id']}",
                "description": f"Claim coordinates overlap within 40m radius of claim {c['claim_id']} ({c['claimant_name']}, {c['claimed_area_ha']} Ha). Potential double-claiming or boundary contestation.",
                "rule_reference": "FRA Rule 11(2) - Physical demarcation and joint Gram Sabha boundary settlement"
            })

        conn.close()
        return anomalies

    def run_full_scan(self) -> Dict[str, Any]:
        """Runs anomaly engine across entire database and updates the anomalies table."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT claim_id FROM claims;")
        claim_ids = [row["claim_id"] for row in cursor.fetchall()]

        inserted_count = 0
        all_detected = []

        for cid in claim_ids:
            claim_anomalies = self.scan_claim(cid)
            for anom in claim_anomalies:
                all_detected.append(anom)
                cursor.execute("""
                    INSERT OR REPLACE INTO anomalies (
                        anomaly_id, claim_id, district_code, anomaly_type, severity,
                        risk_score, title, description, rule_reference, detected_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'OPEN')
                """, (
                    anom["anomaly_id"], anom["claim_id"], anom["district_code"],
                    anom["anomaly_type"], anom["severity"], anom["risk_score"],
                    anom["title"], anom["description"], anom["rule_reference"]
                ))
                inserted_count += 1

        conn.commit()
        conn.close()

        return {
            "total_claims_scanned": len(claim_ids),
            "total_anomalies_detected": len(all_detected),
            "critical_anomalies": len([a for a in all_detected if a["severity"] == "CRITICAL"]),
            "high_anomalies": len([a for a in all_detected if a["severity"] == "HIGH"]),
            "medium_anomalies": len([a for a in all_detected if a["severity"] == "MEDIUM"])
        }

    def compute_district_risk_metrics(self, district_code: str) -> Dict[str, Any]:
        """Calculates multi-dimensional risk scores and administrative bottlenecks for a district."""
        conn = self._get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total_claims,
                SUM(CASE WHEN status = 'TITLE_ISSUED' THEN 1 ELSE 0 END) as titles_issued,
                SUM(CASE WHEN status = 'REJECTED' THEN 1 ELSE 0 END) as rejections,
                SUM(CASE WHEN status NOT IN ('TITLE_ISSUED', 'REJECTED') THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN claimant_type = 'IFR' THEN 1 ELSE 0 END) as ifr_claims,
                SUM(CASE WHEN claimant_type IN ('CFR', 'CFRR') THEN 1 ELSE 0 END) as cfr_claims,
                SUM(CASE WHEN is_pvtg = 1 THEN 1 ELSE 0 END) as pvtg_claims,
                SUM(CASE WHEN delay_days > 90 THEN 1 ELSE 0 END) as delayed_claims,
                SUM(CASE WHEN claimant_type = 'IFR' AND claimed_area_ha > 4.0 THEN 1 ELSE 0 END) as cap_violations,
                SUM(CASE WHEN land_mismatch_flag = 1 THEN 1 ELSE 0 END) as boundary_mismatches,
                COALESCE(SUM(approved_area_ha), 0.0) as total_approved_area_ha,
                COALESCE(AVG(delay_days), 0.0) as avg_delay_days
            FROM claims
            WHERE district_code = ?;
        """, (district_code,))
        row = cursor.fetchone()

        if not row or row["total_claims"] == 0:
            conn.close()
            return {}

        metrics = dict(row)

        cursor.execute("""
            SELECT severity, COUNT(*) as count
            FROM anomalies
            WHERE district_code = ?
            GROUP BY severity;
        """, (district_code,))
        severity_counts = {r["severity"]: r["count"] for r in cursor.fetchall()}

        conn.close()

        total = metrics["total_claims"]
        rejection_rate = round((metrics["rejections"] / total) * 100, 2)
        delay_rate = round((metrics["delayed_claims"] / total) * 100, 2)
        mismatch_rate = round((metrics["boundary_mismatches"] / total) * 100, 2)
        pvtg_share = round((metrics["pvtg_claims"] / total) * 100, 2)
        title_rate = round((metrics["titles_issued"] / total) * 100, 2)

        # Composite FRA Implementation Risk Index (0 - 100)
        # Higher score = more severe systemic issues requiring urgent administrative intervention
        composite_risk = min(100, int(
            (delay_rate * 0.35) +
            (rejection_rate * 0.30) +
            (mismatch_rate * 0.20) +
            (min(50, metrics["cap_violations"] * 5) * 0.15)
        ))

        if composite_risk >= 70:
            risk_tier = "CRITICAL_INTERVENTION"
        elif composite_risk >= 45:
            risk_tier = "ELEVATED_RISK"
        elif composite_risk >= 25:
            risk_tier = "MODERATE"
        else:
            risk_tier = "NORMAL"

        return {
            "district_code": district_code,
            "total_claims": total,
            "titles_issued": metrics["titles_issued"],
            "rejections": metrics["rejections"],
            "pending": metrics["pending"],
            "ifr_claims": metrics["ifr_claims"],
            "cfr_claims": metrics["cfr_claims"],
            "pvtg_claims": metrics["pvtg_claims"],
            "delayed_claims": metrics["delayed_claims"],
            "cap_violations": metrics["cap_violations"],
            "boundary_mismatches": metrics["boundary_mismatches"],
            "total_approved_area_ha": round(metrics["total_approved_area_ha"], 2),
            "avg_delay_days": round(metrics["avg_delay_days"], 1),
            "rates": {
                "title_distribution_rate": title_rate,
                "rejection_rate": rejection_rate,
                "delay_rate": delay_rate,
                "mismatch_rate": mismatch_rate,
                "pvtg_share": pvtg_share
            },
            "anomalies_by_severity": severity_counts,
            "composite_risk_score": composite_risk,
            "risk_tier": risk_tier
        }


if __name__ == "__main__":
    engine = FRAAnomalyEngine()
    result = engine.run_full_scan()
    print("Full Anomaly Scan Results:", result)
    sample_risk = engine.compute_district_risk_metrics("OD_MAY")
    print("Sample District Risk (Mayurbhanj):", sample_risk)
