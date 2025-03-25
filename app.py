from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)

# Initialize MongoDB connection
client = MongoClient("mongodb://localhost:27017/")
db = client["kaatha_book"]
log_collection = db["log_sheet"]
total_collection = db["totals"]  # Collection to store daily totals


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

        log_collection.insert_one(log_entry)
        update_totals(selected_date)  # Update daily totals
        return redirect(url_for('log_sheet', date=selected_date))

    logs = list(log_collection.find({"date": selected_date}))
    total = total_collection.find_one({"date": selected_date}) or {"total_debit": 0, "total_credit": 0}

    return render_template('log_sheet.html', logs=logs, selected_date=selected_date, total=total)


def update_totals(date):
    """Calculate and store the total debit and credit for a specific date."""
    pipeline = [
        {"$match": {"date": date}},
        {"$group": {
            "_id": "$date",
            "total_debit": {"$sum": "$debit"},
            "total_credit": {"$sum": "$credit"}
        }}
    ]

    totals = list(log_collection.aggregate(pipeline))
    if totals:
        total_data = {
            "date": date,
            "total_debit": totals[0]["total_debit"],
            "total_credit": totals[0]["total_credit"]
        }
        total_collection.update_one({"date": date}, {"$set": total_data}, upsert=True)


@app.route('/sales-bill')
def sales_bill():
    return render_template('sales.html')


@app.route('/purchase-bill')
def purchase_bill():
    return render_template('purchase.html')


if __name__ == '__main__':
    app.run(debug=True)
