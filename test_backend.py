"""
Vanadhikar AI - Automated Verification & Test Suite
Tests all database operations, WebGIS GeoJSON data structures, AI anomaly detection algorithms,
decision support summaries, and simulated HTTP request handlers without network socket dependencies.
"""

import io
import json
import sqlite3
from http.server import HTTPServer
from server import VanadhikarAPIHandler, anomaly_engine, ai_engine
from database import get_db_connection, DB_FILE, init_db


class MockRequest:
    """Simulates a socket for BaseHTTPRequestHandler in-memory."""
    def __init__(self, request_bytes: bytes):
        self._rfile = io.BytesIO(request_bytes)
        self._wfile = io.BytesIO()

    def makefile(self, mode, *args, **kwargs):
        if "b" in mode:
            if "r" in mode:
                return self._rfile
            elif "w" in mode:
                return self._wfile
        raise ValueError("Only binary mode supported")

    def sendall(self, data):
        self._wfile.write(data)


def simulate_request(method: str, path: str, body: dict = None, headers: dict = None):
    """Invokes VanadhikarAPIHandler directly using in-memory streams."""
    req_body_bytes = json.dumps(body or {}).encode("utf-8") if body else b""
    header_lines = [
        f"{method} {path} HTTP/1.1",
        "Host: localhost",
        f"Content-Length: {len(req_body_bytes)}"
    ]
    if headers:
        for k, v in headers.items():
            header_lines.append(f"{k}: {v}")
    header_lines.append("")
    header_lines.append("")

    full_request = "\r\n".join(header_lines).encode("utf-8") + req_body_bytes
    mock_socket = MockRequest(full_request)

    handler = VanadhikarAPIHandler(mock_socket, ("127.0.0.1", 8000), None)
    mock_socket._wfile.seek(0)
    response_raw = mock_socket._wfile.read().decode("utf-8", errors="replace")

    # Parse status and body
    lines = response_raw.split("\r\n")
    status_line = lines[0]
    status_code = int(status_line.split(" ")[1])

    # Find blank line separating headers from body
    body_start_idx = response_raw.find("\r\n\r\n")
    body_text = response_raw[body_start_idx + 4:] if body_start_idx != -1 else ""

    try:
        json_data = json.loads(body_text)
    except Exception:
        json_data = body_text

    return status_code, json_data


def run_tests():
    print("==================================================")
    print("🌲 Starting Vanadhikar AI In-Process Test Suite...")
    print("==================================================")

    passed = 0
    total = 0

    def assert_test(condition, test_name):
        nonlocal passed, total
        total += 1
        if condition:
            print(f"  ✅ PASS: {test_name}")
            passed += 1
        else:
            print(f"  ❌ FAIL: {test_name}")
            raise AssertionError(f"Test failed: {test_name}")

    # Test 1: Health endpoint
    status, data = simulate_request("GET", "/health")
    assert_test(status == 200 and data.get("status") == "healthy", "GET /health responds with healthy status")

    # Test 2: WebGIS Districts GeoJSON
    status, data = simulate_request("GET", "/api/gis/districts")
    assert_test(status == 200 and data["type"] == "FeatureCollection", "GET /api/gis/districts returns valid GeoJSON FeatureCollection")
    assert_test(len(data["features"]) == 10, f"Returns all 10 monitored tribal districts (got {len(data['features'])})")
    sample_dist = data["features"][0]
    assert_test(sample_dist["geometry"]["type"] == "Polygon", "District geometry is a valid closed Polygon")
    assert_test("composite_risk_score" in sample_dist["properties"]["metrics"], "District contains composite risk score")

    # Test 3: WebGIS Claims GeoJSON
    status, data = simulate_request("GET", "/api/gis/claims?limit=25")
    assert_test(status == 200 and len(data["features"]) == 25, "GET /api/gis/claims returns paginated claims")
    sample_claim = data["features"][0]
    assert_test(sample_claim["geometry"]["type"] == "Point", "Claim geometry is valid Point coordinates")
    sample_claim_id = sample_claim["properties"]["claim_id"]

    # Test 4: WebGIS Claims Filter (Anomalies Only)
    status, data = simulate_request("GET", "/api/gis/claims?anomaly_only=true&limit=15")
    assert_test(status == 200 and all(f["properties"]["has_anomaly"] for f in data["features"]), "GET /api/gis/claims?anomaly_only=true isolates claims with anomalies")

    # Test 5: Forest Cover GeoJSON
    status, data = simulate_request("GET", "/api/gis/forest-cover")
    assert_test(status == 200 and len(data["features"]) == 30, f"GET /api/gis/forest-cover returns 30 forest compartments (got {len(data['features'])})")

    # Test 6: Claim Details
    status, data = simulate_request("GET", f"/api/gis/claim-details/{sample_claim_id}")
    assert_test(status == 200 and data["claim_id"] == sample_claim_id, f"GET /api/gis/claim-details/{sample_claim_id} returns record")
    assert_test("anomalies" in data, "Claim includes detected anomalies list")

    # Test 7: Anomalies Query & Severity Filtering
    status, data = simulate_request("GET", "/api/anomalies?severity=CRITICAL&limit=10")
    assert_test(status == 200 and len(data["anomalies"]) > 0, "GET /api/anomalies returns critical anomalies")
    assert_test(all(a["severity"] == "CRITICAL" for a in data["anomalies"]), "Filter correctly restricts to CRITICAL severity")

    # Test 8: Trigger AI Scan
    status, data = simulate_request("POST", "/api/anomalies/scan")
    assert_test(status == 200 and data["status"] == "success", "POST /api/anomalies/scan re-scans all claims")
    assert_test(data["scan_results"]["total_claims_scanned"] == 1200, "Scanned all 1,200 claims in database")

    # Test 9: State Overview Decision Panel
    status, data = simulate_request("GET", "/api/analytics/state-overview")
    assert_test(status == 200 and data["total_states"] == 5, f"GET /api/analytics/state-overview returns 5 states (got {data['total_states']})")
    assert_test(data["state_progress"][0]["conversion_rate"] >= 0, "State overview calculates title conversion rates")

    # Test 10: District KPIs
    status, data = simulate_request("GET", "/api/analytics/district-kpis/OD_MAY")
    assert_test(status == 200 and len(data["taluk_breakdown"]) > 0, "GET /api/analytics/district-kpis/OD_MAY includes taluk breakdown")
    assert_test(len(data["tribe_breakdown"]) > 0, "Includes tribal demographic distribution")

    # Test 11: Triage List
    status, data = simulate_request("GET", "/api/analytics/triage")
    assert_test(status == 200 and len(data["priority_action_list"]) > 0, "GET /api/analytics/triage returns priority action list")
    assert_test(data["priority_action_list"][0]["risk_score"] >= data["priority_action_list"][-1]["risk_score"], "Triage items correctly ordered by risk score descending")

    # Test 12: AI District Decision Dossier
    status, data = simulate_request("POST", "/api/ai/district-brief/OD_MAY")
    assert_test(status == 200 and "briefing_markdown" in data, "POST /api/ai/district-brief/OD_MAY generates executive briefing")
    assert_test("FRA" in data["briefing_markdown"] or "Forest Rights" in data["briefing_markdown"], "AI briefing cites Forest Rights Act legal provisions")

    # Test 13: AI Claim Diagnostic
    status, data = simulate_request("POST", f"/api/ai/analyze-claim/{sample_claim_id}")
    assert_test(status == 200 and "diagnostic_markdown" in data, "POST /api/ai/analyze-claim generates legal diagnostic")

    # Test 14: Export Summary JSON
    status, data = simulate_request("GET", "/api/export/summary?format=json")
    assert_test(status == 200 and len(data["exported_districts"]) == 10, "GET /api/export/summary exports all 10 districts")

    # Test 15: Export Summary CSV
    status, raw_csv = simulate_request("GET", "/api/export/summary?format=csv")
    assert_test(status == 200 and "district_code,district_name" in str(raw_csv), "GET /api/export/summary?format=csv exports valid CSV header")

    # Test 16: Frontend Index HTML Serving
    status, index_html = simulate_request("GET", "/")
    assert_test(status == 200 and "Vanadhikar AI" in str(index_html) and "three-canvas-container" in str(index_html), "GET / serves rich frontend/index.html")

    # Test 17: Stylesheet Serving
    status, styles = simulate_request("GET", "/styles.css")
    assert_test(status == 200 and "leaflet-container" in str(styles), "GET /styles.css serves styles.css correctly")

    # Test 18: 3D Terrain Engine JS Serving
    status, three_js = simulate_request("GET", "/three_terrain.js")
    assert_test(status == 200 and "FRA3DTerrainEngine" in str(three_js), "GET /three_terrain.js serves Three.js terrain engine")

    # Test 19: App Controller JS Serving
    status, app_js = simulate_request("GET", "/app.js")
    assert_test(status == 200 and "deckState" in str(app_js), "GET /app.js serves frontend controller script")

    print("==================================================")
    print(f"🎉 ALL {passed}/{total} VERIFICATION TESTS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    run_tests()
