import os
import re
import psycopg2
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime

app = Flask(__name__)

# Detect environment and configure the database URL
if os.getenv("RENDER_ENV"):
    # Running on Render, use the provided DATABASE_URL
    DATABASE_URL = os.getenv("DATABASE_URL")
else:
    # Running locally, use local PostgreSQL
    DATABASE_URL = "postgresql://flask_user:Psico123@localhost:5432/flask_pub"

# Function to connect to the database
def get_db_connection():
    return psycopg2.connect(DATABASE_URL)

# Initialize the database table
def initialize_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS publications (
                        id SERIAL PRIMARY KEY,
                        title TEXT NOT NULL,
                        type TEXT NOT NULL,
                        project TEXT,
                        journal TEXT,
                        authors TEXT,
                        submission_date DATE,
                        status TEXT,
                        observation TEXT
                    );
                """)
                conn.commit()
                print("Database initialized successfully.")
    except psycopg2.Error as e:
        print(f"Database initialization error: {e}")
        raise

STATUS_CHOICES = [
    "In preparation", "Waiting for submission", "Submitted",
    "Under review", "Changes needed", "Resubmitted",
    "Rejected", "Accepted", "Published"
]

# Helper function to parse dates safely
def parse_date(date_string):
    if date_string:
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except ValueError:
            return None
    return None

# Helper function to make links clickable in the observation field
def make_links_clickable(observation):
    if not isinstance(observation, str):
        return observation  # If it's not a string, return as-is

    # Regex to find URLs
    url_pattern = r'(https?://\S+|www\.\S+)'

    # Replace the match with an HTML <a> tag
    def replace_with_link(match):
        url = match.group(0)
        # Add http:// if the URL starts with www.
        if url.startswith("www."):
            url = f"http://{url}"
        return f"<a href='{url}' target='_blank' style='color: blue; text-decoration: underline;'>click here</a>"

    return re.sub(url_pattern, replace_with_link, observation)

# Route: Index
@app.route("/")
def index():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM publications ORDER BY id;")
            publications = cur.fetchall()

    # Make observation links clickable
    publications = [
        (
            pub[0], pub[1], pub[2], pub[3], pub[4], pub[5],
            pub[6], pub[7], make_links_clickable(pub[8])
        )
        for pub in publications
    ]

    return render_template("index.html", publications=publications, statuses=STATUS_CHOICES)

# Route: Add or Update Publication
@app.route("/add_update", methods=["POST"])
def add_update():
    data = {
        'id': request.form.get("id"),
        'title': request.form.get("title"),
        'type': request.form.get("type"),
        'project': request.form.get("project"),
        'journal': request.form.get("journal"),
        'authors': request.form.get("authors"),
        'submission_date': parse_date(request.form.get("submission_date")),
        'status': request.form.get("status"),
        'observation': request.form.get("observation"),
    }

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            if data['id']:  # Update existing record
                cur.execute("""
                    UPDATE publications
                    SET title = %s, type = %s, project = %s, journal = %s,
                        authors = %s, submission_date = %s, status = %s, observation = %s
                    WHERE id = %s;
                """, (data['title'], data['type'], data['project'], data['journal'],
                      data['authors'], data['submission_date'], data['status'], data['observation'], data['id']))
            else:  # Insert new record
                cur.execute("""
                    INSERT INTO publications (title, type, project, journal, authors, submission_date, status, observation)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
                """, (data['title'], data['type'], data['project'], data['journal'],
                      data['authors'], data['submission_date'], data['status'], data['observation']))
            conn.commit()

    return redirect(url_for("index"))

# Route: Delete Publication
@app.route("/delete/<int:pub_id>", methods=["POST"])
def delete(pub_id):
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM publications WHERE id = %s;", (pub_id,))
            conn.commit()

    return redirect(url_for("index"))

# Route: Generate APA
@app.route("/generate_apa")
def generate_apa():
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT authors, title, journal, submission_date, status FROM publications;")
            publications = cur.fetchall()

    apa_references = []
    for pub in publications:
        authors, title, journal, submission_date, status = pub
        year = submission_date.year if submission_date else "n.d."
        apa_references.append(f"{authors} ({year}). <em>{title}</em>. <i>{journal}</i>. [Status: {status}]")

    return jsonify({"apa": "<br>".join(apa_references)})

# Initialize the database table
initialize_db()

# Run the application
if __name__ == "__main__":
    app.run(debug=True)
