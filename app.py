import os
import re
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, jsonify
from datetime import datetime

app = Flask(__name__)

# Path to your local SQLite database file
DATABASE_FILE = "publications.db"

# Function to connect to the database
def get_db_connection():
    """
    Returns a connection to the local SQLite database.
    """
    conn = sqlite3.connect(DATABASE_FILE)
    # By default, sqlite3 returns data as tuples. 
    # If you want dictionary-like behavior, uncomment the next line:
    # conn.row_factory = sqlite3.Row
    return conn

# Initialize the database table
def initialize_db():
    """
    Creates the 'publications' table if it doesn't exist.
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS publications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    type TEXT NOT NULL,
                    project TEXT,
                    journal TEXT,
                    authors TEXT,
                    submission_date TEXT,
                    status TEXT,
                    observation TEXT
                );
            """)
            conn.commit()
            print("Database initialized successfully.")
    except sqlite3.Error as e:
        print(f"Database initialization error: {e}")
        raise

STATUS_CHOICES = [
    "In preparation", "Waiting for submission", "Submitted",
    "Under review", "Changes needed", "Resubmitted",
    "Rejected", "Accepted", "Published"
]

# Helper function to parse dates safely
def parse_date(date_string):
    """
    Safely parse a string in 'YYYY-MM-DD' format into a datetime.date object.
    Returns None if parsing fails or if the input is empty.
    """
    if date_string:
        try:
            return datetime.strptime(date_string, '%Y-%m-%d').date()
        except ValueError:
            return None
    return None

# Helper function to make links clickable in the observation field
def make_links_clickable(observation):
    """
    Converts URLs in a text string into clickable links.
    """
    if not isinstance(observation, str):
        return observation  # If it's not a string, return as-is

    # Regex to find URLs
    url_pattern = r'(https?://\S+|www\.\S+)'

    # Replace the match with an HTML <a> tag
    def replace_with_link(match):
        url = match.group(0)
        # Add http:// if the URL starts with "www."
        if url.startswith("www."):
            url = f"http://{url}"
        return f"<a href='{url}' target='_blank' style='color: blue; text-decoration: underline;'>click here</a>"

    return re.sub(url_pattern, replace_with_link, observation)

# Route: Index
@app.route("/")
def index():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM publications ORDER BY id;")
        publications = cur.fetchall()

    # Make observation links clickable
    publications = [
        (
            pub[0],  # id
            pub[1],  # title
            pub[2],  # type
            pub[3],  # project
            pub[4],  # journal
            pub[5],  # authors
            pub[6],  # submission_date
            pub[7],  # status
            make_links_clickable(pub[8])  # observation
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

    # Convert the parsed date object back to a string (YYYY-MM-DD) for storage
    if data['submission_date']:
        data['submission_date'] = data['submission_date'].strftime("%Y-%m-%d")

    with get_db_connection() as conn:
        cur = conn.cursor()
        if data['id']:  # Update existing record
            cur.execute(
                """
                UPDATE publications
                SET title = ?, type = ?, project = ?, journal = ?,
                    authors = ?, submission_date = ?, status = ?, observation = ?
                WHERE id = ?;
                """,
                (
                    data['title'], data['type'], data['project'], data['journal'],
                    data['authors'], data['submission_date'], data['status'], data['observation'], data['id']
                )
            )
        else:  # Insert new record
            cur.execute(
                """
                INSERT INTO publications (title, type, project, journal, authors, submission_date, status, observation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data['title'], data['type'], data['project'], data['journal'],
                    data['authors'], data['submission_date'], data['status'], data['observation']
                )
            )
        conn.commit()

    return redirect(url_for("index"))

# Route: Delete Publication
@app.route("/delete/<int:pub_id>", methods=["POST"])
def delete(pub_id):
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM publications WHERE id = ?;", (pub_id,))
        conn.commit()

    return redirect(url_for("index"))

# Route: Generate APA
@app.route("/generate_apa")
def generate_apa():
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT authors, title, journal, submission_date, status FROM publications;")
        publications = cur.fetchall()

    apa_references = []
    for pub in publications:
        authors, title, journal, submission_date, status = pub
        submission_date_obj = parse_date(submission_date)
        year = submission_date_obj.year if submission_date_obj else "n.d."
        apa_references.append(
            f"{authors} ({year}). <em>{title}</em>. <i>{journal}</i>. [Status: {status}]"
        )

    return jsonify({"apa": "<br>".join(apa_references)})

# Initialize the database table at startup
initialize_db()

# Run the application
if __name__ == "__main__":
    app.run(debug=True)
