
from flask import Flask, render_template, request, redirect, url_for
import sqlite3
from datetime import datetime
import os

app = Flask(__name__)
DB_PATH = "silo_data.db"

def init_db():
    if not os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS silos (name TEXT PRIMARY KEY, capacity INTEGER, current INTEGER)")
        c.execute("CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, silo TEXT, action TEXT, amount REAL, date TEXT)")
        # Insert initial silos if not present
        c.execute("SELECT COUNT(*) FROM silos")
        if c.fetchone()[0] == 0:
            silos = [
                ('Bastak', 200, 150),
                ('Faramarzan', 130, 90),
                ('Lemazan', 130, 110),
                ('Charak', 80, 40)
            ]
            c.executemany("INSERT INTO silos VALUES (?, ?, ?)", silos)
        conn.commit()
        conn.close()

def get_silos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, capacity, current FROM silos")
    silos = {row[0]: {"capacity": row[1], "current": row[2]} for row in c.fetchall()}
    conn.close()
    return silos

def get_history_by_date(date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT silo, action, amount, date FROM history WHERE date(date) = date(?) ORDER BY id DESC", (date,))
    history = [{"silo": row[0], "action": row[1], "amount": row[2], "date": row[3]} for row in c.fetchall()]
    conn.close()
    return history

def update_silo(silo_name, amount, action, log_date):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT capacity, current FROM silos WHERE name = ?", (silo_name,))
    row = c.fetchone()
    if row:
        capacity, current = row
        if action == 'input':
            new_current = min(capacity, current + amount)
        elif action == 'output':
            new_current = max(0, current - amount)
        else:
            conn.close()
            return
        c.execute("UPDATE silos SET current = ? WHERE name = ?", (new_current, silo_name))
        c.execute("INSERT INTO history (silo, action, amount, date) VALUES (?, ?, ?, ?)",
                  (silo_name, action, amount, log_date))
        conn.commit()
    conn.close()

def calculate_daily_inventory(date):
    silos = get_silos()
    inventory = {}
    for name in silos:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT SUM(CASE WHEN action='input' THEN amount ELSE -amount END) FROM history WHERE silo=? AND date(date) < date(?)", (name, date))
        prev_change = c.fetchone()[0] or 0
        start_of_day = prev_change

        c.execute("SELECT SUM(CASE WHEN action='input' THEN amount ELSE -amount END) FROM history WHERE silo=? AND date(date)=date(?)", (name, date))
        day_change = c.fetchone()[0] or 0
        end_of_day = start_of_day + day_change
        conn.close()

        inventory[name] = {
            "start": round(start_of_day, 2),
            "end": round(end_of_day, 2)
        }
    return inventory

@app.route('/', methods=["GET", "POST"])
def index():
    if request.method == "POST":
        silo = request.form['silo']
        amount = float(request.form['amount'])
        action = request.form['action']
        date = request.form['date']
        update_silo(silo, amount, action, date)
        return redirect(url_for('index', date=date))

    selected_date = request.args.get('date')
    if not selected_date:
        selected_date = datetime.now().strftime('%Y-%m-%d')

    silos = get_silos()
    history = get_history_by_date(selected_date)
    inventory = calculate_daily_inventory(selected_date)

    return render_template('index.html', silos=silos, history=history, inventory=inventory, selected_date=selected_date)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
