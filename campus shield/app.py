from flask import Flask, render_template, request, jsonify, session, redirect
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "CAMPUS_SHIELD_SECRET_KEY_2026"

# Master Security Passcode
ADMIN_SECRET_KEY = "ADMIN@2026"

def init_db():
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    # Complaints & Maintenance Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id TEXT UNIQUE,
            category TEXT,
            student_name TEXT,
            roll_number TEXT,
            location TEXT,
            priority TEXT,
            description TEXT,
            evidence_file TEXT,
            status TEXT DEFAULT 'Under Review by Department',
            created_at TEXT
        )
    ''')
    # Emergency SOS Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sos_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            location_info TEXT,
            timestamp TEXT,
            status TEXT DEFAULT 'ACTIVE EMERGENCY'
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    return render_template('index.html')

# Direct API to verify Admin Key & Login
@app.route('/api/admin-login', methods=['POST'])
def admin_login():
    data = request.json or {}
    key = data.get('secret_key', '').strip()
    if key == ADMIN_SECRET_KEY:
        session['admin_logged_in'] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Incorrect Security Key!"}), 401

@app.route('/admin-panel')
def admin_panel():
    if not session.get('admin_logged_in'):
        return redirect('/')
    
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM complaints ORDER BY id DESC')
    complaints = cursor.fetchall()

    cursor.execute('SELECT * FROM sos_alerts ORDER BY id DESC')
    sos_alerts = cursor.fetchall()
    conn.close()

    return render_template('admin.html', complaints=complaints, sos_alerts=sos_alerts)

@app.route('/admin-logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/')

# Ticket Submission
@app.route('/api/submit', methods=['POST'])
def submit_complaint():
    try:
        data = request.json
        token = f"CF-{random.randint(10000, 99999)}"
        name = "Anonymous" if data.get('is_anonymous') else (data.get('name') or "Student")
        roll = "Hidden" if data.get('is_anonymous') else (data.get('roll') or "N/A")
        now = datetime.now().strftime("%d %b %Y, %I:%M %p")

        conn = sqlite3.connect('campus.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO complaints (token_id, category, student_name, roll_number, location, priority, description, evidence_file, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            token,
            data.get('category'),
            name,
            roll,
            data.get('location'),
            data.get('priority'),
            data.get('description'),
            data.get('evidence_file', 'None'),
            now
        ))
        conn.commit()
        conn.close()

        return jsonify({"success": True, "token": token})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# Ticket Tracking API
@app.route('/api/track/<token>', methods=['GET'])
def track_complaint(token):
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('SELECT category, location, status, priority, created_at FROM complaints WHERE token_id = ?', (token.strip(),))
    row = cursor.fetchone()
    conn.close()

    if row:
        return jsonify({
            "found": True,
            "category": row[0],
            "location": row[1],
            "status": row[2],
            "priority": row[3],
            "date": row[4]
        })
    return jsonify({"found": False}), 404

# Live SOS Trigger API
@app.route('/api/sos', methods=['POST'])
def trigger_sos():
    data = request.json or {}
    coords = data.get('coords', 'Campus Premises (GPS Unknown)')
    now = datetime.now().strftime("%d %b %Y, %I:%M:%S %p")

    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO sos_alerts (location_info, timestamp) VALUES (?, ?)', (coords, now))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "msg": "SOS broadcasted to Admin control desk."})

# Admin Update Status
@app.route('/api/update-status', methods=['POST'])
def update_status():
    if not session.get('admin_logged_in'):
        return "Unauthorized", 401

    token_id = request.form.get('token_id')
    new_status = request.form.get('status')

    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE complaints SET status = ? WHERE token_id = ?', (new_status, token_id))
    conn.commit()
    conn.close()
    return redirect('/admin-panel')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
