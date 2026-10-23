
from flask import Flask, render_template, request, jsonify
import sqlite3
import os
from pathlib import Path

app = Flask(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "findmychild.db"


# ---------------- DATABASE ----------------

def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS missing_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                label TEXT NOT NULL,
                age INTEGER NOT NULL,
                district TEXT NOT NULL,
                report_date TEXT NOT NULL,
                details TEXT DEFAULT ''
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS found_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                age INTEGER NOT NULL,
                district TEXT NOT NULL,
                report_date TEXT NOT NULL,
                details TEXT DEFAULT ''
            )
        """)


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- CREATE MISSING REPORT ----------------

@app.route("/api/missing", methods=["POST"])
def create_missing_report():
    data = request.get_json(silent=True) or {}

    label = str(data.get("label", "")).strip()
    district = str(data.get("district", "")).strip()
    report_date = str(data.get("date", "")).strip()
    details = str(data.get("details", "")).strip()

    try:
        age = int(data.get("age"))
    except (TypeError, ValueError):
        return jsonify({"error": "Age must be a whole number."}), 400

    if not label or not district or not report_date:
        return jsonify({"error": "Required fields are missing."}), 400

    if not 0 <= age <= 17:
        return jsonify({"error": "Age must be between 0 and 17."}), 400

    if len(label) > 80 or len(district) > 80 or len(details) > 500:
        return jsonify({"error": "One or more fields are too long."}), 400

    with get_db() as db:
        cursor = db.execute("""
            INSERT INTO missing_reports
            (label, age, district, report_date, details)
            VALUES (?, ?, ?, ?, ?)
        """, (label, age, district, report_date, details))

        report_id = cursor.lastrowid

    return jsonify({
        "message": "Missing demo report saved.",
        "id": report_id
    }), 201


# ---------------- CREATE FOUND REPORT ----------------

@app.route("/api/found", methods=["POST"])
def create_found_report():
    data = request.get_json(silent=True) or {}

    district = str(data.get("district", "")).strip()
    report_date = str(data.get("date", "")).strip()
    details = str(data.get("details", "")).strip()

    try:
        age = int(data.get("age"))
    except (TypeError, ValueError):
        return jsonify({"error": "Age must be a whole number."}), 400

    if not district or not report_date:
        return jsonify({"error": "Required fields are missing."}), 400

    if not 0 <= age <= 17:
        return jsonify({"error": "Age must be between 0 and 17."}), 400

    if len(district) > 80 or len(details) > 500:
        return jsonify({"error": "One or more fields are too long."}), 400

    with get_db() as db:
        cursor = db.execute("""
            INSERT INTO found_reports
            (age, district, report_date, details)
            VALUES (?, ?, ?, ?)
        """, (age, district, report_date, details))

        report_id = cursor.lastrowid

    return jsonify({
        "message": "Found demo report saved.",
        "id": report_id
    }), 201


# ---------------- POSSIBLE MATCHES ----------------

@app.route("/api/matches")
def possible_matches():
    with get_db() as db:
        rows = db.execute("""
            SELECT
                m.id AS missing_id,
                m.label,
                m.age,
                m.district,
                f.id AS found_id,
                f.report_date AS found_date
            FROM missing_reports AS m
            JOIN found_reports AS f
              ON m.age = f.age
             AND LOWER(TRIM(m.district)) =
                 LOWER(TRIM(f.district))
            ORDER BY m.id DESC
        """).fetchall()

    matches = [dict(row) for row in rows]

    return jsonify({
        "matches": matches,
        "count": len(matches),
        "notice": (
            "Potential matches only. "
            "Identity must not be inferred from this result."
        )
    })


# ---------------- DASHBOARD ----------------

@app.route("/api/dashboard")
def dashboard():
    with get_db() as db:
        missing_count = db.execute(
            "SELECT COUNT(*) FROM missing_reports"
        ).fetchone()[0]

        found_count = db.execute(
            "SELECT COUNT(*) FROM found_reports"
        ).fetchone()[0]

        match_count = db.execute("""
            SELECT COUNT(*)
            FROM missing_reports m
            JOIN found_reports f
              ON m.age = f.age
             AND LOWER(TRIM(m.district)) =
                 LOWER(TRIM(f.district))
        """).fetchone()[0]

    return jsonify({
        "missing": missing_count,
        "found": found_count,
        "matches": match_count
    })


# ---------------- RUN APPLICATION ----------------

if __name__ == "__main__":
    initialize_database()
    app.run(debug=True)
