from flask import Flask, render_template, request, redirect, url_for
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

app = Flask(__name__)

# Initialize Firebase Admin SDK
cred = credentials.Certificate("sbrt-f86f2-firebase-adminsdk-fbsvc-752da26068.json")  # Replace with your actual path
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/log-sheet', methods=['GET', 'POST'])
def log_sheet():
    selected_date = request.args.get('date', datetime.today().strftime('%Y-%m-%d'))

    if request.method == 'POST':
        particulars = request.form['particulars']
        debit = request.form['debit']
        credit = request.form['credit']

        log_entry = {
            "date": selected_date,
            "particulars": particulars,
            "debit": float(debit) if debit else 0.0,
            "credit": float(credit) if credit else 0.0
        }

        db.collection("log_sheet").add(log_entry)
        update_totals(selected_date)  # Update daily totals
        return redirect(url_for('log_sheet', date=selected_date))

    logs = db.collection("log_sheet").where("date", "==", selected_date).stream()
    logs = [log.to_dict() for log in logs]

    total_doc = db.collection("totals").document(selected_date).get()
    total = total_doc.to_dict() if total_doc.exists else {"total_debit": 0, "total_credit": 0}

    return render_template('log_sheet.html', logs=logs, selected_date=selected_date, total=total)

def update_totals(date):
    """Calculate and store the total debit and credit for a specific date."""
    logs = db.collection("log_sheet").where("date", "==", date).stream()
    total_debit, total_credit = 0, 0

    for log in logs:
        log_data = log.to_dict()
        total_debit += log_data.get("debit", 0)
        total_credit += log_data.get("credit", 0)

    total_data = {"total_debit": total_debit, "total_credit": total_credit}
    db.collection("totals").document(date).set(total_data)

@app.route('/sales-bill')
def sales_bill():
    return render_template('sales.html')

@app.route('/purchase-bill')
def purchase_bill():
    return render_template('purchase.html')

if _name_ == '_main_':
    app.run(debug=True)
