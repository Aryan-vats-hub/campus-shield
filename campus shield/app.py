from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import sqlite3
import random
from datetime import datetime

app = Flask(__name__)
app.secret_key = "CAMPUS_SHIELD_SECRET_KEY_2026"

ADMIN_SECRET_KEY = "ADMIN@2026"
DB_NAME = "campus_v2.db"

def get_db_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
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
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sos_alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alert_type TEXT DEFAULT 'GENERAL',
            location_info TEXT,
            timestamp TEXT,
            status TEXT DEFAULT 'ACTIVE EMERGENCY'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route('/')
def home():
    token = request.args.get('token')
    track_result = None
    search_token = request.args.get('track_token')
    
    if search_token:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM complaints WHERE token_id = ?", (search_token.strip(),))
        track_result = cursor.fetchone()
        conn.close()

    return render_template('index.html', token=token, track_result=track_result)

@app.route('/login/google')
def student_google_login():
    session['student_logged_in'] = True
    return redirect(url_for('home'))

@app.route('/admin-login-post', methods=['POST'])
def admin_login_post():
    key = request.form.get('admin_key', '').strip()
    if key == ADMIN_SECRET_KEY:
        session['is_admin'] = True
        return redirect(url_for('admin_panel'))
    return "<script>alert('Invalid Passcode!'); window.location.href='/';</script>"

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

@app.route('/admin-logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('home'))

@app.route('/submit-grievance', methods=['POST'])
def submit_grievance_direct():
    try:
        category = request.form.get('category', 'General Infrastructure')
        is_anonymous = request.form.get('is_anonymous') == 'on'
        
        if is_anonymous:
            student_name = "Anonymous"
            roll_number = "N/A"
        else:
            student_name = request.form.get('name') or 'Anonymous'
            roll_number = request.form.get('roll') or 'N/A'

        location = request.form.get('location') or 'Not specified'
        priority = request.form.get('priority', 'Normal')
        description = request.form.get('description', '')
        created_at = datetime.now().strftime('%d %b %Y, %I:%M %p')
        token_id = f"CF-{random.randint(100000, 999999)}"

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO complaints (token_id, category, student_name, roll_number, location, priority, description, evidence_file, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'None', 'Under Review by Department', ?)
        ''', (token_id, category, student_name, roll_number, location, priority, description, created_at))
        conn.commit()
        conn.close()

        return redirect(url_for('home', token=token_id))
    except Exception as e:
        return f"Submission Error: {str(e)}"

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
