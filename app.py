import os
import json
import re
import subprocess
import psutil
import socket
import sys
import hashlib
import secrets
import time
import threading
import requests
from datetime import datetime, timedelta
from flask import Flask, send_from_directory, request, jsonify, session, redirect, url_for
from db_handler import db_handler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
USERS_DIR = os.path.join(BASE_DIR, "USERS")
os.makedirs(USERS_DIR, exist_ok=True)

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
app.config['MAX_CONTENT_LENGTH'] = 200 * 1024 * 1024  # 200MB

# Global Database
db = db_handler.load_db()

# ============== PORT MANAGEMENT ==============
def get_assigned_port():
    for port in range(8100, 9000):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.1)
            result = s.connect_ex(('127.0.0.1', port))
            s.close()
            if result != 0: return port
        except: return port
    return 8080

# ============== ROUTES ==============
@app.route('/')
def home():
    if 'username' not in session: return redirect('/login')
    return redirect('/dashboard')

@app.route('/login')
def login_page():
    if 'username' in session: return redirect('/')
    with open(os.path.join(BASE_DIR, 'login.html'), 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/dashboard')
def dashboard():
    if 'username' not in session: return redirect('/login')
    with open(os.path.join(BASE_DIR, 'index.html'), 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/admin')
def admin_panel():
    if 'username' not in session: return redirect('/login')
    with open(os.path.join(BASE_DIR, 'admin_panel.html'), 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/ping')
def ping():
    return jsonify({"status": "alive", "time": str(datetime.now())})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    u, p = data.get("username", "").strip(), data.get("password", "").strip()
    user = db["users"].get(u)
    if user and user["password"] == hashlib.sha256(p.encode()).hexdigest():
        session['username'] = u
        session.permanent = True
        return jsonify({"success": True, "redirect": "/dashboard"})
    return jsonify({"success": False, "message": "خطأ في البيانات"})

# ============== SERVER MANAGEMENT & CONSOLE ==============
@app.route('/api/server/install/<folder>', methods=['POST'])
def install_requirements(folder):
    if "username" not in session: return jsonify({"success": False}), 401
    srv = db["servers"].get(folder)
    if not srv or srv["owner"] != session["username"]: return jsonify({"success": False})
    
    req_file = os.path.join(srv["path"], "requirements.txt")
    if os.path.exists(req_file):
        try:
            log_path = os.path.join(srv["path"], "out.log")
            with open(req_file, 'r', encoding='utf-8') as rf:
                packages = [line.strip() for line in rf.readlines() if line.strip() and not line.startswith('#')]
            
            log_file = open(log_path, "a", encoding='utf-8', buffering=1)
            log_file.write("\n" + "="*60 + "\n")
            log_file.write("📦 OMAR BRO HOST - Package Installation Started\n")
            log_file.write("="*60 + "\n")
            log_file.write(f"📋 Packages to install: {len(packages)}\n")
            for i, pkg in enumerate(packages, 1): log_file.write(f"   {i}. {pkg}\n")
            log_file.write("="*60 + "\n\n")
            log_file.flush()
            
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--progress-bar", "on", "--no-cache-dir", "-v"],
                cwd=srv["path"], stdout=log_file, stderr=subprocess.STDOUT, bufsize=1
            )
            
            def monitor_install(p, lf):
                p.wait()
                lf.write("\n" + "="*60 + "\n")
                lf.write("✅ Installation Completed!" if p.returncode == 0 else f"❌ Installation Failed (Code: {p.returncode})\n")
                lf.write("="*60 + "\n")
                lf.flush()
                lf.close()
            
            threading.Thread(target=monitor_install, args=(proc, log_file), daemon=True).start()
            return jsonify({"success": True, "message": "📦 بدأ التثبيت، تابع الكونسول"})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)})
    return jsonify({"success": False, "message": "❌ requirements.txt غير موجود"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
