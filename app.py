fromom flask import Flask, render_template, request, redirect, session, url_for, jsonify
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.secret_key = "viperaid_secret_key_123"

DB = "viperaid.db"


# ---------- DB HELPERS ----------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS reports (
        id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        animal_type TEXT NOT NULL,
        urgency TEXT NOT NULL,
        location_text TEXT NOT NULL,
        geo TEXT,
        description TEXT NOT NULL,
        reporter_name TEXT,
        reporter_phone TEXT,
        status TEXT NOT NULL DEFAULT 'Reported',
        decision TEXT NOT NULL DEFAULT 'Pending',   -- Pending/Accepted/Rejected
        assigned_to TEXT DEFAULT ''
    );
    """)
    conn.commit()
    conn.close()


# ---------- PUBLIC PAGES ----------
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/report")
def report_page():
    return render_template("report.html")


@app.route("/donate")
def donate():
    return render_template("donate.html")


@app.route("/about")
def about():
    return render_template("about.html")


# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login_citizen():
    if request.method == "POST":
        session["role"] = "citizen"
        session["name"] = request.form.get("name", "").strip()
        return redirect(url_for("home"))
    return render_template("login_citizen.html")


@app.route("/rescue-login", methods=["GET", "POST"])
def login_rescuer():
    if request.method == "POST":
        org = request.form.get("org", "").strip()
        code = request.form.get("code", "").strip()

        if code == "VIPERNGO":
            session["role"] = "rescuer"
            session["org"] = org
            return redirect(url_for("rescue"))  # ✅ goes to dashboard
        return render_template("login_rescuer.html", error="Invalid NGO access code")

    return render_template("login_rescuer.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------- PROTECTED DASHBOARD ----------
@app.route("/rescue")
def rescue():
    if session.get("role") != "rescuer":
        return redirect(url_for("login_rescuer"))
    return render_template("rescue.html")


# ---------- API: CREATE REPORT (from report.html) ----------
@app.route("/api/report", methods=["POST"])
def api_create_report():
    data = request.get_json(force=True)

    # Required fields
    animal_type = (data.get("animalType") or "").strip()
    urgency = (data.get("urgency") or "").strip()
    location_text = (data.get("locationText") or "").strip()
    description = (data.get("description") or "").strip()

    if not (animal_type and urgency and location_text and description):
        return jsonify({"ok": False, "error": "Missing required fields"}), 400

    report_id = "VA-" + str(int(datetime.utcnow().timestamp() * 1000))
    created_at = datetime.utcnow().isoformat(timespec="seconds") + "Z"

    geo = (data.get("geo") or "").strip()
    reporter_name = (data.get("reporterName") or "").strip()
    reporter_phone = (data.get("reporterPhone") or "").strip()

    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO reports (id, created_at, animal_type, urgency, location_text, geo, description, reporter_name, reporter_phone)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (report_id, created_at, animal_type, urgency, location_text, geo, description, reporter_name, reporter_phone))
    conn.commit()
    conn.close()

    return jsonify({"ok": True, "id": report_id})


# ---------- API: LIST REPORTS (for rescue dashboard) ----------
@app.route("/api/reports", methods=["GET"])
def api_list_reports():
    if session.get("role") != "rescuer":
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    conn = get_db()
    rows = conn.execute("SELECT * FROM reports ORDER BY created_at DESC").fetchall()
    conn.close()

    reports = [dict(r) for r in rows]
    return jsonify({"ok": True, "reports": reports})


# ---------- API: UPDATE STATUS / DECISION ----------
@app.route("/api/report/<report_id>/update", methods=["POST"])
def api_update_report(report_id):
    if session.get("role") != "rescuer":
        return jsonify({"ok": False, "error": "Unauthorized"}), 401

    data = request.get_json(force=True)
    status = (data.get("status") or "").strip()
    decision = (data.get("decision") or "").strip()
    assigned_to = (data.get("assignedTo") or "").strip()

    # allow only safe values
    allowed_status = {"Reported", "Accepted", "In Progress", "Completed"}
    allowed_decision = {"Pending", "Accepted", "Rejected"}

    if status and status not in allowed_status:
        return jsonify({"ok": False, "error": "Invalid status"}), 400
    if decision and decision not in allowed_decision:
        return jsonify({"ok": False, "error": "Invalid decision"}), 400

    conn = get_db()
    cur = conn.cursor()

    # Build dynamic update
    fields = []
    params = []

    if status:
        fields.append("status=?")
        params.append(status)
    if decision:
        fields.append("decision=?")
        params.append(decision)
    if assigned_to is not None:
        fields.append("assigned_to=?")
        params.append(assigned_to)

    if not fields:
        return jsonify({"ok": False, "error": "Nothing to update"}), 400

    params.append(report_id)
    cur.execute(f"UPDATE reports SET {', '.join(fields)} WHERE id=?", params)
    conn.commit()
    conn.close()

    return jsonify({"ok": True})


if __name__ == "__main__":
    init_db()
    app.run(debug=True)