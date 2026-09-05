"""
Vanadhikar AI - Database Module
Provides SQLite database connection management, table schemas, and helper queries.
"""

import sqlite3
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

DB_FILE = Path(__file__).resolve().parent / "vanadhikar.db"


def get_db_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with row factory enabled."""
    path = db_path or str(DB_FILE)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: Optional[str] = None) -> None:
    """Initializes all required tables for Vanadhikar AI."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 1. Districts table (Geospatial polygons + administrative baseline)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS districts (
            district_code TEXT PRIMARY KEY,
            district_name TEXT NOT NULL,
            state TEXT NOT NULL,
            tribal_population_pct REAL DEFAULT 0.0,
            forest_cover_sqkm REAL DEFAULT 0.0,
            center_lat REAL NOT NULL,
            center_lng REAL NOT NULL,
            boundary_geojson TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # 2. Forest Compartments / Cadastral baseline (from Bhuvan/ISRO forest layers)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS forest_compartments (
            compartment_id TEXT PRIMARY KEY,
            district_code TEXT NOT NULL,
            compartment_name TEXT NOT NULL,
            forest_type TEXT NOT NULL,
            recorded_area_ha REAL NOT NULL,
            canopy_density_pct REAL DEFAULT 60.0,
            boundary_geojson TEXT NOT NULL,
            FOREIGN KEY (district_code) REFERENCES districts(district_code) ON DELETE CASCADE
        );
    """)

    # 3. FRA Claims Table (IFR, CFR, CFRR)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            claim_id TEXT PRIMARY KEY,
            claimant_name TEXT NOT NULL,
            claimant_type TEXT NOT NULL CHECK(claimant_type IN ('IFR', 'CFR', 'CFRR')),
            tribe_name TEXT NOT NULL,
            is_pvtg INTEGER DEFAULT 0 CHECK(is_pvtg IN (0, 1)),
            state TEXT NOT NULL,
            district_code TEXT NOT NULL,
            taluk_block TEXT NOT NULL,
            gram_panchayat TEXT NOT NULL,
            village TEXT NOT NULL,
            claim_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('SUBMITTED', 'GS_VERIFIED', 'SDLC_REVIEW', 'DLC_APPROVED', 'REJECTED', 'TITLE_ISSUED')),
            claimed_area_ha REAL NOT NULL,
            approved_area_ha REAL DEFAULT 0.0,
            forest_compartment_id TEXT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            geometry_geojson TEXT NOT NULL,
            submission_timestamp TEXT NOT NULL,
            gs_verification_date TEXT,
            sdlc_review_date TEXT,
            dlc_approval_date TEXT,
            rejection_reason TEXT,
            documents_verified INTEGER DEFAULT 1,
            land_mismatch_flag INTEGER DEFAULT 0,
            delay_days INTEGER DEFAULT 0,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (district_code) REFERENCES districts(district_code) ON DELETE CASCADE,
            FOREIGN KEY (forest_compartment_id) REFERENCES forest_compartments(compartment_id)
        );
    """)

    # 4. AI Detected Anomalies Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS anomalies (
            anomaly_id TEXT PRIMARY KEY,
            claim_id TEXT,
            district_code TEXT NOT NULL,
            anomaly_type TEXT NOT NULL,
            severity TEXT NOT NULL CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
            risk_score INTEGER NOT NULL CHECK(risk_score BETWEEN 0 AND 100),
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            rule_reference TEXT NOT NULL,
            detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'OPEN' CHECK(status IN ('OPEN', 'UNDER_REVIEW', 'RESOLVED')),
            resolution_notes TEXT,
            FOREIGN KEY (claim_id) REFERENCES claims(claim_id) ON DELETE CASCADE,
            FOREIGN KEY (district_code) REFERENCES districts(district_code) ON DELETE CASCADE
        );
    """)

    # 5. AI Generated Executive Briefings & Decision Dossiers
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ai_briefings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL CHECK(entity_type IN ('DISTRICT', 'CLAIM', 'STATE')),
            entity_code TEXT NOT NULL,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary_text TEXT NOT NULL,
            legal_citations TEXT NOT NULL,
            recommended_actions TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            model_used TEXT NOT NULL
        );
    """)

    # Indices for blazing fast GIS & status queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_district ON claims(district_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_type ON claims(claimant_type);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_claims_pvtg ON claims(is_pvtg);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_district ON anomalies(district_code);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_anomalies_type ON anomalies(anomaly_type);")

    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print(f"Vanadhikar AI database initialized successfully at {DB_FILE}")
