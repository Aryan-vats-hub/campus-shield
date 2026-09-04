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
            student_email TEXT DEFAULT 'Not Logged In',
            location TEXT,
            priority TEXT,
            description TEXT,
            evidence_file TEXT,
            status TEXT DEFAULT 'Under Review by Department',
            created_at TEXT
        )
    ''')
    # Backward compatibility: agar student_email column na ho toh add kar do
    try:
        cursor.execute("ALTER TABLE complaints ADD COLUMN student_email TEXT DEFAULT 'Not Logged In'")
    except sqlite3.OperationalError:
        pass

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

    user_email = session.get('user_email')
    return render_template('index.html', token=token, track_result=track_result, user_email=user_email)

# --- STUDENT GMAIL LOGIN SIMULATION ---
@app.route('/login/google')
def student_google_login():
    # College Demo Google Login Simulation
    session['user_email'] = "student.demo@campus.edu"
    session['student_name'] = "Verified Student"
    return redirect(url_for('home'))

@app.route('/logout')
def student_logout():
    session.pop('user_email', None)
    session.pop('student_name', None)
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

# --- STATUS UPDATE ---
@app.route('/update-status', methods=['POST'])
@app.route('/api/update-status', methods=['POST'])
@app.route('/update_status', methods=['POST'])
def update_status():
    if not session.get('is_admin'):
        return redirect(url_for('home'))
    
    data = request.get_json(silent=True) or request.form or {}
    token_id = data.get('token_id') or data.get('token')
    new_status = data.get('status') or data.get('new_status')

    if token_id and new_status:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE complaints SET status = ? WHERE token_id = ?", (new_status, token_id))
        conn.commit()
        conn.close()

    if request.is_json:
        return jsonify({'status': 'success', 'message': 'Status updated'})
    return redirect(url_for('admin_panel'))

# --- DELETE COMPLAINT (FOR ADMIN & STUDENT) ---
@app.route('/delete-complaint', methods=['POST'])
def delete_complaint():
    token_id = request.form.get('token_id')
    source = request.form.get('source', 'student')

    if token_id:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM complaints WHERE token_id = ?", (token_id,))
        conn.commit()
        conn.close()

    if source == 'admin':
        return redirect(url_for('admin_panel'))
    return redirect(url_for('home'))

@app.route('/submit-grievance', methods=['POST'])
def submit_grievance_direct():
    try:
        category = request.form.get('category', 'General Infrastructure')
        is_anonymous = request.form.get('is_anonymous') == 'on'
        
        if is_anonymous:
            student_name = "Anonymous"
            roll_number = "N/A"
            student_email = "Hidden (Anonymous)"
        else:
            student_name = request.form.get('name') or session.get('student_name') or 'Anonymous'
            roll_number = request.form.get('roll') or 'N/A'
            student_email = session.get('user_email') or 'Not Logged In'

        location = request.form.get('location') or 'Not specified'
        priority = request.form.get('priority', 'Normal')
        description = request.form.get('description', '')
        created_at = datetime.now().strftime('%d %b %Y, %I:%M %p')
        token_id = f"CF-{random.randint(100000, 999999)}"

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO complaints (token_id, category, student_name, roll_number, student_email, location, priority, description, evidence_file, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'None', 'Under Review by Department', ?)
        ''', (token_id, category, student_name, roll_number, student_email, location, priority, description, created_at))
        conn.commit()
        conn.close()

        return redirect(url_for('home', token=token_id))
    except Exception as e:
        return f"Submission Error: {str(e)}"

@app.route('/api/verify-admin', methods=['POST'])
def verify_admin():
    data = request.get_json(silent=True) or request.form or {}
    key = str(data.get('key', '')).strip()
    if key == ADMIN_SECRET_KEY:
        session['is_admin'] = True
        return jsonify({'status': 'success', 'redirect': '/admin-panel'})
    return jsonify({'status': 'error', 'message': 'Invalid Passcode'}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
