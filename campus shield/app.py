from flask import Flask, render_template, request, jsonify, redirect, session
import sqlite3
import random

app = Flask(__name__)
app.secret_key = "CAMPUS_SHIELD_SUPER_SECRET_SESSION_KEY"

# Master Security Key
ADMIN_SECRET_KEY = "ADMIN@2026"

def init_db():
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS complaints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_id TEXT UNIQUE,
            category TEXT,
            student_name TEXT,
            location TEXT,
            description TEXT,
            evidence_file TEXT,
            status TEXT DEFAULT 'Under Review by Department'
        )
    ''')
    conn.commit()
    conn.close()

@app.route('/')
def home():
    # Regular student home portal
    return render_template('index.html')

# Separate Admin Gateway
@app.route('/admin', methods=['GET', 'POST'])
def admin_portal():
    if request.method == 'POST':
        entered_key = request.form.get('secret_key', '').strip()
        if entered_key == ADMIN_SECRET_KEY:
            session['admin_logged_in'] = True
            return redirect('/admin')
        else:
            return render_template('admin.html', authenticated=False, error="Invalid Security Key! Access Denied.")

    # GET Request
    if session.get('admin_logged_in'):
        conn = sqlite3.connect('campus.db')
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM complaints ORDER BY id DESC')
        complaints = cursor.fetchall()
        conn.close()
        return render_template('admin.html', authenticated=True, complaints=complaints)
    
    return render_template('admin.html', authenticated=False)

@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    return redirect('/admin')

@app.route('/api/submit', methods=['POST'])
def submit_complaint():
    data = request.json
    token = f"CF-{random.randint(10000, 99999)}"
    
    name = "Anonymous" if data.get('is_anonymous') else data.get('name', 'Student')
    
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO complaints (token_id, category, student_name, location, description, evidence_file)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        token,
        data.get('category'),
        name,
        data.get('location'),
        data.get('description'),
        data.get('evidence_file', 'None')
    ))
    conn.commit()
    conn.close()
    
    return jsonify({"success": True, "token": token})

@app.route('/api/track/<token>', methods=['GET'])
def track_complaint(token):
    conn = sqlite3.connect('campus.db')
    cursor = conn.cursor()
    cursor.execute('SELECT category, location, status FROM complaints WHERE token_id = ?', (token,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            "found": True,
            "category": row[0],
            "location": row[1],
            "status": row[2]
        })
    return jsonify({"found": False}), 404

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
    return redirect('/admin')

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
    