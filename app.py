from flask import Flask, render_template, request
import csv
import os
import io
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload

app = Flask(__name__)

# 🔹 Google Drive API Setup
SERVICE_ACCOUNT_FILE = "credentials.json"  # ✅ Replace with actual credentials
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
FOLDER_ID = "1NXFNZy0AgcNZWbVszgr1eEOy85RUxEgp"  # ✅ Replace with actual Google Drive folder ID

credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
drive_service = build("drive", "v3", credentials=credentials)

# 🔹 Directory to store local logs before uploading
LOGS_DIR = "logs"
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

def get_csv_filename(date):
    """Returns the CSV filename for a given day."""
    return f"{date}.csv"  # ✅ Now each date has a unique CSV file

def get_drive_file_id(filename):
    """Fetches the Google Drive file ID if it exists, else returns None."""
    query = f"name='{filename}' and '{FOLDER_ID}' in parents"
    results = drive_service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    return files[0]["id"] if files else None

def create_drive_file(filename):
    """Creates a new CSV file on Google Drive."""
    local_path = os.path.join(LOGS_DIR, filename)

    # ✅ Ensure the local CSV file exists before uploading
    if not os.path.exists(local_path):
        with open(local_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Date", "Particulars", "Debit", "Credit"])  # ✅ Correct column names

    # ✅ Upload file to Google Drive
    file_metadata = {
        "name": filename,
        "mimeType": "text/csv",
        "parents": [FOLDER_ID],
    }
    media = MediaFileUpload(local_path, mimetype="text/csv")
    file = drive_service.files().create(body=file_metadata, media_body=media, fields="id").execute()
    return file.get("id")

def download_drive_file(file_id, local_path):
    """Downloads the CSV file from Google Drive."""
    request = drive_service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()

    # ✅ Write downloaded content to the local file
    with open(local_path, "wb") as f:
        f.write(fh.getvalue())

def upload_drive_file(local_path, file_id):
    """Uploads the modified CSV file back to Google Drive."""
    media = MediaFileUpload(local_path, mimetype="text/csv")
    drive_service.files().update(fileId=file_id, media_body=media).execute()

def write_log_entry(date, particulars, debit, credit):
    """Writes a new log entry to the corresponding CSV file on Google Drive."""
    filename = get_csv_filename(date)
    local_path = os.path.join(LOGS_DIR, filename)

    # 🔹 Check if file exists on Google Drive
    file_id = get_drive_file_id(filename)
    
    if not file_id:
        file_id = create_drive_file(filename)

    # 🔹 Download latest file
    download_drive_file(file_id, local_path)

    # 🔹 Append new entry
    with open(local_path, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([date, particulars, debit, credit])

    # 🔹 Upload back to Google Drive
    upload_drive_file(local_path, file_id)

@app.route("/")
def home():
    return render_template("home.html")

@app.route("/log-sheet", methods=["GET", "POST"])
def log_sheet():
    selected_date = request.args.get("date", datetime.today().strftime("%Y-%m-%d"))

    # Initialize totals
    total_credit = 0
    total_debit = 0
    logs = []  # ✅ Ensure logs list is initialized

    if request.method == "POST":
        particulars = request.form["particulars"]
        debit = float(request.form["debit"]) if request.form["debit"] else 0
        credit = float(request.form["credit"]) if request.form["credit"] else 0

        write_log_entry(selected_date, particulars, debit, credit)

    # 🔹 Read logs from CSV
    filename = get_csv_filename(selected_date)
    local_path = os.path.join(LOGS_DIR, filename)

    file_id = get_drive_file_id(filename)
    if file_id:
        download_drive_file(file_id, local_path)

    # 🔹 Read file content if it exists
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        with open(local_path, mode="r", newline="") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["Date"] == selected_date:  # ✅ Only show logs for the selected date
                    logs.append({
                        "Particulars": row["Particulars"],
                        "Credit": float(row["Credit"]) if row["Credit"] else 0,
                        "Debit": float(row["Debit"]) if row["Debit"] else 0,
                    })
                    total_debit += logs[-1]["Debit"]
                    total_credit += logs[-1]["Credit"]

    total = {"total_credit": total_credit, "total_debit": total_debit}

    return render_template("log_sheet.html", selected_date=selected_date, logs=logs, total=total)

if __name__ == "__main__":
    app.run(debug=True)
