"""
Vanadhikar AI - AI Decision Support & Legal Reasoning Engine
Integrates with free LLMs (Google Gemini API, Groq, or OpenRouter) while providing a robust
built-in Offline Indian FRA Legal & Administrative Reasoning Engine for instant zero-dependency execution.
"""

import os
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional
from database import get_db_connection


class AIDecisionSupportEngine:
    """Generates executive summaries, legal analysis, and administrative triage for FRA monitoring."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY")
        self.groq_api_key = os.environ.get("GROQ_API_KEY")

    def _call_gemini_api(self, prompt: str) -> Optional[str]:
        """Calls Google Gemini API via REST without external library requirements."""
        if not self.gemini_api_key:
            return None

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 1024
            }
        }

        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                result = json.loads(response.read().decode("utf-8"))
                candidates = result.get("candidates", [])
                if candidates:
                    return candidates[0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"Notice: Gemini API call failed or timed out ({e}). Falling back to internal legal reasoning engine.")
        return None

    def generate_district_briefing(self, district_code: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generates a high-level Decision Support Dossier for District Magistrates and DLC Chairs."""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM districts WHERE district_code = ?", (district_code,))
        dist = dict(cursor.fetchone())

        cursor.execute("""
            SELECT anomaly_type, severity, title, COUNT(*) as count
            FROM anomalies
            WHERE district_code = ?
            GROUP BY anomaly_type, severity
            ORDER BY count DESC;
        """, (district_code,))
        anomaly_summary = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Prompt definition for LLM
        prompt = f"""
You are the Chief Legal and Geospatial Decision Support Advisor to the Ministry of Tribal Affairs (MoTA) and District Level Committee (DLC) for the Forest Rights Act (FRA), 2006.
Review the following district FRA monitoring data for District {dist['district_name']} ({dist['state']}):
- Total claims filed: {metrics.get('total_claims')}
- Titles Distributed: {metrics.get('titles_issued')} ({metrics.get('rates', {}).get('title_distribution_rate')}%)
- Rejected Claims: {metrics.get('rejections')} ({metrics.get('rates', {}).get('rejection_rate')}%)
- Pending Claims: {metrics.get('pending')}
- Statutory Delay Backlog (>90 days): {metrics.get('delayed_claims')}
- Boundary/Cadastral Mismatches: {metrics.get('boundary_mismatches')}
- Statutory Area Ceiling (>4 Ha) Violations: {metrics.get('cap_violations')}
- Composite Implementation Risk Score: {metrics.get('composite_risk_score')}/100 ({metrics.get('risk_tier')})
- Tribal Population: {dist['tribal_population_pct']}%

Generate a concise, authoritative executive decision briefing covering:
1. Executive Summary & Administrative Health
2. Key Bottlenecks & Anomaly Diagnostic (citing FRA 2006 Sec 4(6), Rule 12A, etc.)
3. Time-bound Directives for District Collector / DLC Chairman (30-60 day actions).
Format with clear markdown headings.
"""

        # Try live LLM first
        llm_text = self._call_gemini_api(prompt)
        model_used = "Gemini 1.5 Flash (Online)" if llm_text else "Vanadhikar Legal Intelligence Engine (Offline/Zero-Dep)"

        if not llm_text:
            # High-fidelity offline statutory reasoning generator
            llm_text = self._offline_district_reasoning(dist, metrics, anomaly_summary)

        # Cache briefing into SQLite
        conn = get_db_connection(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO ai_briefings (entity_type, entity_code, summary_text, legal_citations, recommended_actions, metrics_json, model_used)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            "DISTRICT",
            district_code,
            llm_text,
            "FRA 2006 Sec 4(6), FRA Rules 2012 Rule 12A(3), Rule 12A(6), MoTA Guidelines 2015",
            json.dumps([
                "Mandate Sub-Divisional Level Committee (SDLC) special hearings for claims overdue >90 days",
                "Deploy Joint Forest-Revenue GPS field survey teams to resolve cadastral boundary discrepancies",
                "Review all summary rejections under Rule 12A(6) to ensure written speaking orders were issued",
                "Fast-track Particularly Vulnerable Tribal Group (PVTG) habitat rights pursuant to Section 3(1)(e)"
            ]),
            json.dumps(metrics),
            model_used
        ))
        conn.commit()
        conn.close()

        return {
            "district_code": district_code,
            "district_name": dist["district_name"],
            "state": dist["state"],
            "model_used": model_used,
            "briefing_markdown": llm_text,
            "metrics": metrics
        }

    def _offline_district_reasoning(self, dist: Dict[str, Any], metrics: Dict[str, Any], anomalies: list) -> str:
        """Rule-based natural language generator emulating administrative legal counsel."""
        rates = metrics.get("rates", {})
        risk_tier = metrics.get("risk_tier", "NORMAL")
        score = metrics.get("composite_risk_score", 0)

        urgency_statement = (
            "⚠️ **URGENT ADMINISTRATIVE INTERVENTION REQUIRED**: This district displays an alarming backlog and elevated risk index."
            if score >= 50 else
            "ℹ️ **STABLE IMPLEMENTATION WITH TARGETED BOTTLENECKS**: Progress is ongoing but specific procedural bottlenecks require rectification."
        )

        return f"""### Executive Decision Dossier: District {dist['district_name']} ({dist['state']})
**Monitoring Authority**: State Level Monitoring Committee (SLMC) & District Magistrate (DLC Chair)
**Composite FRA Risk Index**: `{score}/100` — **[{risk_tier}]**

{urgency_statement}

---

#### 1. Implementation Progress & Diagnostic Overview
- **Total Claims Docketed**: {metrics.get('total_claims')} claims (IFR: {metrics.get('ifr_claims')}, CFR/CFRR: {metrics.get('cfr_claims')}).
- **Title Recognition Ratio**: `{rates.get('title_distribution_rate')}%` ({metrics.get('titles_issued')} titles finalized, recognizing {metrics.get('total_approved_area_ha')} Hectares).
- **Cumulative Rejection Rate**: `{rates.get('rejection_rate')}%` ({metrics.get('rejections')} claims rejected).
- **Pendency & Processing Backlog**: {metrics.get('pending')} claims ({rates.get('delay_rate')}% delayed beyond statutory timelines).
- **Tribal Demographic Context**: Scheduled Tribes constitute {dist['tribal_population_pct']}% of district population, with {metrics.get('pvtg_claims')} claims from Particularly Vulnerable Tribal Groups (PVTGs).

---

#### 2. Critical Anomalies & Statutory Violations Flagged
1. **Statutory Timeline Breaches (FRA Amendment Rules 2012, Rule 12A(3))**:
   - **{metrics.get('delayed_claims')} claims** exceed the statutory 60-day inquiry window at the Sub-Divisional Level Committee (SDLC). Average delay stands at **{metrics.get('avg_delay_days')} days**.
   - *Legal Mandate*: SDLC is legally bound to dispose of inquiries or record reasons for extension in writing. Prolonged pendency violates claimant statutory tenure rights.

2. **Land Ceiling Violations (FRA 2006, Section 4(6))**:
   - **{metrics.get('cap_violations')} individual claims (IFR)** claim land parcels exceeding the **4.0 hectare absolute statutory ceiling**.
   - *Directive*: DLC must not sanction titles exceeding 4.0 hectares under IFR without converting to Community Forest Resource (CFR) or requiring Gram Sabha rectification.

3. **Geospatial & Cadastral Discrepancies**:
   - **{metrics.get('boundary_mismatches')} claim locations** do not coincide with ISRO Bhuvan demarcated forest compartments or fall in unclassified revenue strips.
   - *Procedural Flaw*: Forest Department field staff are failing to participate in joint Gram Sabha boundary surveys.

4. **Rejection Scrutiny (Rule 12A(6))**:
   - Out of {metrics.get('rejections')} rejections, multiple entries lack documented speaking orders or were dismissed on arbitrary grounds ("lack of satellite proof"), violating the 2015 MoTA Circular and Supreme Court review guidelines.

---

#### 3. Time-Bound Directives for District Level Committee (DLC)
- **[Immediate - 15 Days]**: Convene a Special DLC Tribunal to review the {metrics.get('delayed_claims')} delayed claims stuck at SDLC level.
- **[30 Days]**: Deploy Joint Survey Units (Revenue Inspector + Forest Beat Guard + FRC Member) equipped with mobile GPS to resolve the {metrics.get('boundary_mismatches')} boundary mismatch flags.
- **[45 Days]**: Issue reasoned speaking orders for all rejected claims, giving claimants 60 days to exercise statutory right of appeal under Section 6(4).
- **[60 Days]**: Fast-track habitat rights recognition for PVTG villages under Section 3(1)(e) on a mission mode.
"""

    def generate_claim_diagnostic(self, claim_id: str) -> Dict[str, Any]:
        """Generates legal diagnostic and procedural recommendations for a single contested claim."""
        conn = get_db_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,))
        claim_row = cursor.fetchone()
        if not claim_row:
            conn.close()
            return {"error": "Claim not found"}

        claim = dict(claim_row)

        cursor.execute("SELECT * FROM anomalies WHERE claim_id = ?", (claim_id,))
        anomalies = [dict(r) for r in cursor.fetchall()]
        conn.close()

        # Offline diagnostic generation
        diagnostic_text = f"""### AI Claim Diagnostic Dossier: {claim_id}
**Claimant**: {claim['claimant_name']} | **Tribe**: {claim['tribe_name']} {'(PVTG)' if claim['is_pvtg'] else ''}
**Location**: Village {claim['village']}, GP {claim['gram_panchayat']}, Block {claim['taluk_block']}, {claim['state']}
**Type**: {claim['claimant_type']} | **Claimed Area**: {claim['claimed_area_ha']} Hectares | **Status**: {claim['status']}

---

#### Legal Status & Anomaly Analysis:
- **Anomalies Detected**: {len(anomalies)} issue(s) identified.
"""
        for a in anomalies:
            diagnostic_text += f"- **[{a['severity']}] {a['title']}**: {a['description']} *(Ref: {a['rule_reference']})*\n"

        if not anomalies:
            diagnostic_text += "- **Status**: Verified clean. No statutory delays or geospatial discrepancies detected.\n"

        diagnostic_text += f"""
---
#### Legal Assessment & Recommended Action:
"""
        if claim["claimant_type"] == "IFR" and claim["claimed_area_ha"] > 4.0:
            diagnostic_text += f"- **Ceiling Rectification**: The claimed parcel of {claim['claimed_area_ha']} Ha violates Section 4(6) of FRA 2006. The DLC must restrict title approval to a maximum of 4.0 Ha or advise the claimant to submit a Community Forest Rights (CFR) petition for the remainder.\n"

        if claim["status"] == "REJECTED":
            diagnostic_text += f"- **Appellate Review**: Rejection reason cited: *'{claim.get('rejection_reason', 'Not recorded')}'*. Under FRA Rule 12A(6), if written speaking orders were not provided, this rejection is legally vulnerable. Recommend suo motu review by DLC.\n"

        if claim["delay_days"] > 90:
            diagnostic_text += f"- **Fast-Track Hearing**: Stalled for {claim['delay_days']} days. Recommend placing on priority docket for the next DLC session on Friday.\n"

        return {
            "claim_id": claim_id,
            "claimant_name": claim["claimant_name"],
            "status": claim["status"],
            "anomalies_count": len(anomalies),
            "diagnostic_markdown": diagnostic_text,
            "anomalies": anomalies
        }


if __name__ == "__main__":
    ai_engine = AIDecisionSupportEngine()
    test_metrics = {
        "total_claims": 120, "titles_issued": 21, "rejections": 13, "pending": 86,
        "ifr_claims": 96, "cfr_claims": 24, "pvtg_claims": 26, "delayed_claims": 52,
        "cap_violations": 3, "boundary_mismatches": 15, "total_approved_area_ha": 4380.79,
        "avg_delay_days": 148.6, "composite_risk_score": 58, "risk_tier": "ELEVATED_RISK",
        "rates": {"title_distribution_rate": 17.5, "rejection_rate": 10.83, "delay_rate": 43.33}
    }
    briefing = ai_engine.generate_district_briefing("OD_MAY", test_metrics)
    print("AI Briefing generated successfully! Model used:", briefing["model_used"])
    print(briefing["briefing_markdown"][:350] + "...")
