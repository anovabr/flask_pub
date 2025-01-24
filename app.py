import re
import os
import pandas as pd
import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# Utility functions
CSV_FILE = "publications.csv"

def load_publications():
    if os.path.exists(CSV_FILE):
        return pd.read_csv(CSV_FILE)
    else:
        return pd.DataFrame(columns=[
            "ID", "Title", "Type", "Project", "Journal", "Authors", "SubmissionDate", "Status", "Observation"
        ])

def save_publications(df):
    df.to_csv(CSV_FILE, index=False)

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

STATUS_CHOICES = [
    "In preparation", "Waiting for submission", "Submitted",
    "Under review", "Changes needed", "Resubmitted",
    "Rejected", "Accepted", "Published"
]

@app.route("/")
def index():
    df = load_publications()

    # Make "Observation" field clickable for web links
    if not df.empty:
        df["Observation"] = df["Observation"].apply(make_links_clickable)

    return render_template("index.html", publications=df, statuses=STATUS_CHOICES, datetime=datetime)

@app.route("/add_update", methods=["POST"])
def add_update():
    df = load_publications()

    pub_id = request.form.get("id")
    title = request.form.get("title")
    ptype = request.form.get("type")
    project = request.form.get("project")
    journal = request.form.get("journal")
    authors = request.form.get("authors")
    submission_date = request.form.get("submission_date")
    status = request.form.get("status")
    observation = request.form.get("observation")

    if pub_id:  # Update existing
        df.loc[df['ID'] == int(pub_id), :] = [pub_id, title, ptype, project, journal, authors, submission_date, status, observation]
    else:  # Add new
        new_id = df['ID'].max() + 1 if not df.empty else 1
        new_row = pd.DataFrame([{
            "ID": new_id,
            "Title": title,
            "Type": ptype,
            "Project": project,
            "Journal": journal,
            "Authors": authors,
            "SubmissionDate": submission_date,
            "Status": status,
            "Observation": observation
        }])
        df = pd.concat([df, new_row], ignore_index=True)

    save_publications(df)
    return redirect(url_for("index"))

@app.route("/generate_apa")
def generate_apa_view():
    df = load_publications()
    if not df.empty:
        apa_html = generate_apa(df)
    else:
        apa_html = "<p>No publications yet.</p>"

    return jsonify({"apa": apa_html})

def generate_apa(df):
    if df.empty:
        return "<p>No publications yet.</p>"

    apa_list = []
    for _, row in df.iterrows():
        authors = row['Authors']
        title = row['Title']
        journal = row['Journal']
        submission_date = row['SubmissionDate']
        status = row['Status']
        year = pd.to_datetime(submission_date).year if pd.notnull(submission_date) else "n.d."
        
        # Create an APA-styled reference
        reference = f"{authors} ({year}). <em>{title}</em>. <i>{journal}</i>. [Status: {status}]"
        apa_list.append(f"<p>{reference}</p>")

    return "\n".join(apa_list)

@app.route("/delete/<int:pub_id>", methods=["POST"])
def delete(pub_id):
    df = load_publications()
    df = df[df['ID'] != pub_id]
    save_publications(df)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)