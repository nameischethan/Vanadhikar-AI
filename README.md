# Vanadhikar AI (वनअधिकार AI)
### AI-Powered Decision Support System for Forest Rights Act (FRA) Monitoring
> **Problem Statement PS-7**: Implementation of the Forest Rights Act is hard to track across states — claims, approvals, and land-use data are fragmented, making it difficult for officials to monitor progress and flag anomalies.

---

## 🌟 Overview & High-Impact Features

**Vanadhikar AI** is a decision support and WebGIS monitoring platform engineered specifically for the Ministry of Tribal Affairs (MoTA), State Level Monitoring Committees (SLMC), and District Magistrates (DLC Chairpersons). It reconciles fragmented tribal claims, forest cadastral layers, and committee review timelines.

```
                  ┌────────────────────────────────────────┐
                  │       Frontend Client Application      │
                  │ (Leaflet.js / Mapbox / React / Native) │
                  └───────────────────┬────────────────────┘
                                      │ REST / GeoJSON
                                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          Vanadhikar AI Backend                           │
├──────────────────────────────────────────────────────────────────────────┤
│ 🗺️  WebGIS Spatial Engine      │ 🧠 AI Anomaly Detection Engine          │
│  - GeoJSON Districts & Polygons │  - Timeline Delay Violation Detector    │
│  - ISRO Bhuvan Forest Cadastre  │  - Sec 4(6) Area Cap (>4ha) Detector    │
│  - Spatial Claim Coordinates    │  - Forest Cadastral Discrepancy Flag    │
│  - Status & Demographics Filter │  - Double-Dipping & Overlap Detector    │
├─────────────────────────────────┼────────────────────────────────────────┤
│ 📊 Decision Support Analytics   │ ⚖️ LLM / Legal Reasoning Layer         │
│  - State Progress Matrix        │  - Gemini / Free LLM Integration       │
│  - District Collector KPIs      │  - Offline FRA 2006 Legal Reasoning    │
│  - Administrative Triage Docket │  - Time-Bound Action Directives        │
└─────────────────────────────────┴────────────────────────────────────────┘
```

---

## 🎯 Exact Match to PS-7 Expected Build

| Requirement in Photo | Vanadhikar AI Implementation | API Endpoint |
|---|---|---|
| **WebGIS-style map view of mock FRA claim data by district** | GeoJSON `FeatureCollection` for 10 high-tribal districts across Odisha, MP, Chhattisgarh, Maharashtra, and Jharkhand with Bhuvan forest compartments & 1,200+ spatial claims. | `GET /api/gis/districts`<br>`GET /api/gis/claims`<br>`GET /api/gis/forest-cover` |
| **AI layer that flags anomalies** | Multi-factor anomaly engine flagging statutory delays (>90 days), FRA Sec 4(6) ceiling violations (>4.0 Ha), Bhuvan boundary mismatches, and DLC unreasoned rejections. | `GET /api/anomalies`<br>`POST /api/anomalies/scan`<br>`GET /api/analytics/triage` |
| **Simple decision-support panel summarizing state-wise progress** | Live dashboard aggregating conversion rates, pendency, land recognized in hectares, and composite district implementation risk index (0–100). | `GET /api/analytics/state-overview`<br>`GET /api/analytics/district-kpis/{code}` |
| **Free LLM for anomaly-summary text** | Integrates with Google Gemini API (`GEMINI_API_KEY`) and includes a built-in zero-dependency Indian FRA Legal Reasoning Engine citing FRA 2006 sections & rules. | `POST /api/ai/district-brief/{code}`<br>`POST /api/ai/analyze-claim/{id}` |

---

## 🚀 Quick Start (Zero Dependencies Required)

The backend has **zero mandatory third-party dependencies** and runs out of the box with standard Python 3.

### 1. Run Server
```bash
cd /Users/chethansaiurumu/.gemini/antigravity/scratch/vanadhikar-ai
python3 server.py 8000
```

### 2. Access WebGIS Demo & API Docs
- 🗺️ **Interactive WebGIS & Decision Panel**: [http://localhost:8000/](http://localhost:8000/)
- 📚 **Swagger / OpenAPI Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🩺 **Health Check**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 🛠️ Production FastAPI Setup (Optional)

If deploying with FastAPI and Uvicorn:

```bash
pip install -r requirements.txt
uvicorn fastapi_app.main:app --host 0.0.0.0 --port 8000 --reload
```

Or via Docker:
```bash
docker build -t vanadhikar-ai .
docker run -p 8000:8000 vanadhikar-ai
```

---

## 📡 Complete REST API Reference

### 1. WebGIS Spatial Endpoints
- `GET /api/gis/districts`
  - Returns GeoJSON `FeatureCollection` of district boundaries with composite risk scores.
  - *Params*: `state` (optional)
- `GET /api/gis/claims`
  - Returns GeoJSON `FeatureCollection` of individual and community forest claims.
  - *Params*: `state`, `district_code`, `status`, `claimant_type` (IFR/CFR/CFRR), `is_pvtg` (0/1), `anomaly_only` (true/false), `limit`, `offset`.
- `GET /api/gis/forest-cover`
  - Returns GeoJSON polygons of ISRO Bhuvan forest compartments and reserved forest blocks.
- `GET /api/gis/claim-details/{claim_id}`
  - Returns full claim history, submission timestamp, Gram Sabha/SDLC dates, and anomalies.

### 2. AI Anomaly Engine Endpoints
- `GET /api/anomalies`
  - Returns detected anomalies with severity breakdown (`CRITICAL`, `HIGH`, `MEDIUM`).
  - *Params*: `district_code`, `severity`, `anomaly_type`, `status`, `limit`.
- `POST /api/anomalies/scan`
  - Triggers an automated multi-factor AI scan across all claims in the database.

### 3. Decision Support & Analytics Endpoints
- `GET /api/analytics/state-overview`
  - Aggregates state-wise implementation matrices (titles distributed, conversion rates, land recognized in hectares, pending backlogs).
- `GET /api/analytics/district-kpis/{district_code}`
  - Detailed district collector dashboard with block-wise and tribe-wise breakdowns.
- `GET /api/analytics/triage`
  - Ranked priority action list of the highest-risk stalled claims.
- `GET /api/export/summary?format=json` or `?format=csv`
  - Exportable decision dossiers for state-level monitoring committee meetings.

### 4. AI Briefings & LLM Endpoints
- `POST /api/ai/district-brief/{district_code}`
  - Generates an executive decision support dossier citing statutory rules for District Magistrates.
- `POST /api/ai/analyze-claim/{claim_id}`
  - Generates legal assessment and actionable next steps for contested claims.

---

## ⚖️ Anomaly Detection & Legal Rules Catalog

1. **Statutory Delay (`STATUTORY_TIMELINE_DELAY`)**:
   - *Legal Reference*: FRA Amendment Rules 2012, Rule 12A(3).
   - *Logic*: Flags claims exceeding 60-90 days at SDLC or DLC without recorded reasons.
2. **Statutory Land Ceiling Cap (`STATUTORY_AREA_CAP_EXCEEDED`)**:
   - *Legal Reference*: Forest Rights Act 2006, Section 4(6).
   - *Logic*: Flags Individual Forest Rights (IFR) claims claiming > 4.0 Hectares.
3. **Forest Cadastre Discrepancy (`FOREST_RECORD_MISMATCH`)**:
   - *Legal Reference*: FRA Section 2(d) & MoTA Joint Verification Protocols.
   - *Logic*: Flags claims whose coordinates fall outside ISRO Bhuvan forest compartment polygons.
4. **Unreasoned DLC Rejections (`DISPROPORTIONATE_REJECTION`)**:
   - *Legal Reference*: FRA Rules 2012, Rule 12A(6).
   - *Logic*: Flags rejections where written speaking orders were not issued to claimants.
5. **PVTG Habitat Neglect (`PVTG_PENDENCY_BOTTLENECK`)**:
   - *Legal Reference*: FRA Section 3(1)(e).
   - *Logic*: Fast-tracks Particularly Vulnerable Tribal Groups (Birhor, Baiga, Dongria Kondh, etc.).

---

## 🧪 Automated Verification
Run the built-in automated test suite:
```bash
python3 test_backend.py
```
Outputs test passes for all 26 verification checkpoints.
