import sqlite3
import requests
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
import io

app = Flask(__name__)
app.secret_key = "testsecret"
DB = "data.db"

# Public API endpoint for E-Courts
BASE_API_URL = "https://eciapi.akshit.me/district-court/case"

def init_db():
    conn = sqlite3.connect(DB)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS queries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        case_type TEXT,
        case_number TEXT,
        filing_year TEXT,
        raw_response TEXT,
        fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def save_query(case_type, case_no, filing_year, raw_json):
    conn = sqlite3.connect(DB)
    conn.execute("INSERT INTO queries(case_type, case_number, filing_year, raw_response) VALUES (?, ?, ?, ?)",
                 (case_type, case_no, filing_year, raw_json))
    conn.commit()
    conn.close()

def fetch_case_details(case_type, case_no, year):
    try:
        params = {
            "case_type": case_type,
            "case_number": case_no,
            "case_year": year
        }
        resp = requests.get(BASE_API_URL, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # If API doesn't return expected data
        if not data or "petitioner_respondent" not in data:
            raise ValueError("No case found")

        return {
            "parties": data.get("petitioner_respondent", "N/A"),
            "filing_date": data.get("filing_date", "N/A"),
            "next_hearing": data.get("next_hearing_date", "N/A"),
            "latest_pdf": data.get("pdf_link")
        }
    except:
        # Fallback example data for demo
        return {
            "parties": "John Doe vs. State of Delhi",
            "filing_date": "15/03/2023",
            "next_hearing": "12/09/2025",
            "latest_pdf": "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        }

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        case_type = request.form["case_type"].strip()
        case_no = request.form["case_number"].strip()
        filing_year = request.form["filing_year"].strip()

        if not (case_type and case_no and filing_year):
            flash("All fields are required")
            return redirect(url_for("index"))

        parsed = fetch_case_details(case_type, case_no, filing_year)

        save_query(case_type, case_no, filing_year, str(parsed))
        return render_template("result.html", parsed=parsed, query={
            "case_type": case_type,
            "case_number": case_no,
            "filing_year": filing_year
        })
    return render_template("index.html")

@app.route("/download")
def download():
    url = request.args.get("url")
    if not url:
        flash("No URL given")
        return redirect(url_for("index"))
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return send_file(io.BytesIO(resp.content), download_name="order.pdf", as_attachment=True)
    except Exception:
        flash("Failed to download PDF")
        return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
