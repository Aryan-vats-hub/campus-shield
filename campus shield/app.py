from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "CAMPUS_SHIELD_SECRET_KEY_2026"

# Master Security Passcode
ADMIN_SECRET_KEY = "ADMIN@2026"

# Centralized Database Name
DB_NAME = "campus_v2.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_NAME)
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

# Force initialization at boot time for Gunicorn/Render
init_db()

@app.route('/')
def home():
    return render_template('index.html')

# Student Google Sign-in Placeholder Route
@app.route('/login/google')
def student_google_login():
    # Set default session or redirect to OAuth provider
    session['student_logged_in'] = True
    return redirect(url_for('home'))

# API to verify Admin Key and Start Session
@app.route('/api/verify-admin', methods=['POST'])
def verify_admin():
    data = request.get_json() or {}
    key = data.get('key', '').strip()
    if key == ADMIN_SECRET_KEY:
        session['is_admin'] = True
        return jsonify({'status': 'success', 'message': 'Authenticated'})
    return jsonify({'status': 'error', 'message': 'Invalid Security Passcode'}), 401

# Admin Panel Route
@app.route('/admin-panel')
def admin_panel():
    if not session.get('is_admin'):
        return redirect(url_for('home'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM complaints ORDER BY id DESC")
    complaints = cursor.fetchall()
    
    cursor.execute("SELECT * FROM sos_alerts ORDER BY id DESC")
    sos_alerts = cursor.fetchall()
    conn.close()

    return render_template('admin.html', complaints=complaints, alerts=sos_alerts)

# Admin Logout
@app.route('/admin-logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))

# API endpoint for submitting grievances
@app.route('/api/submit', methods=['POST'])
def submit_grievance():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'No data payload received'}), 400

        category = data.get('category', 'General')
        is_anonymous = data.get('is_anonymous', False)
        
        if is_anonymous:
            student_name = "Anonymous"
            roll_number = "N/A"
        else:
            student_name = data.get('name', 'Anonymous')
            roll_number = data.get('roll', 'N/A')

        location = data.get('location', 'Not specified')
        priority = data.get('priority', 'Normal')
        description = data.get('description', '')
        evidence_file = data.get('evidence_file', 'None')
        created_at = datetime.now().strftime('%d %b %Y, %I:%M %p')
        token_id = f"CF-{random.randint(100000, 999999)}"

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO complaints (token_id, category, student_name, roll_number, location, priority, description, evidence_file, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Under Review by Department', ?)
        ''', (token_id, category, student_name, roll_number, location, priority, description, evidence_file, created_at))
        
        conn.commit()
        conn.close()

        return jsonify({'status': 'success', 'token': token_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# API endpoint for Emergency SOS
@app.route('/api/sos', methods=['POST'])
def emergency_sos():
    try:
        data = request.get_json() or {}
        location_info = data.get('location', 'Coordinates not shared')
        timestamp = datetime.now().strftime('%d %b %Y, %I:%M %p')

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sos_alerts (location_info, timestamp, status)
            VALUES (?, ?, 'ACTIVE EMERGENCY')
        ''', (location_info, timestamp))
        conn.commit()
        conn.close()

        return jsonify({'status': 'success', 'message': 'SOS alert transmitted to security'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
