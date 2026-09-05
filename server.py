"""
Vanadhikar AI - Complete WebGIS & Decision Support Backend Server
Zero-dependency, production-grade Python HTTP server featuring full REST APIs,
GeoJSON spatial endpoints, AI Anomaly Detection, and an interactive WebGIS & Decision Panel.
"""

import sys
import os
import json
import sqlite3
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any, List, Optional

# Local modules
from database import get_db_connection, init_db, DB_FILE
from anomaly_engine import FRAAnomalyEngine
from ai_summary_engine import AIDecisionSupportEngine

PORT = int(os.environ.get("PORT", 8000))
HOST = "0.0.0.0"

anomaly_engine = FRAAnomalyEngine()
ai_engine = AIDecisionSupportEngine()


class VanadhikarAPIHandler(BaseHTTPRequestHandler):
    """Handles all REST, GeoJSON, AI, and WebGIS requests."""

    def _set_cors_headers(self, status: int = 200, content_type: str = "application/json"):
        self.send_response(status)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")
        self.end_headers()

    def do_OPTIONS(self):
        """Handle CORS pre-flight requests."""
        self._set_cors_headers(204)

    def _parse_query_params(self, url_path: str) -> Dict[str, str]:
        parsed = urllib.parse.urlparse(url_path)
        params = urllib.parse.parse_qs(parsed.query)
        return {k: v[0] for k, v in params.items()}

    def _read_json_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            raw_body = self.rfile.read(content_length).decode("utf-8")
            try:
                return json.loads(raw_body)
            except Exception:
                return {}
        return {}

    def _send_json(self, data: Any, status: int = 200):
        self._set_cors_headers(status, "application/json")
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def _send_error(self, message: str, status: int = 400):
        self._set_cors_headers(status, "application/json")
        self.wfile.write(json.dumps({"error": message, "status": status}).encode("utf-8"))

    # ========================== ROUTING ==========================

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = self._parse_query_params(self.path)

        # 1. WebGIS UI Demo & Documentation
        if path == "/" or path == "/index.html":
            self._serve_webgis_ui()
            return
        elif path == "/docs":
            self._serve_docs()
            return
        elif path in ("/styles.css", "/three_terrain.js", "/app.js") or path.startswith("/frontend/"):
            self._serve_static_file(path)
            return

        # 2. Health check
        elif path in ("/health", "/api/health"):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM claims;")
            claims_c = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM anomalies;")
            anom_c = cursor.fetchone()[0]
            conn.close()
            self._send_json({
                "status": "healthy",
                "system": "Vanadhikar AI Backend",
                "version": "1.0.0",
                "total_claims": claims_c,
                "total_anomalies": anom_c
            })
            return

        # 3. WebGIS GeoJSON Endpoints
        elif path == "/api/gis/districts":
            self._handle_gis_districts(params)
            return
        elif path == "/api/gis/claims":
            self._handle_gis_claims(params)
            return
        elif path == "/api/gis/forest-cover":
            self._handle_gis_forest_cover(params)
            return
        elif path.startswith("/api/gis/claim-details/"):
            claim_id = path.replace("/api/gis/claim-details/", "").strip()
            self._handle_claim_details(claim_id)
            return

        # 4. Anomalies Endpoints
        elif path == "/api/anomalies":
            self._handle_list_anomalies(params)
            return

        # 5. Analytics & Decision-Support Panel Endpoints
        elif path == "/api/analytics/state-overview":
            self._handle_state_overview()
            return
        elif path.startswith("/api/analytics/district-kpis/"):
            district_code = path.replace("/api/analytics/district-kpis/", "").strip()
            self._handle_district_kpis(district_code)
            return
        elif path == "/api/analytics/triage":
            self._handle_triage_list(params)
            return

        # 6. Export Report
        elif path == "/api/export/summary":
            self._handle_export_summary(params)
            return

        else:
            self._send_error(f"Route '{path}' not found. View API documentation at /docs", 404)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        # 1. Trigger Anomaly Scan
        if path == "/api/anomalies/scan":
            result = anomaly_engine.run_full_scan()
            self._send_json({"status": "success", "scan_results": result})
            return

        # 2. AI District Decision Briefing
        elif path.startswith("/api/ai/district-brief/"):
            district_code = path.replace("/api/ai/district-brief/", "").strip()
            metrics = anomaly_engine.compute_district_risk_metrics(district_code)
            if not metrics:
                self._send_error(f"District '{district_code}' not found", 404)
                return
            briefing = ai_engine.generate_district_briefing(district_code, metrics)
            self._send_json(briefing)
            return

        # 3. AI Claim Diagnostic
        elif path.startswith("/api/ai/analyze-claim/"):
            claim_id = path.replace("/api/ai/analyze-claim/", "").strip()
            diag = ai_engine.generate_claim_diagnostic(claim_id)
            if "error" in diag:
                self._send_error(diag["error"], 404)
                return
            self._send_json(diag)
            return

        else:
            self._send_error(f"POST route '{path}' not found.", 404)

    # ========================== HANDLER IMPLEMENTATIONS ==========================

    def _handle_gis_districts(self, params: Dict[str, str]):
        """Returns GeoJSON FeatureCollection of districts with FRA progress metrics."""
        state_filter = params.get("state")
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM districts"
        query_args = []
        if state_filter:
            query += " WHERE state = ?"
            query_args.append(state_filter)

        cursor.execute(query, query_args)
        rows = cursor.fetchall()

        features = []
        for r in rows:
            dist = dict(r)
            geom = json.loads(dist["boundary_geojson"])
            metrics = anomaly_engine.compute_district_risk_metrics(dist["district_code"])

            features.append({
                "type": "Feature",
                "id": dist["district_code"],
                "geometry": geom,
                "properties": {
                    "district_code": dist["district_code"],
                    "district_name": dist["district_name"],
                    "state": dist["state"],
                    "tribal_population_pct": dist["tribal_population_pct"],
                    "forest_cover_sqkm": dist["forest_cover_sqkm"],
                    "center": [dist["center_lat"], dist["center_lng"]],
                    "metrics": metrics
                }
            })

        conn.close()
        self._send_json({
            "type": "FeatureCollection",
            "metadata": {
                "total_districts": len(features),
                "generated_by": "Vanadhikar AI WebGIS Engine"
            },
            "features": features
        })

    def _handle_gis_claims(self, params: Dict[str, str]):
        """Returns GeoJSON FeatureCollection of FRA claim points with spatial filters."""
        conn = get_db_connection()
        cursor = conn.cursor()

        filters = []
        args = []

        if "state" in params:
            filters.append("state = ?")
            args.append(params["state"])
        if "district_code" in params:
            filters.append("district_code = ?")
            args.append(params["district_code"])
        if "status" in params:
            filters.append("status = ?")
            args.append(params["status"])
        if "claimant_type" in params:
            filters.append("claimant_type = ?")
            args.append(params["claimant_type"])
        if "is_pvtg" in params:
            filters.append("is_pvtg = ?")
            args.append(int(params["is_pvtg"]))
        if params.get("anomaly_only", "").lower() in ("true", "1"):
            filters.append("(delay_days > 90 OR (claimant_type = 'IFR' AND claimed_area_ha > 4.0) OR land_mismatch_flag = 1)")

        where_clause = " WHERE " + " AND ".join(filters) if filters else ""
        limit = min(int(params.get("limit", 600)), 2000)
        offset = int(params.get("offset", 0))

        sql = f"SELECT * FROM claims {where_clause} ORDER BY delay_days DESC LIMIT ? OFFSET ?;"
        args.extend([limit, offset])

        cursor.execute(sql, args)
        rows = cursor.fetchall()

        features = []
        for r in rows:
            c = dict(r)
            geom = json.loads(c["geometry_geojson"])
            has_anomaly = (c["delay_days"] > 90 or (c["claimant_type"] == "IFR" and c["claimed_area_ha"] > 4.0) or c["land_mismatch_flag"] == 1)

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
                    "has_anomaly": has_anomaly,
                    "land_mismatch": bool(c["land_mismatch_flag"])
                }
            })

        conn.close()
        self._send_json({
            "type": "FeatureCollection",
            "metadata": {
                "returned_count": len(features),
                "limit": limit,
                "offset": offset
            },
            "features": features
        })

    def _handle_gis_forest_cover(self, params: Dict[str, str]):
        """Returns GeoJSON FeatureCollection of Bhuvan/ISRO forest compartments."""
        conn = get_db_connection()
        cursor = conn.cursor()

        district_filter = params.get("district_code")
        query = "SELECT * FROM forest_compartments"
        args = []
        if district_filter:
            query += " WHERE district_code = ?"
            args.append(district_filter)

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
        self._send_json({
            "type": "FeatureCollection",
            "metadata": {"total_compartments": len(features)},
            "features": features
        })

    def _handle_claim_details(self, claim_id: str):
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM claims WHERE claim_id = ?", (claim_id,))
        claim_row = cursor.fetchone()
        if not claim_row:
            conn.close()
            self._send_error(f"Claim '{claim_id}' not found", 404)
            return

        claim = dict(claim_row)
        cursor.execute("SELECT * FROM anomalies WHERE claim_id = ?", (claim_id,))
        anomalies = [dict(r) for r in cursor.fetchall()]
        conn.close()

        claim["geometry"] = json.loads(claim["geometry_geojson"])
        claim["anomalies"] = anomalies
        self._send_json(claim)

    def _handle_list_anomalies(self, params: Dict[str, str]):
        conn = get_db_connection()
        cursor = conn.cursor()

        filters = []
        args = []
        if "district_code" in params:
            filters.append("district_code = ?")
            args.append(params["district_code"])
        if "severity" in params:
            filters.append("severity = ?")
            args.append(params["severity"].upper())
        if "anomaly_type" in params:
            filters.append("anomaly_type = ?")
            args.append(params["anomaly_type"])
        if "status" in params:
            filters.append("status = ?")
            args.append(params["status"].upper())

        where = " WHERE " + " AND ".join(filters) if filters else ""
        limit = min(int(params.get("limit", 200)), 1000)

        sql = f"SELECT * FROM anomalies {where} ORDER BY risk_score DESC LIMIT ?;"
        args.append(limit)

        cursor.execute(sql, args)
        anomalies = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT severity, COUNT(*) as count FROM anomalies GROUP BY severity;")
        severity_breakdown = {r["severity"]: r["count"] for r in cursor.fetchall()}

        cursor.execute("SELECT anomaly_type, COUNT(*) as count FROM anomalies GROUP BY anomaly_type;")
        type_breakdown = {r["anomaly_type"]: r["count"] for r in cursor.fetchall()}

        conn.close()
        self._send_json({
            "total_returned": len(anomalies),
            "severity_summary": severity_breakdown,
            "type_summary": type_breakdown,
            "anomalies": anomalies
        })

    def _handle_state_overview(self):
        """Decision Support panel: Aggregates progress by state."""
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

        state_summaries = []
        for r in rows:
            s = dict(r)
            tot = s["total_claims"] or 1
            s["conversion_rate"] = round((s["titles_issued"] / tot) * 100, 2)
            s["rejection_rate"] = round((s["rejections"] / tot) * 100, 2)
            s["delay_rate"] = round((s["delayed_claims"] / tot) * 100, 2)
            s["forest_land_recognized_ha"] = round(s["forest_land_recognized_ha"], 2)
            s["avg_delay_days"] = round(s["avg_delay_days"], 1)
            state_summaries.append(s)

        self._send_json({
            "generated_at": "Live Database State",
            "total_states": len(state_summaries),
            "state_progress": state_summaries
        })

    def _handle_district_kpis(self, district_code: str):
        metrics = anomaly_engine.compute_district_risk_metrics(district_code)
        if not metrics:
            self._send_error(f"District '{district_code}' not found", 404)
            return

        conn = get_db_connection()
        cursor = conn.cursor()

        # Taluk/Block Breakdown
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
        taluks = [dict(r) for r in cursor.fetchall()]

        # Tribe breakdown
        cursor.execute("""
            SELECT tribe_name, COUNT(*) as count,
                   SUM(CASE WHEN status = 'TITLE_ISSUED' THEN 1 ELSE 0 END) as issued
            FROM claims
            WHERE district_code = ?
            GROUP BY tribe_name
            ORDER BY count DESC;
        """, (district_code,))
        tribes = [dict(r) for r in cursor.fetchall()]
        conn.close()

        metrics["taluk_breakdown"] = taluks
        metrics["tribe_breakdown"] = tribes
        self._send_json(metrics)

    def _handle_triage_list(self, params: Dict[str, str]):
        """Ranks highest-risk claims requiring urgent administrative intervention."""
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
        triage_items = [dict(r) for r in cursor.fetchall()]
        conn.close()

        self._send_json({
            "triage_count": len(triage_items),
            "priority_action_list": triage_items
        })

    def _handle_export_summary(self, params: Dict[str, str]):
        """Exports decision-support summary."""
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT district_code, district_name, state, tribal_population_pct, forest_cover_sqkm
            FROM districts;
        """)
        districts = [dict(r) for r in cursor.fetchall()]
        conn.close()

        export_data = []
        for d in districts:
            metrics = anomaly_engine.compute_district_risk_metrics(d["district_code"])
            export_data.append({**d, **metrics})

        fmt = params.get("format", "json").lower()
        if fmt == "csv":
            self._set_cors_headers(200, "text/csv")
            headers = ["district_code", "district_name", "state", "total_claims", "titles_issued", "rejections", "pending", "composite_risk_score", "risk_tier"]
            csv_lines = [",".join(headers)]
            for row in export_data:
                csv_lines.append(",".join(str(row.get(h, "")) for h in headers))
            self.wfile.write("\n".join(csv_lines).encode("utf-8"))
            return

        self._send_json({"exported_districts": export_data})

    # ========================== UI & DOCS SERVERS ==========================

    def _serve_static_file(self, path: str):
        """Serves static files (CSS, JS, images) from the frontend/ directory."""
        clean_path = path.replace("/frontend/", "").lstrip("/")
        file_path = Path(__file__).resolve().parent / "frontend" / clean_path
        if file_path.exists() and file_path.is_file():
            mime = "text/plain"
            if clean_path.endswith(".css"):
                mime = "text/css"
            elif clean_path.endswith(".js"):
                mime = "application/javascript"
            elif clean_path.endswith(".html"):
                mime = "text/html"
            elif clean_path.endswith(".png"):
                mime = "image/png"
            elif clean_path.endswith(".jpg") or clean_path.endswith(".jpeg"):
                mime = "image/jpeg"
            elif clean_path.endswith(".svg"):
                mime = "image/svg+xml"

            with open(file_path, "rb") as f:
                content = f.read()
            self._set_cors_headers(200, mime)
            self.wfile.write(content)
        else:
            self._send_error(f"Static file '{clean_path}' not found", 404)

    def _serve_webgis_ui(self):
        """Serves the rich interactive WebGIS map & decision support panel."""
        frontend_html = Path(__file__).resolve().parent / "frontend" / "index.html"
        if frontend_html.exists():
            with open(frontend_html, "rb") as f:
                content = f.read()
            self._set_cors_headers(200, "text/html")
            self.wfile.write(content)
            return

        self._set_cors_headers(200, "text/html")
        html_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Vanadhikar AI - Forest Rights Act (FRA) WebGIS & Decision Support</title>
  <!-- Leaflet CSS & JS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <!-- Google Fonts & Tailwind -->
  <script src="https://cdn.tailwindcss.com"></script>
  <style>
    #map { height: calc(100vh - 70px); }
    .custom-scrollbar::-webkit-scrollbar { width: 6px; }
    .custom-scrollbar::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 4px; }
  </style>
</head>
<body class="bg-slate-900 text-slate-100 flex flex-col h-screen overflow-hidden font-sans">

  <!-- Header Bar -->
  <header class="h-[70px] bg-slate-950 border-b border-emerald-800/40 px-6 flex items-center justify-between z-10">
    <div class="flex items-center space-x-3">
      <div class="w-10 h-10 rounded-lg bg-emerald-600 flex items-center justify-center text-xl font-bold shadow-lg shadow-emerald-900/50">
        🌲
      </div>
      <div>
        <h1 class="text-xl font-extrabold tracking-tight text-white flex items-center gap-2">
          Vanadhikar AI
          <span class="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-900 text-emerald-300 border border-emerald-700">PS-7 FRA Monitoring</span>
        </h1>
        <p class="text-xs text-slate-400">AI-Powered Decision Support & WebGIS Land Record Intelligence</p>
      </div>
    </div>

    <!-- Quick Stats in Header -->
    <div class="hidden md:flex items-center space-x-6 text-sm">
      <div><span class="text-slate-400">Districts:</span> <span id="hdr-districts" class="font-bold text-emerald-400">10</span></div>
      <div><span class="text-slate-400">Total Claims:</span> <span id="hdr-claims" class="font-bold text-blue-400">1,200</span></div>
      <div><span class="text-slate-400">Anomalies:</span> <span id="hdr-anomalies" class="font-bold text-amber-400">--</span></div>
      <button onclick="runAnomalyScan()" class="bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold px-3 py-2 rounded-md shadow flex items-center gap-1.5 transition">
        <span>⚡</span> Rescan AI Anomalies
      </button>
      <a href="/docs" target="_blank" class="text-xs text-slate-300 hover:text-white bg-slate-800 border border-slate-700 px-3 py-2 rounded-md">
        API Docs
      </a>
    </div>
  </header>

  <!-- Main Body: Sidebar + Map + Floating AI Decision Panel -->
  <div class="flex flex-1 overflow-hidden relative">

    <!-- Left Controls / Filter Panel -->
    <aside class="w-80 bg-slate-950/95 border-r border-slate-800 flex flex-col custom-scrollbar overflow-y-auto z-[400] text-xs">
      <div class="p-4 border-b border-slate-800">
        <h2 class="font-bold text-slate-200 uppercase tracking-wider mb-2">WebGIS Spatial Layers</h2>
        <div class="space-y-2">
          <label class="flex items-center space-x-2 text-slate-300 cursor-pointer">
            <input type="checkbox" id="layer-districts" checked onchange="toggleDistrictsLayer()" class="rounded text-emerald-600 focus:ring-0">
            <span>District Boundaries (FRA Polygon)</span>
          </label>
          <label class="flex items-center space-x-2 text-slate-300 cursor-pointer">
            <input type="checkbox" id="layer-forest" checked onchange="toggleForestLayer()" class="rounded text-emerald-600 focus:ring-0">
            <span>ISRO Bhuvan Forest Compartments</span>
          </label>
          <label class="flex items-center space-x-2 text-slate-300 cursor-pointer">
            <input type="checkbox" id="layer-claims" checked onchange="loadClaims()" class="rounded text-emerald-600 focus:ring-0">
            <span>FRA Claims (Spatial Points)</span>
          </label>
          <label class="flex items-center space-x-2 text-amber-400 font-semibold cursor-pointer">
            <input type="checkbox" id="filter-anomaly-only" onchange="loadClaims()" class="rounded text-amber-500 focus:ring-0">
            <span>Show Anomalies Only ⚠️</span>
          </label>
        </div>
      </div>

      <!-- State & District Selector -->
      <div class="p-4 border-b border-slate-800">
        <h2 class="font-bold text-slate-200 uppercase tracking-wider mb-2">Spatial Filter</h2>
        <label class="block text-slate-400 mb-1">State Filter</label>
        <select id="state-select" onchange="onStateChange()" class="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-white mb-3">
          <option value="">All States (Odisha, MP, CG, MH, JH)</option>
          <option value="Odisha">Odisha</option>
          <option value="Madhya Pradesh">Madhya Pradesh</option>
          <option value="Chhattisgarh">Chhattisgarh</option>
          <option value="Maharashtra">Maharashtra</option>
          <option value="Jharkhand">Jharkhand</option>
        </select>

        <label class="block text-slate-400 mb-1">Select District</label>
        <select id="district-select" onchange="onDistrictChange()" class="w-full bg-slate-900 border border-slate-700 rounded p-1.5 text-white">
          <option value="">-- All Districts --</option>
        </select>
      </div>

      <!-- Anomaly Triage Feed -->
      <div class="p-4 flex-1">
        <div class="flex items-center justify-between mb-2">
          <h2 class="font-bold text-slate-200 uppercase tracking-wider">AI Anomaly Triage</h2>
          <span id="triage-count" class="bg-red-950 text-red-400 px-1.5 py-0.5 rounded font-bold">--</span>
        </div>
        <div id="triage-feed" class="space-y-2.5">
          <div class="text-slate-500 italic">Loading anomalies...</div>
        </div>
      </div>
    </aside>

    <!-- Center WebGIS Leaflet Map -->
    <main class="flex-1 relative">
      <div id="map"></div>

      <!-- Map Floating Legend -->
      <div class="absolute bottom-6 left-6 bg-slate-950/90 backdrop-blur border border-slate-800 p-3 rounded-lg z-[400] text-xs shadow-xl space-y-1">
        <div class="font-bold text-slate-300 mb-1">Map Legend</div>
        <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-emerald-500 inline-block"></span> Title Issued (Patta Approved)</div>
        <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-amber-400 inline-block"></span> Pending / In Review</div>
        <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-red-500 inline-block"></span> Rejected</div>
        <div class="flex items-center gap-2"><span class="w-3 h-3 rounded-full bg-purple-500 inline-block ring-2 ring-red-400"></span> Anomaly Detected (Stalled/Cap Violation)</div>
        <div class="flex items-center gap-2"><span class="w-3 h-3 bg-emerald-800/40 border border-emerald-500 inline-block"></span> Reserved / Protected Forest</div>
      </div>
    </main>

    <!-- Right Decision Support & AI Briefing Drawer (Collapsible) -->
    <section id="decision-drawer" class="w-96 bg-slate-950 border-l border-slate-800 flex flex-col custom-scrollbar overflow-y-auto z-[400] text-xs p-4">
      <div class="flex items-center justify-between border-b border-slate-800 pb-3 mb-4">
        <div>
          <h2 class="font-extrabold text-sm text-white">Decision Support Panel</h2>
          <p class="text-slate-400">Executive Summary & State Progress</p>
        </div>
        <button onclick="requestAIBriefing()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-2.5 py-1.5 rounded shadow flex items-center gap-1">
          <span>✨</span> AI Briefing
        </button>
      </div>

      <!-- State Progress Matrix -->
      <div class="mb-5">
        <h3 class="font-bold text-slate-300 uppercase tracking-wider mb-2">State Implementation Matrix</h3>
        <div id="state-matrix" class="space-y-2">
          <div class="text-slate-500 italic">Fetching state metrics...</div>
        </div>
      </div>

      <!-- Selected District Decision Dossier -->
      <div>
        <h3 class="font-bold text-slate-300 uppercase tracking-wider mb-2">AI Administrative Dossier</h3>
        <div id="ai-dossier" class="bg-slate-900 border border-slate-800 p-3 rounded text-slate-300 leading-relaxed font-mono whitespace-pre-wrap">
Select a district or click "AI Briefing" to generate an executive legal analysis for District Collectors.
        </div>
      </div>
    </section>

  </div>

  <script>
    // Initialize WebGIS Map
    const map = L.map('map').setView([21.5, 82.5], 6);
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap contributors & CARTO | Bhuvan ISRO Forest Cadastre'
    }).addTo(map);

    let districtsLayer = L.geoJSON(null).addTo(map);
    let forestLayer = L.geoJSON(null).addTo(map);
    let claimsLayer = L.layerGroup().addTo(map);

    let districtsCache = [];

    async function init() {
      await loadDistricts();
      await loadForestCover();
      await loadClaims();
      await loadStateOverview();
      await loadTriage();
    }

    async function loadDistricts() {
      const res = await fetch('/api/gis/districts');
      const data = await res.json();
      districtsCache = data.features;

      const sel = document.getElementById('district-select');
      sel.innerHTML = '<option value="">-- All Districts --</option>';
      data.features.forEach(f => {
        const opt = document.createElement('option');
        opt.value = f.properties.district_code;
        opt.textContent = `${f.properties.district_name} (${f.properties.state})`;
        sel.appendChild(opt);
      });

      districtsLayer.clearLayers();
      districtsLayer.addData(data);
      districtsLayer.setStyle({
        color: '#10b981',
        weight: 2,
        fillColor: '#059669',
        fillOpacity: 0.1
      });
      districtsLayer.eachLayer(layer => {
        const p = layer.feature.properties;
        layer.bindPopup(`
          <div class="p-1 text-slate-900 text-xs">
            <h3 class="font-bold text-sm text-emerald-800">${p.district_name} (${p.state})</h3>
            <p><strong>Tribal Pop:</strong> ${p.tribal_population_pct}%</p>
            <p><strong>Forest Cover:</strong> ${p.forest_cover_sqkm} sq.km</p>
            <p><strong>Risk Score:</strong> <span class="font-bold text-red-600">${p.metrics?.composite_risk_score ?? '--'}/100</span> (${p.metrics?.risk_tier ?? ''})</p>
            <button onclick="selectDistrict('${p.district_code}')" class="mt-2 bg-emerald-700 text-white px-2 py-1 rounded text-[11px] font-bold">Open AI Dossier</button>
          </div>
        `);
      });
    }

    async function loadForestCover() {
      const res = await fetch('/api/gis/forest-cover');
      const data = await res.json();
      forestLayer.clearLayers();
      forestLayer.addData(data);
      forestLayer.setStyle({
        color: '#22c55e',
        weight: 1,
        fillColor: '#15803d',
        fillOpacity: 0.25,
        dashArray: '4'
      });
    }

    async function loadClaims() {
      const dist = document.getElementById('district-select').value;
      const state = document.getElementById('state-select').value;
      const anomalyOnly = document.getElementById('filter-anomaly-only').checked;

      let url = `/api/gis/claims?limit=800`;
      if (dist) url += `&district_code=${dist}`;
      if (state) url += `&state=${encodeURIComponent(state)}`;
      if (anomalyOnly) url += `&anomaly_only=true`;

      const res = await fetch(url);
      const data = await res.json();

      claimsLayer.clearLayers();
      data.features.forEach(f => {
        const [lng, lat] = f.geometry.coordinates;
        const p = f.properties;

        let color = '#f59e0b';
        if (p.has_anomaly) color = '#a855f7';
        else if (p.status === 'TITLE_ISSUED') color = '#10b981';
        else if (p.status === 'REJECTED') color = '#ef4444';

        const circle = L.circleMarker([lat, lng], {
          radius: p.has_anomaly ? 6 : 4,
          fillColor: color,
          color: p.has_anomaly ? '#f87171' : '#ffffff',
          weight: p.has_anomaly ? 2 : 1,
          opacity: 1,
          fillOpacity: 0.85
        });

        circle.bindPopup(`
          <div class="text-slate-900 text-xs p-1">
            <h4 class="font-bold text-emerald-800">${p.claim_id}</h4>
            <p><strong>Claimant:</strong> ${p.claimant_name}</p>
            <p><strong>Tribe:</strong> ${p.tribe_name} ${p.is_pvtg ? '<span class="text-red-600 font-bold">(PVTG)</span>' : ''}</p>
            <p><strong>Type:</strong> ${p.claimant_type} | <strong>Area:</strong> ${p.claimed_area_ha} Ha</p>
            <p><strong>Status:</strong> ${p.status}</p>
            <p><strong>Delay:</strong> ${p.delay_days} days</p>
            ${p.has_anomaly ? '<p class="text-red-600 font-bold">⚠️ Anomaly Detected</p>' : ''}
            <button onclick="diagnoseClaim('${p.claim_id}')" class="mt-1.5 bg-slate-900 text-white px-2 py-0.5 rounded text-[10px]">AI Diagnostic</button>
          </div>
        `);
        claimsLayer.addLayer(circle);
      });
    }

    async function loadStateOverview() {
      const res = await fetch('/api/analytics/state-overview');
      const data = await res.json();
      const cont = document.getElementById('state-matrix');
      cont.innerHTML = '';

      data.state_progress.forEach(s => {
        const div = document.createElement('div');
        div.className = 'bg-slate-900 border border-slate-800 p-2.5 rounded';
        div.innerHTML = `
          <div class="flex justify-between items-center font-bold text-white mb-1">
            <span>${s.state}</span>
            <span class="text-emerald-400">${s.conversion_rate}% Titles Issued</span>
          </div>
          <div class="grid grid-cols-3 gap-1 text-[11px] text-slate-400">
            <div>Claims: <strong class="text-slate-200">${s.total_claims}</strong></div>
            <div>Issued: <strong class="text-emerald-400">${s.titles_issued}</strong></div>
            <div>Rejected: <strong class="text-red-400">${s.rejections}</strong></div>
            <div>Delayed: <strong class="text-amber-400">${s.delayed_claims}</strong></div>
            <div class="col-span-2">Forest Recognized: <strong class="text-slate-200">${s.forest_land_recognized_ha} Ha</strong></div>
          </div>
        `;
        cont.appendChild(div);
      });
    }

    async function loadTriage() {
      const res = await fetch('/api/analytics/triage');
      const data = await res.json();
      document.getElementById('triage-count').textContent = data.triage_count;
      document.getElementById('hdr-anomalies').textContent = data.triage_count;

      const cont = document.getElementById('triage-feed');
      cont.innerHTML = '';

      data.priority_action_list.slice(0, 15).forEach(item => {
        const div = document.createElement('div');
        div.className = 'bg-slate-900 border-l-2 border-red-500 p-2 rounded cursor-pointer hover:bg-slate-800/80 transition';
        div.onclick = () => diagnoseClaim(item.claim_id);
        div.innerHTML = `
          <div class="flex justify-between font-bold text-slate-200">
            <span>${item.claimant_name}</span>
            <span class="text-[10px] text-red-400 font-extrabold">${item.severity}</span>
          </div>
          <div class="text-[11px] text-slate-400">${item.title}</div>
          <div class="text-[10px] text-amber-300 font-mono mt-0.5">${item.taluk_block} | Risk Score: ${item.risk_score}</div>
        `;
        cont.appendChild(div);
      });
    }

    async function requestAIBriefing() {
      const dist = document.getElementById('district-select').value || 'OD_MAY';
      const dossierEl = document.getElementById('ai-dossier');
      dossierEl.textContent = 'Generating AI Executive Legal Briefing for ' + dist + '...';

      const res = await fetch(`/api/ai/district-brief/${dist}`, { method: 'POST' });
      const data = await res.json();
      dossierEl.textContent = data.briefing_markdown;
    }

    async function diagnoseClaim(claimId) {
      const dossierEl = document.getElementById('ai-dossier');
      dossierEl.textContent = 'Running AI Legal Diagnostic on ' + claimId + '...';

      const res = await fetch(`/api/ai/analyze-claim/${claimId}`, { method: 'POST' });
      const data = await res.json();
      dossierEl.textContent = data.diagnostic_markdown;
    }

    async function runAnomalyScan() {
      const btn = event.currentTarget;
      btn.textContent = 'Scanning...';
      const res = await fetch('/api/anomalies/scan', { method: 'POST' });
      const data = await res.json();
      btn.innerHTML = '<span>⚡</span> Rescan AI Anomalies';
      await loadTriage();
      await loadClaims();
      alert(`AI Scan Complete: Scanned ${data.scan_results.total_claims_scanned} claims, identified ${data.scan_results.total_anomalies_detected} anomalies.`);
    }

    function toggleDistrictsLayer() {
      if (document.getElementById('layer-districts').checked) map.addLayer(districtsLayer);
      else map.removeLayer(districtsLayer);
    }
    function toggleForestLayer() {
      if (document.getElementById('layer-forest').checked) map.addLayer(forestLayer);
      else map.removeLayer(forestLayer);
    }
    function onStateChange() {
      loadClaims();
    }
    function onDistrictChange() {
      const code = document.getElementById('district-select').value;
      if (code) {
        const feat = districtsCache.find(f => f.properties.district_code === code);
        if (feat) {
          map.setView(feat.properties.center, 9);
          requestAIBriefing();
        }
      }
      loadClaims();
    }
    function selectDistrict(code) {
      document.getElementById('district-select').value = code;
      onDistrictChange();
    }

    window.onload = init;
  </script>
</body>
</html>
"""
        self.wfile.write(html_content.encode("utf-8"))

    def _serve_docs(self):
        """Serves interactive Swagger/OpenAPI documentation page."""
        self._set_cors_headers(200, "text/html")
        html_docs = """<!DOCTYPE html>
<html>
<head>
  <title>Vanadhikar AI - API Reference</title>
  <link rel="stylesheet" type="text/css" href="https://unpkg.com/swagger-ui-dist@3/swagger-ui.css">
  <style>body { margin: 0; background: #fafafa; }</style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@3/swagger-ui-bundle.js"></script>
  <script>
    const spec = {
      openapi: "3.0.0",
      info: {
        title: "Vanadhikar AI API",
        version: "1.0.0",
        description: "AI-powered Decision Support System for Forest Rights Act (FRA) Monitoring & WebGIS Engine"
      },
      paths: {
        "/api/gis/districts": {
          get: {
            summary: "Get GeoJSON FeatureCollection of all monitored districts with FRA implementation metrics",
            parameters: [{ name: "state", in: "query", schema: { type: "string" } }],
            responses: { 200: { description: "GeoJSON FeatureCollection" } }
          }
        },
        "/api/gis/claims": {
          get: {
            summary: "Get GeoJSON FeatureCollection of FRA claim coordinates with spatial filtering",
            parameters: [
              { name: "state", in: "query", schema: { type: "string" } },
              { name: "district_code", in: "query", schema: { type: "string" } },
              { name: "status", in: "query", schema: { type: "string" } },
              { name: "claimant_type", in: "query", schema: { type: "string" } },
              { name: "is_pvtg", in: "query", schema: { type: "integer" } },
              { name: "anomaly_only", in: "query", schema: { type: "boolean" } },
              { name: "limit", in: "query", schema: { type: "integer", default: 500 } }
            ],
            responses: { 200: { description: "GeoJSON FeatureCollection" } }
          }
        },
        "/api/gis/forest-cover": {
          get: {
            summary: "Get GeoJSON FeatureCollection of ISRO Bhuvan forest compartments",
            parameters: [{ name: "district_code", in: "query", schema: { type: "string" } }],
            responses: { 200: { description: "GeoJSON FeatureCollection" } }
          }
        },
        "/api/gis/claim-details/{claim_id}": {
          get: {
            summary: "Get full claim record, milestones, documents, and detected anomalies",
            responses: { 200: { description: "Claim record" } }
          }
        },
        "/api/anomalies": {
          get: {
            summary: "List flagged anomalies filtered by district, severity, and anomaly type",
            responses: { 200: { description: "Anomaly list and severity counts" } }
          }
        },
        "/api/anomalies/scan": {
          post: {
            summary: "Trigger on-demand multi-factor AI scan of claim database",
            responses: { 200: { description: "Scan execution results" } }
          }
        },
        "/api/analytics/state-overview": {
          get: {
            summary: "Get state-wise FRA monitoring progress matrix",
            responses: { 200: { description: "State progress overview" } }
          }
        },
        "/api/analytics/district-kpis/{district_code}": {
          get: {
            summary: "Get detailed KPIs, block-wise breakdown, and risk index for a district",
            responses: { 200: { description: "District KPIs" } }
          }
        },
        "/api/analytics/triage": {
          get: {
            summary: "Get ranked triage list of highest-risk stalled claims requiring urgent intervention",
            responses: { 200: { description: "Ranked triage items" } }
          }
        },
        "/api/ai/district-brief/{district_code}": {
          post: {
            summary: "Generate AI executive decision support briefing citing FRA 2006 for District Collector",
            responses: { 200: { description: "AI Decision Dossier" } }
          }
        },
        "/api/ai/analyze-claim/{claim_id}": {
          post: {
            summary: "Generate AI legal diagnostic and recommendation for a specific claim",
            responses: { 200: { description: "Claim Diagnostic" } }
          }
        },
        "/api/export/summary": {
          get: {
            summary: "Export consolidated decision metrics in JSON or CSV format",
            parameters: [{ name: "format", in: "query", schema: { type: "string", enum: ["json", "csv"] } }],
            responses: { 200: { description: "Export file" } }
          }
        }
      }
    };
    SwaggerUIBundle({
      spec: spec,
      dom_id: '#swagger-ui',
      presets: [SwaggerUIBundle.presets.apis],
      layout: "BaseLayout"
    });
  </script>
</body>
</html>
"""
        self.wfile.write(html_docs.encode("utf-8"))


def run_server(port: int = PORT, host: str = HOST):
    """Starts the Vanadhikar AI HTTP server."""
    # Ensure database is initialized
    if not DB_FILE.exists():
        from seed_data import seed_database
        seed_database()

    server_address = (host, port)
    httpd = HTTPServer(server_address, VanadhikarAPIHandler)
    print(f"\n=======================================================")
    print(f"🌲 Vanadhikar AI - FRA Decision Support System Started")
    print(f"📡 API Server & WebGIS running on: http://localhost:{port}")
    print(f"🗺️  Interactive WebGIS Demo UI:    http://localhost:{port}/")
    print(f"📚 OpenAPI / Swagger Docs:         http://localhost:{port}/docs")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        httpd.server_close()


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(port=port_arg)
