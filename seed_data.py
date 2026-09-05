"""
Vanadhikar AI - Realistic Geospatial & FRA Claims Data Seeder
Generates 1,000+ realistic claims across key tribal districts in India,
along with GeoJSON district polygons, forest compartments, and realistic anomaly patterns.
"""

import math
import random
import json
import sqlite3
from datetime import datetime, timedelta
from database import get_db_connection, init_db

# Set seed for reproducible demo data
random.seed(42)

DISTRICTS_DATA = [
    {
        "district_code": "OD_MAY",
        "district_name": "Mayurbhanj",
        "state": "Odisha",
        "tribal_population_pct": 58.7,
        "forest_cover_sqkm": 4011.0,
        "center_lat": 21.93,
        "center_lng": 86.44,
        "radius_deg": 0.45,
        "tribes": ["Santhal", "Kolha", "Munda", "Lodha", "Mankirdia (PVTG)"],
        "taluks": ["Baripada", "Rairangpur", "Karanjia", "Udala", "Bangiriposi"]
    },
    {
        "district_code": "OD_RAY",
        "district_name": "Rayagada",
        "state": "Odisha",
        "tribal_population_pct": 56.0,
        "forest_cover_sqkm": 3218.0,
        "center_lat": 19.17,
        "center_lng": 83.41,
        "radius_deg": 0.40,
        "tribes": ["Dongria Kondh (PVTG)", "Kutia Kondh (PVTG)", "Saora", "Kandha"],
        "taluks": ["Rayagada", "Gunupur", "Bissam Cuttack", "Muniguda", "Kalyansinghpur"]
    },
    {
        "district_code": "OD_SUN",
        "district_name": "Sundargarh",
        "state": "Odisha",
        "tribal_population_pct": 50.7,
        "forest_cover_sqkm": 3530.0,
        "center_lat": 22.12,
        "center_lng": 84.03,
        "radius_deg": 0.42,
        "tribes": ["Oraon", "Munda", "Kisan", "Kharia"],
        "taluks": ["Sundargarh", "Panposh", "Bonai", "Rajgangpur", "Lathikata"]
    },
    {
        "district_code": "MP_DIN",
        "district_name": "Dindori",
        "state": "Madhya Pradesh",
        "tribal_population_pct": 64.7,
        "forest_cover_sqkm": 3020.0,
        "center_lat": 22.95,
        "center_lng": 81.08,
        "radius_deg": 0.38,
        "tribes": ["Baiga (PVTG)", "Gond", "Pradhan"],
        "taluks": ["Dindori", "Shahpura", "Bajag", "Karanjiya", "Samnapur"]
    },
    {
        "district_code": "MP_MAN",
        "district_name": "Mandla",
        "state": "Madhya Pradesh",
        "tribal_population_pct": 57.9,
        "forest_cover_sqkm": 2854.0,
        "center_lat": 22.60,
        "center_lng": 80.37,
        "radius_deg": 0.36,
        "tribes": ["Gond", "Baiga (PVTG)", "Kol"],
        "taluks": ["Mandla", "Nainpur", "Bichhiya", "Ghughri", "Niwas"]
    },
    {
        "district_code": "MP_BAL",
        "district_name": "Balaghat",
        "state": "Madhya Pradesh",
        "tribal_population_pct": 52.4,
        "forest_cover_sqkm": 4960.0,
        "center_lat": 21.81,
        "center_lng": 80.18,
        "radius_deg": 0.42,
        "tribes": ["Gond", "Baiga (PVTG)", "Halba"],
        "taluks": ["Balaghat", "Baihar", "Waraseoni", "Paraswada", "Katangi"]
    },
    {
        "district_code": "CG_BAS",
        "district_name": "Bastar",
        "state": "Chhattisgarh",
        "tribal_population_pct": 66.3,
        "forest_cover_sqkm": 3315.0,
        "center_lat": 19.07,
        "center_lng": 82.03,
        "radius_deg": 0.40,
        "tribes": ["Muria Gond", "Maria Gond", "Dhurwa", "Bhatra", "Halba"],
        "taluks": ["Jagdalpur", "Bastanar", "Tokapal", "Lohandiguda", "Bakawand"]
    },
    {
        "district_code": "CG_SUR",
        "district_name": "Surguja",
        "state": "Chhattisgarh",
        "tribal_population_pct": 55.1,
        "forest_cover_sqkm": 3950.0,
        "center_lat": 23.12,
        "center_lng": 83.20,
        "radius_deg": 0.42,
        "tribes": ["Pahadi Korwa (PVTG)", "Birhor (PVTG)", "Oraon", "Gond", "Kanwar"],
        "taluks": ["Ambikapur", "Sitapur", "Mainpat", "Lundra", "Batoli"]
    },
    {
        "district_code": "MH_GAD",
        "district_name": "Gadchiroli",
        "state": "Maharashtra",
        "tribal_population_pct": 38.7,
        "forest_cover_sqkm": 9996.0,
        "center_lat": 20.18,
        "center_lng": 80.00,
        "radius_deg": 0.55,
        "tribes": ["Madia Gond (PVTG)", "Koya", "Pradhan", "Halba"],
        "taluks": ["Gadchiroli", "Dhanora", "Kurkheda", "Etapalli", "Bhamragad", "Aheri"]
    },
    {
        "district_code": "JH_WSB",
        "district_name": "West Singhbhum",
        "state": "Jharkhand",
        "tribal_population_pct": 67.3,
        "forest_cover_sqkm": 3840.0,
        "center_lat": 22.57,
        "center_lng": 85.81,
        "radius_deg": 0.44,
        "tribes": ["Ho", "Munda", "Santhal", "Birhor (PVTG)", "Oraon"],
        "taluks": ["Chaibasa", "Chakradharpur", "Jagannathpur", "Manoharpur", "Noamundi"]
    }
]

PVTG_COMMUNITIES = [
    "Baiga (PVTG)", "Dongria Kondh (PVTG)", "Kutia Kondh (PVTG)",
    "Pahadi Korwa (PVTG)", "Birhor (PVTG)", "Madia Gond (PVTG)", "Mankirdia (PVTG)"
]

FIRST_NAMES = [
    "Budhu", "Sukru", "Mangal", "Lachhu", "Sombari", "Rameshwar", "Birsa", "Manki",
    "Somra", "Kamla", "Shanti", "Muni", "Ghanshyam", "Bhikari", "Gurubari", "Dhanu",
    "Chaitan", "Jogi", "Tulsi", "Phulo", "Jano", "Mangli", "Shyamlal", "Devsingh",
    "Pandu", "Balki", "Govind", "Rambati", "Moti", "Chamra", "Charan", "Maina"
]

SURNAMES = [
    "Murmu", "Soren", "Hembram", "Marndi", "Tudu", "Baiga", "Gond", "Markam",
    "Netam", "Korram", "Kondh", "Dora", "Majhi", "Kunkal", "Bhengra", "Tigga",
    "Tete", "Kerketta", "Pahan", "Oraon", "Munda", "Ho", "Soy", "Purty"
]


def generate_polygon(center_lat: float, center_lng: float, radius: float, num_points: int = 8) -> dict:
    """Generates a realistic closed GeoJSON Polygon around a center point with natural variations."""
    coords = []
    angle_step = (2 * math.pi) / num_points
    for i in range(num_points):
        angle = i * angle_step
        # Add jitter
        r = radius * random.uniform(0.82, 1.18)
        lat = center_lat + (r * math.sin(angle))
        # Longitude adjustment for latitude distortion
        lng = center_lng + (r * math.cos(angle) / math.cos(math.radians(center_lat)))
        coords.append([round(lng, 5), round(lat, 5)])
    # Close polygon
    coords.append(coords[0])
    return {
        "type": "Polygon",
        "coordinates": [coords]
    }


def seed_database():
    """Populates SQLite with realistic districts, forest compartments, claims, and anomalies."""
    init_db()
    conn = get_db_connection()
    cursor = conn.cursor()

    # Clear existing data for fresh seed
    cursor.execute("DELETE FROM ai_briefings;")
    cursor.execute("DELETE FROM anomalies;")
    cursor.execute("DELETE FROM claims;")
    cursor.execute("DELETE FROM forest_compartments;")
    cursor.execute("DELETE FROM districts;")
    conn.commit()

    print("Seeding Districts...")
    compartments_pool = []

    for d in DISTRICTS_DATA:
        boundary = generate_polygon(d["center_lat"], d["center_lng"], d["radius_deg"], num_points=12)
        cursor.execute("""
            INSERT INTO districts (district_code, district_name, state, tribal_population_pct, forest_cover_sqkm, center_lat, center_lng, boundary_geojson)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d["district_code"],
            d["district_name"],
            d["state"],
            d["tribal_population_pct"],
            d["forest_cover_sqkm"],
            d["center_lat"],
            d["center_lng"],
            json.dumps(boundary)
        ))

        # Generate 2-3 Forest Compartments per district
        forest_types = ["Reserved Forest (RF)", "Protected Forest (PF)", "Wildlife Sanctuary Buffer"]
        for comp_idx in range(1, 4):
            comp_id = f"FC_{d['district_code']}_{comp_idx:02d}"
            comp_name = f"{d['district_name']} Sector-{comp_idx} {forest_types[comp_idx-1]}"
            comp_lat = d["center_lat"] + random.uniform(-0.15, 0.15)
            comp_lng = d["center_lng"] + random.uniform(-0.15, 0.15)
            comp_boundary = generate_polygon(comp_lat, comp_lng, d["radius_deg"] * 0.35, num_points=8)
            comp_area = round(random.uniform(1200.0, 4800.0), 2)
            canopy = round(random.uniform(45.0, 88.0), 1)

            cursor.execute("""
                INSERT INTO forest_compartments (compartment_id, district_code, compartment_name, forest_type, recorded_area_ha, canopy_density_pct, boundary_geojson)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                comp_id,
                d["district_code"],
                comp_name,
                forest_types[comp_idx-1],
                comp_area,
                canopy,
                json.dumps(comp_boundary)
            ))
            compartments_pool.append({
                "compartment_id": comp_id,
                "district_code": d["district_code"],
                "center_lat": comp_lat,
                "center_lng": comp_lng
            })

    conn.commit()
    print(f"Districts and {len(compartments_pool)} Forest Compartments created.")

    print("Generating 1,200+ FRA Claims across districts...")
    total_claims = 1200
    claims_per_district = total_claims // len(DISTRICTS_DATA)

    all_claims = []
    anomaly_records = []
    base_date = datetime(2023, 1, 15)

    claim_counter = 1

    for d in DISTRICTS_DATA:
        dist_compartments = [c for c in compartments_pool if c["district_code"] == d["district_code"]]

        for i in range(claims_per_district):
            claim_id = f"FRA-{d['state'][:2].upper()}-{d['district_code'].split('_')[1]}-2024-{claim_counter:04d}"
            claim_counter += 1

            # Claimant details
            first_name = random.choice(FIRST_NAMES)
            last_name = random.choice(SURNAMES)
            claimant_name = f"{first_name} {last_name}"

            tribe = random.choice(d["tribes"])
            is_pvtg = 1 if "(PVTG)" in tribe else 0

            taluk = random.choice(d["taluks"])
            gram_panchayat = f"{taluk} GP-{random.randint(1, 15)}"
            village = f"Gram {first_name}pur-{random.randint(1, 25)}"

            # Claimant Type: 80% IFR, 15% CFR, 5% CFRR
            type_roll = random.random()
            if type_roll < 0.80:
                claimant_type = "IFR"
                # FRA Sec 4(6) cap is 4.0 Ha. Usually 0.4 to 3.5 ha
                # Introduce deliberate anomaly: 5% exceed 4.0 ha statutory cap!
                if random.random() < 0.05:
                    claimed_area = round(random.uniform(4.2, 8.5), 2)  # Cap violation anomaly!
                else:
                    claimed_area = round(random.uniform(0.45, 3.80), 2)
            elif type_roll < 0.95:
                claimant_type = "CFR"
                claimed_area = round(random.uniform(25.0, 650.0), 2)
                claimant_name = f"{village} Gram Sabha Committee"
            else:
                claimant_type = "CFRR"
                claimed_area = round(random.uniform(50.0, 950.0), 2)
                claimant_name = f"{taluk} Forest Dwellers Collective"

            # Submission and processing dates
            days_ago = random.randint(30, 650)
            submission_dt = datetime.now() - timedelta(days=days_ago)
            submission_str = submission_dt.strftime("%Y-%m-%d")

            # Geographic Location
            # 85% inside valid forest compartment; 15% outside / boundary anomaly
            is_boundary_mismatch = (random.random() < 0.08)
            if dist_compartments and not is_boundary_mismatch:
                comp = random.choice(dist_compartments)
                comp_id = comp["compartment_id"]
                lat = comp["center_lat"] + random.uniform(-0.06, 0.06)
                lng = comp["center_lng"] + random.uniform(-0.06, 0.06)
            else:
                comp_id = None
                # Outlier or unclassified revenue land
                lat = d["center_lat"] + random.uniform(-d["radius_deg"] * 0.95, d["radius_deg"] * 0.95)
                lng = d["center_lng"] + random.uniform(-d["radius_deg"] * 0.95, d["radius_deg"] * 0.95)

            # Claim geometry (Point + small envelope polygon)
            point_geom = {
                "type": "Point",
                "coordinates": [round(lng, 5), round(lat, 5)]
            }

            # Claim Progression Status
            # Roll for status progression
            status_roll = random.random()
            gs_date = None
            sdlc_date = None
            dlc_date = None
            rejection_reason = None
            approved_area = 0.0
            delay_days = 0

            # Statutory delay check: under FRA Rules, SDLC must verify in 60-90 days
            # Introduce deliberate statutory delay anomalies (claims stuck for 180+ days)
            is_delayed = (days_ago > 180 and random.random() < 0.35)

            if status_roll < 0.15:
                status = "SUBMITTED"
                if days_ago > 90:
                    delay_days = days_ago - 90
            elif status_roll < 0.32:
                status = "GS_VERIFIED"
                gs_date = (submission_dt + timedelta(days=random.randint(15, 45))).strftime("%Y-%m-%d")
                if days_ago > 120:
                    delay_days = days_ago - 120
            elif status_roll < 0.52:
                status = "SDLC_REVIEW"
                gs_date = (submission_dt + timedelta(days=random.randint(15, 30))).strftime("%Y-%m-%d")
                sdlc_date = (submission_dt + timedelta(days=random.randint(45, 90))).strftime("%Y-%m-%d")
                if days_ago > 150:
                    delay_days = days_ago - 150
            elif status_roll < 0.65:
                # REJECTED (deliberate real-world FRA rejection grounds)
                status = "REJECTED"
                gs_date = (submission_dt + timedelta(days=20)).strftime("%Y-%m-%d")
                sdlc_date = (submission_dt + timedelta(days=60)).strftime("%Y-%m-%d")
                rejection_reasons = [
                    "Lack of 75-year OTFD continuous occupation evidence under Rule 11",
                    "Claimed land claimed as Reserve Forest with pending Supreme Court WP 109/2008",
                    "Discrepancy between Gram Sabha recommendation and joint verification sketch",
                    "Unreasoned rejection by DLC (FRA Rule 12A(6) procedural non-compliance)",
                    "Area claimed falls under Tiger Corridor / Wildlife Protection Act zone"
                ]
                rejection_reason = random.choice(rejection_reasons)
                approved_area = 0.0
            elif status_roll < 0.82:
                status = "DLC_APPROVED"
                gs_date = (submission_dt + timedelta(days=25)).strftime("%Y-%m-%d")
                sdlc_date = (submission_dt + timedelta(days=70)).strftime("%Y-%m-%d")
                dlc_date = (submission_dt + timedelta(days=120)).strftime("%Y-%m-%d")
                approved_area = round(claimed_area * random.uniform(0.85, 1.0), 2)
            else:
                status = "TITLE_ISSUED"
                gs_date = (submission_dt + timedelta(days=20)).strftime("%Y-%m-%d")
                sdlc_date = (submission_dt + timedelta(days=55)).strftime("%Y-%m-%d")
                dlc_date = (submission_dt + timedelta(days=95)).strftime("%Y-%m-%d")
                approved_area = claimed_area

            # If delayed flag is triggered artificially
            if is_delayed and status in ("SUBMITTED", "GS_VERIFIED", "SDLC_REVIEW"):
                delay_days = max(delay_days, days_ago - 75)

            cursor.execute("""
                INSERT INTO claims (
                    claim_id, claimant_name, claimant_type, tribe_name, is_pvtg,
                    state, district_code, taluk_block, gram_panchayat, village,
                    claim_date, status, claimed_area_ha, approved_area_ha,
                    forest_compartment_id, latitude, longitude, geometry_geojson,
                    submission_timestamp, gs_verification_date, sdlc_review_date,
                    dlc_approval_date, rejection_reason, documents_verified,
                    land_mismatch_flag, delay_days
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                claim_id, claimant_name, claimant_type, tribe_name if 'tribe_name' in locals() else tribe,
                is_pvtg, d["state"], d["district_code"], taluk, gram_panchayat, village,
                submission_str, status, claimed_area, approved_area, comp_id,
                round(lat, 5), round(lng, 5), json.dumps(point_geom),
                submission_dt.isoformat(), gs_date, sdlc_date, dlc_date,
                rejection_reason, 1 if status != "REJECTED" else 0,
                1 if is_boundary_mismatch else 0, delay_days
            ))

            # Proactively register known anomalies in anomalies table
            # 1. Statutory timeline delay anomaly
            if delay_days > 90 and status not in ("TITLE_ISSUED", "REJECTED"):
                anom_id = f"ANOM-DELAY-{claim_id}"
                severity = "CRITICAL" if delay_days > 240 else ("HIGH" if delay_days > 150 else "MEDIUM")
                risk_score = min(98, 40 + int(delay_days / 6))
                cursor.execute("""
                    INSERT OR REPLACE INTO anomalies (
                        anomaly_id, claim_id, district_code, anomaly_type, severity,
                        risk_score, title, description, rule_reference, detected_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'OPEN')
                """, (
                    anom_id, claim_id, d["district_code"],
                    "STATUTORY_TIMELINE_DELAY",
                    severity,
                    risk_score,
                    f"Statutory Delay of {delay_days} days at {status} stage",
                    f"Claim filed by {claimant_name} ({tribe}) has been stalled for {delay_days} days beyond statutory window.",
                    "FRA Amendment Rules 2012 Rule 12A(3) - Disposal within 60 days"
                ))

            # 2. Area Cap Violation Anomaly (> 4.0 Ha for IFR)
            if claimant_type == "IFR" and claimed_area > 4.0:
                anom_id = f"ANOM-AREACAP-{claim_id}"
                cursor.execute("""
                    INSERT OR REPLACE INTO anomalies (
                        anomaly_id, claim_id, district_code, anomaly_type, severity,
                        risk_score, title, description, rule_reference, detected_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'OPEN')
                """, (
                    anom_id, claim_id, d["district_code"],
                    "STATUTORY_AREA_CAP_EXCEEDED",
                    "CRITICAL",
                    95,
                    f"Statutory Cap Exceeded: {claimed_area} Ha claimed (Limit 4.0 Ha)",
                    f"Individual claim by {claimant_name} claims {claimed_area} Ha, which exceeds the absolute 4-hectare statutory ceiling mandated under FRA Section 4(6).",
                    "Forest Rights Act 2006, Section 4(6) - Maximum land ceiling of 4 hectares"
                ))

            # 3. Forest Boundary / Cadastral Mismatch Anomaly
            if is_boundary_mismatch:
                anom_id = f"ANOM-CAD-{claim_id}"
                cursor.execute("""
                    INSERT OR REPLACE INTO anomalies (
                        anomaly_id, claim_id, district_code, anomaly_type, severity,
                        risk_score, title, description, rule_reference, detected_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'OPEN')
                """, (
                    anom_id, claim_id, d["district_code"],
                    "FOREST_RECORD_MISMATCH",
                    "HIGH",
                    82,
                    "Cadastral Record Mismatch: Coordinates fall outside forest boundary",
                    f"Claim coordinates [{round(lat, 4)}, {round(lng, 4)}] do not intersect registered forest compartment cadastre in Bhuvan layers.",
                    "FRA 2006 Section 2(d) & MoTA Verification Guidelines"
                ))

            # 4. Unreasoned DLC Rejection Anomaly
            if status == "REJECTED" and "Unreasoned rejection" in (rejection_reason or ""):
                anom_id = f"ANOM-REJ-{claim_id}"
                cursor.execute("""
                    INSERT OR REPLACE INTO anomalies (
                        anomaly_id, claim_id, district_code, anomaly_type, severity,
                        risk_score, title, description, rule_reference, detected_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'OPEN')
                """, (
                    anom_id, claim_id, d["district_code"],
                    "DISPROPORTIONATE_REJECTION",
                    "HIGH",
                    88,
                    "Procedural Non-Compliance: DLC Rejection without recorded grounds",
                    f"Claim of {claimant_name} ({tribe}) was dismissed by District Level Committee without providing written reasons or referral back to Gram Sabha.",
                    "FRA Rules 2012 Rule 12A(6) - Mandatory recording of rejection reasons in writing"
                ))

            # 5. PVTG Delay Bottleneck Anomaly
            if is_pvtg and status in ("SUBMITTED", "GS_VERIFIED") and days_ago > 120:
                anom_id = f"ANOM-PVTG-{claim_id}"
                cursor.execute("""
                    INSERT OR REPLACE INTO anomalies (
                        anomaly_id, claim_id, district_code, anomaly_type, severity,
                        risk_score, title, description, rule_reference, detected_at, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, 'OPEN')
                """, (
                    anom_id, claim_id, d["district_code"],
                    "PVTG_PENDENCY_BOTTLENECK",
                    "CRITICAL",
                    94,
                    f"Vulnerable Tribal Group Claim Stalled: {tribe}",
                    f"Particularly Vulnerable Tribal Group ({tribe}) claim pending for {days_ago} days. National directives mandate expedited disposal for PVTG habitats.",
                    "MoTA Special Guidelines for PVTG Rights under FRA Sec 3(1)(e)"
                ))

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM claims;")
    claim_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM anomalies;")
    anomaly_count = cursor.fetchone()[0]

    print(f"Seeding completed successfully!")
    print(f"Total Claims: {claim_count}")
    print(f"Total Anomalies flagged: {anomaly_count}")
    conn.close()


if __name__ == "__main__":
    seed_database()
