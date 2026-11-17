import os
from flask import Flask, redirect, render_template_string, request, url_for, session, flash, send_file, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy import text
from functools import wraps
from datetime import datetime
import json
import random
import re

# ==========================================
# 1. KONFIGURASI SERVER & APP (ABSOLUTE PATH)
# ==========================================
app = Flask(__name__)
app.config['SECRET_KEY'] = 'brain-edumath-super-secret-key-2026'

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'brain_edumath.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = os.path.join(basedir, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BACKUP_FOLDER = os.path.join(basedir, 'backups')
os.makedirs(BACKUP_FOLDER, exist_ok=True)

db = SQLAlchemy(app)

# ==========================================
# 2. DATABASE MODELS
# ==========================================
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    nama = db.Column(db.String(150), nullable=False)
    role = db.Column(db.String(50), default='siswa')

class MateriSoal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), default='buka')
    waktu_mulai = db.Column(db.String(50), nullable=True)
    waktu_selesai = db.Column(db.String(50), nullable=True)
    durasi_menit = db.Column(db.Integer, default=60)
    soals = db.relationship('SoalDetail', backref='materi', lazy=True, cascade="all, delete-orphan")

class SoalDetail(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    materi_id = db.Column(db.Integer, db.ForeignKey('materi_soal.id'), nullable=False)
    tipe = db.Column(db.String(20), nullable=False, default='pg')
    pertanyaan = db.Column(db.Text, nullable=False)
    foto = db.Column(db.String(255), nullable=True)
    pilihan_a = db.Column(db.Text)
    pilihan_b = db.Column(db.Text)
    pilihan_c = db.Column(db.Text)
    pilihan_d = db.Column(db.Text)
    kunci_jawaban = db.Column(db.Text, nullable=False)
    keyword_jawaban = db.Column(db.Text, nullable=True)
    pembahasan = db.Column(db.Text, nullable=True)
    poin_soal = db.Column(db.Float, default=10.0)

class JawabanSiswa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    materi_id = db.Column(db.Integer, db.ForeignKey('materi_soal.id'), nullable=False)
    soal_id = db.Column(db.Integer, db.ForeignKey('soal_detail.id'), nullable=False)
    jawaban_teks = db.Column(db.Text, nullable=True)
    lampiran_file = db.Column(db.String(255), nullable=True)
    status_koreksi = db.Column(db.String(20), default='Menunggu Koreksi')
    nilai_diperoleh = db.Column(db.Float, default=0.0)
    feedback_guru = db.Column(db.Text, nullable=True)
    sanggahan_siswa = db.Column(db.Text, nullable=True)

class VocabCategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    vocabs = db.relationship('Vocab', backref='category', lazy=True, cascade="all, delete-orphan")

class Vocab(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category_id = db.Column(db.Integer, db.ForeignKey('vocab_category.id'), nullable=False)
    term_en = db.Column(db.String(100), nullable=False)
    term_id = db.Column(db.String(100), nullable=False)
    definition = db.Column(db.Text, nullable=False)

class RiwayatPengerjaan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    materi_id = db.Column(db.Integer, db.ForeignKey('materi_soal.id'), nullable=False)
    skor_tertinggi = db.Column(db.Float, nullable=False, default=0.0)
    status_ujian = db.Column(db.String(30), default='Selesai Dikerjakan')
    terakhir_dikerjakan = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class KartuSoalUlarTangga(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    warna = db.Column(db.String(20), nullable=False)
    tipe_soal = db.Column(db.String(20), default='angka')
    pertanyaan = db.Column(db.Text, nullable=False)
    jawaban = db.Column(db.String(255), nullable=False)
    keyword_jawaban = db.Column(db.Text, nullable=True)

# ==========================================
# 3. INISIALISASI DATA AWAL & MIGRASI OTOMATIS
# ==========================================
with app.app_context():
    db.create_all()
    
    kolom_baru = [
        ("soal_detail", "foto", "VARCHAR(255)"),
        ("soal_detail", "keyword_jawaban", "TEXT"),
        ("soal_detail", "pembahasan", "TEXT"),
        ("soal_detail", "poin_soal", "FLOAT DEFAULT 10.0"),
        ("jawaban_siswa", "lampiran_file", "VARCHAR(255)"),
        ("materi_soal", "status", "VARCHAR(20) DEFAULT 'buka'"),
        ("materi_soal", "waktu_mulai", "VARCHAR(50)"),
        ("materi_soal", "waktu_selesai", "VARCHAR(50)"),
        ("materi_soal", "durasi_menit", "INTEGER DEFAULT 60"),
        ("riwayat_pengerjaan", "status_ujian", "VARCHAR(30) DEFAULT 'Selesai Dikerjakan'"),
        ("riwayat_pengerjaan", "terakhir_dikerjakan", "DATETIME"),
        ("jawaban_siswa", "feedback_guru", "TEXT"),
        ("jawaban_siswa", "sanggahan_siswa", "TEXT"),
        ("kartu_soal_ular_tangga", "tipe_soal", "VARCHAR(20) DEFAULT 'angka'"),
        ("kartu_soal_ular_tangga", "keyword_jawaban", "TEXT")
    ]
    
    for tabel, kolom, tipe_data in kolom_baru:
        try:
            db.session.execute(text(f"ALTER TABLE {tabel} ADD COLUMN {kolom} {tipe_data}"))
            db.session.commit()
        except Exception:
            db.session.rollback()

    if not User.query.filter_by(username='admin').first():
        db.session.add(User(username='admin', password=generate_password_hash('admin123'), nama='Bapak/Ibu Guru', role='admin'))
    if not User.query.filter_by(username='siswa').first():
        db.session.add(User(username='siswa', password=generate_password_hash('123'), nama='Siswa Teladan', role='siswa'))
    
    if KartuSoalUlarTangga.query.count() == 0:
        default_cards = [
            ('hijau', 'angka', '5 + 3', '8', ''), 
            ('hijau', 'angka', '12 - 4', '8', ''), 
            ('hijau', 'angka', '7 + 6', '13', ''),
            ('biru', 'angka', '4 × 3', '12', ''), 
            ('biru', 'angka', '5 × 5', '25', ''), 
            ('biru', 'angka', '6 × 2', '12', ''),
            ('kuning', 'angka', '15 ÷ 3', '5', ''), 
            ('kuning', 'angka', '20 ÷ 4', '5', ''), 
            ('kuning', 'angka', '18 ÷ 2', '9', ''),
            ('merah', 'angka', '45 + 25', '70', ''), 
            ('merah', 'angka', '88 - 35', '53', ''), 
            ('merah', 'angka', '60 + 15', '75', '')
        ]
        for w, ts, p, j, kw in default_cards:
            db.session.add(KartuSoalUlarTangga(warna=w, tipe_soal=ts, pertanyaan=p, jawaban=j, keyword_jawaban=kw))
    
    db.session.commit()

# ==========================================
# 4. DEKORATOR HAK AKSES
# ==========================================
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Silakan login terlebih dahulu.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('Akses ditolak! Hanya Guru/Admin yang diizinkan.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# ==========================================
# 5. RENDER LAYOUT UTAMA (GLOBAL STYLING)
# ==========================================
def render_page(title, body_content):
    html_template = """
    <!DOCTYPE html>
    <html lang="id">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title} | BRAIN Edumath</title>
        <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
        <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
        <style>
            :root {{ 
                --bg-main: #f4f6f9; 
                --sidebar-bg: linear-gradient(180deg, #1e1b4b 0%, #312e81 100%); 
                --primary: #4f46e5; 
                --primary-hover: #4338ca;
                --success: #059669; 
                --warning: #d97706; 
                --danger: #dc2626; 
                --text-main: #0f172a;
                --text-muted: #64748b;
                --card-bg: #ffffff;
                --border-color: #e2e8f0;
            }}
            * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; }}
            body {{ background: var(--bg-main); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }}
            a {{ text-decoration: none; color: inherit; }}
            
            .sidebar {{ width: 280px; background: var(--sidebar-bg); color: #e0e7ff; display: flex; flex-direction: column; padding: 32px 20px; flex-shrink: 0; box-shadow: 6px 0 30px rgba(79, 70, 229, 0.12); z-index: 10; overflow-y: auto; }}
            .brand {{ font-size: 1.5rem; font-weight: 800; text-align: center; margin-bottom: 40px; letter-spacing: 0.5px; background: linear-gradient(135deg, #818cf8, #c084fc); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: flex; align-items: center; justify-content: center; gap: 12px; }}
            .nav-item {{ display: flex; align-items: center; gap: 14px; padding: 14px 18px; color: #c7d2fe; border-radius: 14px; margin-bottom: 10px; font-weight: 600; font-size: 0.95rem; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); }}
            .nav-item:hover, .nav-item.active {{ background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; transform: translateX(6px); box-shadow: 0 8px 25px rgba(99, 102, 241, 0.4); }}
            
            .main-content {{ flex: 1; padding: 36px 48px; overflow-y: auto; display: flex; flex-direction: column; scroll-behavior: smooth; }}
            .top-header {{ display: flex; justify-content: flex-end; align-items: center; margin-bottom: 28px; gap: 16px; background: white; padding: 16px 28px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.03); border: 1px solid var(--border-color); flex-shrink: 0; }}
            .user-info-badge {{ display: flex; align-items: center; gap: 12px; font-size: 0.95rem; }}
            
            .card {{ background: var(--card-bg); border-radius: 24px; padding: 32px; box-shadow: 0 15px 35px rgba(0,0,0,0.04); margin-bottom: 24px; border: 1px solid rgba(226, 232, 240, 0.8); transition: all 0.3s ease; }}
            .card:hover {{ box-shadow: 0 20px 45px rgba(79, 70, 229, 0.08); transform: translateY(-3px); }}
            
            .btn {{ background: var(--primary); color: white; border: none; padding: 12px 24px; border-radius: 14px; font-weight: 600; cursor: pointer; display: inline-flex; align-items: center; justify-content: center; gap: 8px; text-align: center; transition: all 0.25s ease; box-shadow: 0 6px 20px rgba(79, 70, 229, 0.25); }}
            .btn:hover {{ background: var(--primary-hover); transform: translateY(-2px); box-shadow: 0 8px 25px rgba(79, 70, 229, 0.4); }}
            .btn-danger {{ background: var(--danger); box-shadow: 0 6px 20px rgba(220, 38, 38, 0.25); }}
            .btn-danger:hover {{ background: #b91c1c; }}
            .btn-success {{ background: var(--success); box-shadow: 0 6px 20px rgba(5, 150, 105, 0.25); }}
            .btn-success:hover {{ background: #047857; }}
            .btn-warning {{ background: var(--warning); color:white; box-shadow: 0 6px 20px rgba(217, 119, 6, 0.25); }}
            .btn-warning:hover {{ background: #b45309; }}
            .btn-sm {{ padding: 8px 16px; font-size: 0.85rem; border-radius: 10px; }}
            
            .alert {{ padding: 16px 22px; border-radius: 16px; margin-bottom: 24px; color: white; font-weight: 600; display: flex; align-items: center; gap: 12px; box-shadow: 0 10px 25px rgba(0,0,0,0.06); flex-shrink: 0; }}
            .alert-success {{ background: var(--success); }}
            .alert-danger {{ background: var(--danger); }}
            .alert-warning {{ background: var(--warning); color:#fff; }}

            .form-control {{ width: 100%; padding: 14px 18px; border: 2px solid var(--border-color); border-radius: 14px; margin-bottom: 16px; font-family: inherit; font-size: 0.95rem; outline: none; background: #f8fafc; transition: all 0.25s; }}
            .form-control:focus {{ border-color: var(--primary); background: #ffffff; box-shadow: 0 0 0 4px rgba(79, 70, 229, 0.12); }}
            
            .grid-3 {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 28px; }}
            
            table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
            th, td {{ padding: 18px 16px; text-align: left; border-bottom: 1px solid var(--border-color); }}
            th {{ color: var(--text-muted); font-weight: 700; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.8px; background: #f1f5f9; }}
            tr:hover td {{ background: #f8fafc; }}
            
            @media (max-width: 768px) {{
                body {{ flex-direction: column; overflow: auto; height: auto; }}
                .sidebar {{ width: 100%; padding: 16px; height: auto; }}
                .main-content {{ padding: 20px; }}
                .top-header {{ flex-direction: column; align-items: flex-start; }}
            }}
        </style>
    </head>
    <body>
        <div class="sidebar">
            <div class="brand"><i class="fas fa-brain" style="color: #818cf8;"></i> BRAIN EDUMATH</div>
            <a href="{url_dashboard}" class="nav-item"><i class="fas fa-home"></i> Dashboard</a>
            <a href="{url_bank}" class="nav-item"><i class="fas fa-book-open"></i> Bank Soal</a>
            {admin_menu}
            <a href="{url_vocab}" class="nav-item"><i class="fas fa-spell-check"></i> MathVocab</a>
            <a href="{url_game}" class="nav-item"><i class="fas fa-gamepad"></i> GameMath</a>
            <a href="{url_pencapaian}" class="nav-item"><i class="fas fa-trophy"></i> Pencapaian</a>
        </div>
        
        <div class="main-content">
            {top_header}
            {flash_messages}
            {body_content}
        </div>
    </body>
    </html>
    """
    
    url_dash = url_for('dashboard')
    url_b = url_for('bank_soal')
    url_v = url_for('mathvocab')
    url_g = url_for('gamemath')
    url_p = url_for('pencapaian')
    
    admin_menu = ""
    if session.get('role') == 'admin':
        admin_menu = f"""
        <a href="{url_for('manajemen_siswa')}" class="nav-item"><i class="fas fa-users-cog"></i> Kelola Siswa</a>
        <a href="{url_for('kelola_kartu_ular_tangga')}" class="nav-item"><i class="fas fa-dice"></i> Kelola Kartu Game</a>
        <a href="{url_for('koreksi_ujian')}" class="nav-item"><i class="fas fa-check-double"></i> Koreksi Ujian</a>
        """
        
    top_header = ""
    if session.get('user_id'):
        top_header = f"""
        <div class="top-header">
            <div class="user-info-badge">
                <i class="fas fa-user-circle fa-2x" style="color:var(--primary);"></i>
                <div><b>{session.get('nama', '')}</b> <span style="font-size:0.75rem; color:#4f46e5; text-transform:uppercase; background:#e0e7ff; padding:4px 10px; border-radius:8px; margin-left:8px; font-weight:700;">{session.get('role', '')}</span></div>
            </div>
            <a href="{url_for('logout')}" class="btn btn-danger btn-sm" style="font-weight:700;"><i class="fas fa-sign-out-alt"></i> Keluar</a>
        </div>
        """
        
    flash_html = ""
    with app.test_request_context():
        messages = get_flashed_messages(with_categories=True)
        for cat, msg in messages:
            flash_html += f'<div class="alert alert-{cat}"><i class="fas fa-info-circle fa-lg"></i> <span>{msg}</span></div>'

    rendered = html_template.format(
        title=title,
        url_dashboard=url_dash,
        url_bank=url_b,
        admin_menu=admin_menu,
        url_vocab=url_v,
        url_game=url_g,
        url_pencapaian=url_p,
        top_header=top_header,
        flash_messages=flash_html,
        body_content=body_content
    )
    return rendered

# ==========================================
# 6. ROUTING APLIKASI
# ==========================================
@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            session['user_id'] = user.id
            session['nama'] = user.nama
            session['role'] = user.role
            flash(f'Selamat datang kembali, {user.nama}!', 'success')
            return redirect(url_for('dashboard'))
        flash('Username atau Password yang Anda masukkan salah!', 'danger')
        
    return render_template_string("""
    <!DOCTYPE html>
    <html lang="id">
    <head><title>Login | BRAIN Edumath</title>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body{background:#0f172a; color:#1e293b; font-family:'Plus Jakarta Sans',sans-serif; display:flex; justify-content:center; align-items:center; height:100vh; margin:0; background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #4338ca 100%);}
        .box{background:white; color:#1e293b; padding:48px; border-radius:28px; width:100%; max-width:440px; box-shadow: 0 25px 60px rgba(0,0,0,0.3);}
        input { width:100%; padding:15px; margin-bottom:18px; border-radius:14px; border:2px solid #e2e8f0; font-size:1rem; outline:none; background:#f8fafc; transition:all 0.25s; }
        input:focus { border-color:#4f46e5; background:#fff; box-shadow: 0 0 0 4px rgba(79,70,229,0.12); }
        button { width:100%; padding:15px; background:#4f46e5; color:white; border:none; border-radius:14px; font-weight:bold; font-size:1rem; cursor:pointer; transition:all 0.25s; box-shadow: 0 6px 20px rgba(79,70,229,0.3); }
        button:hover { background:#4338ca; transform: translateY(-2px); }
    </style></head>
    <body>
        <div class="box">
            <h2 style="text-align:center; margin-bottom:8px; color:#0f172a; font-size:2rem; font-weight:800;"><i class="fas fa-brain" style="color:#4f46e5;"></i> BRAIN EDUMATH</h2>
            <p style="text-align:center; color:#64748b; font-size:0.95rem; margin-bottom:32px;">Silakan masuk untuk memulai sesi belajar</p>
            {% with messages = get_flashed_messages() %}{% if messages %}<div style="background:#fee2e2; color:#dc2626; padding:14px; border-radius:12px; margin-bottom:20px; font-size:0.9rem; font-weight:600; text-align:center;">{{ messages[0] }}</div>{% endif %}{% endwith %}
            <form method="POST">
                <label style="font-size:0.85rem; font-weight:bold; color:#475569; display:block; margin-bottom:8px;">Username</label>
                <input type="text" name="username" placeholder="Masukkan username..." required>
                <label style="font-size:0.85rem; font-weight:bold; color:#475569; display:block; margin-bottom:8px;">Password</label>
                <input type="password" name="password" placeholder="Masukkan password..." required>
                <button type="submit">MASUK SEKARANG</button>
            </form>
            <div style="font-size:0.85rem; text-align:center; margin-top:28px; color:#64748b; background:#f8fafc; padding:16px; border-radius:14px; border:1px solid #e2e8f0; line-height:1.6;">
                <p style="margin-bottom:4px;"><b>Akun Guru:</b> admin / admin123</p>
                <p><b>Akun Siswa:</b> siswa / 123</p>
            </div>
        </div>
    </body></html>
    """)

@app.route('/dashboard')
@login_required
def dashboard():
    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:36px;">
        <div>
            <h1 style="font-size:2.2rem; font-weight:800; margin-bottom:8px; letter-spacing:-0.5px;">Halo, {session.get('nama', '')}! 👋</h1>
            <p style="color:var(--text-muted); font-size:1.1rem;">Selamat datang di pusat pembelajaran interaktif BRAIN Edumath.</p>
        </div>
        <div style="background:white; padding:12px 24px; border-radius:16px; box-shadow:0 6px 20px rgba(0,0,0,0.04); font-weight:700; color:var(--primary); border:1px solid var(--border-color);">
            <i class="fas fa-calendar-alt"></i> {datetime.now().strftime('%d %B %Y')}
        </div>
    </div>
    
    <div class="grid-3">
        <div class="card" style="border-top: 6px solid #4f46e5; text-align:center; padding:36px 28px;">
            <div style="width:80px; height:80px; background:rgba(79,70,229,0.1); border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 20px auto;">
                <i class="fas fa-book-open fa-2x" style="color:#4f46e5;"></i>
            </div>
            <h3 style="margin-bottom:10px; font-size:1.4rem;">Bank Soal & Ujian</h3>
            <p style="color:var(--text-muted); font-size:0.95rem; margin-bottom:24px; line-height:1.5;">Kerjakan latihan soal dan evaluasi terstruktur lengkap dengan unggah file/kamera.</p>
            <a href="{url_for('bank_soal')}" class="btn" style="width:100%; padding:14px; background:#4f46e5;">Buka Modul &rarr;</a>
        </div>
        
        <div class="card" style="border-top: 6px solid #059669; text-align:center; padding:36px 28px;">
            <div style="width:80px; height:80px; background:rgba(5,150,105,0.1); border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 20px auto;">
                <i class="fas fa-gamepad fa-2x" style="color:#059669;"></i>
            </div>
            <h3 style="margin-bottom:10px; font-size:1.4rem;">GameMath Edukatif</h3>
            <p style="color:var(--text-muted); font-size:0.95rem; margin-bottom:24px; line-height:1.5;">Asah logika matematika melalui Ular Tangga kelompok interaktif.</p>
            <a href="{url_for('gamemath')}" class="btn btn-success" style="width:100%; padding:14px;">Main Sekarang &rarr;</a>
        </div>
        
        <div class="card" style="border-top: 6px solid #d97706; text-align:center; padding:36px 28px;">
            <div style="width:80px; height:80px; background:rgba(217,119,6,0.1); border-radius:50%; display:flex; align-items:center; justify-content:center; margin:0 auto 20px auto;">
                <i class="fas fa-trophy fa-2x" style="color:#d97706;"></i>
            </div>
            <h3 style="margin-bottom:10px; font-size:1.4rem;">Pencapaian Belajar</h3>
            <p style="color:var(--text-muted); font-size:0.95rem; margin-bottom:24px; line-height:1.5;">Pantau skor, rekap nilai ujian, dan progres perkembangan akademikmu.</p>
            <a href="{url_for('pencapaian')}" class="btn btn-warning" style="width:100%; padding:14px;">Lihat Progres &rarr;</a>
        </div>
    </div>
    """
    return render_page("Dashboard", content)

# ==========================================
# 7. FITUR MANAJEMEN SISWA
# ==========================================
@app.route('/manajemen_siswa', methods=['GET', 'POST'])
@admin_required
def manajemen_siswa():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            username = request.form.get('username').strip()
            nama = request.form.get('nama').strip()
            password = request.form.get('password').strip()
            
            if User.query.filter_by(username=username).first():
                flash(f'Username "{username}" sudah terdaftar!', 'danger')
            else:
                db.session.add(User(username=username, nama=nama, password=generate_password_hash(password), role='siswa'))
                db.session.commit()
                flash('Akun siswa baru berhasil ditambahkan!', 'success')
        elif action == 'edit':
            user_id = request.form.get('user_id')
            siswa = User.query.get(user_id)
            if siswa and siswa.role == 'siswa':
                siswa.nama = request.form.get('nama').strip()
                siswa.username = request.form.get('username').strip()
                new_pass = request.form.get('password').strip()
                if new_pass:
                    siswa.password = generate_password_hash(new_pass)
                db.session.commit()
                flash('Data siswa berhasil diperbarui!', 'success')
        elif action == 'delete':
            user_id = request.form.get('user_id')
            siswa = User.query.get(user_id)
            if siswa and siswa.role == 'siswa':
                db.session.delete(siswa)
                db.session.commit()
                flash('Akun siswa berhasil dihapus!', 'success')
        return redirect(url_for('manajemen_siswa'))

    siswas = User.query.filter_by(role='siswa').all()
    siswa_rows = ""
    for s in siswas:
        siswa_rows += f"""
        <tr>
            <td><div style="font-weight:700; color:var(--text-main);"><i class="fas fa-user-graduate" style="color:var(--primary); margin-right:8px;"></i> {s.nama}</div></td>
            <td><code style="background:#e0e7ff; padding:6px 12px; border-radius:8px; color:#4f46e5; font-weight:700;">{s.username}</code></td>
            <td>
                <button onclick="document.getElementById('editSiswa_{s.id}').showModal()" class="btn btn-sm btn-warning"><i class="fas fa-edit"></i> Edit</button>
                <form method="POST" style="display:inline;" onsubmit="return confirm('Hapus siswa ini?');">
                    <input type="hidden" name="action" value="delete">
                    <input type="hidden" name="user_id" value="{s.id}">
                    <button type="submit" class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                </form>
            </td>
        </tr>
        
        <dialog id="editSiswa_{s.id}" style="border:none; border-radius:24px; padding:36px; max-width:460px; width:90%; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
            <h3 style="margin-bottom:20px; font-size:1.4rem;"><i class="fas fa-user-edit"></i> Edit Siswa: {s.nama}</h3>
            <form method="POST">
                <input type="hidden" name="action" value="edit">
                <input type="hidden" name="user_id" value="{s.id}">
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Nama Lengkap:</label>
                <input type="text" name="nama" class="form-control" value="{s.nama}" required>
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Username:</label>
                <input type="text" name="username" class="form-control" value="{s.username}" required>
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Password Baru (kosongkan jika tetap):</label>
                <input type="password" name="password" class="form-control" placeholder="Password baru...">
                <div style="display:flex; gap:12px; margin-top:12px;">
                    <button type="submit" class="btn btn-success" style="flex:1;">Simpan</button>
                    <button type="button" class="btn btn-danger" onclick="document.getElementById('editSiswa_{s.id}').close()" style="flex:1;">Batal</button>
                </div>
            </form>
        </dialog>
        """
        
    if not siswa_rows: siswa_rows = '<tr><td colspan="3" style="text-align:center; color:var(--text-muted); padding:30px;">Belum ada akun siswa terdaftar.</td></tr>'

    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:32px;">
        <div>
            <h1 style="font-size:2rem; font-weight:800; margin-bottom:6px;">Kelola Akun Siswa</h1>
            <p style="color:var(--text-muted); font-size:1.05rem;">Tambah, ubah, atau hapus akun siswa yang dapat mengakses aplikasi.</p>
        </div>
        <button onclick="document.getElementById('formAddSiswa').showModal()" class="btn btn-success"><i class="fas fa-user-plus"></i> Tambah Siswa Baru</button>
    </div>

    <dialog id="formAddSiswa" style="border:none; border-radius:24px; padding:36px; max-width:480px; width:90%; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
        <h3 style="margin-bottom:20px; color:var(--success); font-size:1.4rem;"><i class="fas fa-user-plus"></i> Tambah Akun Siswa</h3>
        <form method="POST">
            <input type="hidden" name="action" value="add">
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Nama Lengkap:</label>
            <input type="text" name="nama" class="form-control" placeholder="Contoh: Budi Santoso" required>
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Username:</label>
            <input type="text" name="username" class="form-control" placeholder="Contoh: budisantoso" required>
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Password:</label>
            <input type="password" name="password" class="form-control" placeholder="Password akun..." required>
            <div style="display:flex; gap:12px; margin-top:12px;">
                <button type="submit" class="btn btn-success" style="flex:1;">Simpan Akun</button>
                <button type="button" class="btn btn-danger" onclick="document.getElementById('formAddSiswa').close()" style="flex:1;">Batal</button>
            </div>
        </form>
    </dialog>

    <div class="card">
        <h3 style="margin-bottom:20px; font-size:1.3rem;">Daftar Siswa Terdaftar</h3>
        <table>
            <thead><tr><th>Nama Lengkap</th><th>Username</th><th>Aksi Kontrol</th></tr></thead>
            <tbody>{siswa_rows}</tbody>
        </table>
    </div>
    """
    return render_page("Manajemen Siswa", content)

# ==========================================
# 8. KELOLA KARTU SOAL ULAR TANGGA
# ==========================================
@app.route('/kelola_kartu_ular_tangga', methods=['GET', 'POST'])
@admin_required
def kelola_kartu_ular_tangga():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'add':
            db.session.add(KartuSoalUlarTangga(
                warna=request.form.get('warna'),
                tipe_soal=request.form.get('tipe_soal'),
                pertanyaan=request.form.get('pertanyaan').strip(),
                jawaban=request.form.get('jawaban').strip(),
                keyword_jawaban=request.form.get('keyword_jawaban', '').strip()
            ))
            flash('Kartu Soal Ular Tangga berhasil ditambahkan!', 'success')
        elif action == 'edit':
            kartu = KartuSoalUlarTangga.query.get(request.form.get('kartu_id'))
            if kartu:
                kartu.warna = request.form.get('warna')
                kartu.tipe_soal = request.form.get('tipe_soal')
                kartu.pertanyaan = request.form.get('pertanyaan').strip()
                kartu.jawaban = request.form.get('jawaban').strip()
                kartu.keyword_jawaban = request.form.get('keyword_jawaban', '').strip()
                flash('Kartu Soal berhasil diperbarui!', 'success')
        elif action == 'delete':
            kartu = KartuSoalUlarTangga.query.get(request.form.get('kartu_id'))
            if kartu:
                db.session.delete(kartu)
                flash('Kartu Soal dihapus!', 'success')
        db.session.commit()
        return redirect(url_for('kelola_kartu_ular_tangga'))

    kartus = KartuSoalUlarTangga.query.all()
    rows = ""
    for k in kartus:
        color_badge_bg = {'hijau':'#d1fae5','biru':'#e0f2fe','kuning':'#fef3c7','merah':'#fee2e2'}.get(k.warna, '#e2e8f0')
        color_badge_fg = {'hijau':'#059669','biru':'#2563eb','kuning':'#d97706','merah':'#dc2626'}.get(k.warna, '#1e293b')
        
        tipe_label = "Jawaban Cepat (Angka)" if k.tipe_soal == 'angka' else "Uraian (Kata Kunci)"
        kw_info = f"<br><span style='font-size:0.8rem; color:#b45309;'><i class='fas fa-key'></i> Keyword: {k.keyword_jawaban}</span>" if k.keyword_jawaban else ""

        sel_h = "selected" if k.warna=='hijau' else ""
        sel_b = "selected" if k.warna=='biru' else ""
        sel_k = "selected" if k.warna=='kuning' else ""
        sel_m = "selected" if k.warna=='merah' else ""
        sel_t_angka = "selected" if k.tipe_soal=='angka' else ""
        sel_t_uraian = "selected" if k.tipe_soal=='uraian' else ""
        disp_kw = 'block' if k.tipe_soal=='uraian' else 'none'

        rows += f"""
        <tr>
            <td><span style="background:{color_badge_bg}; color:{color_badge_fg}; padding:6px 14px; border-radius:20px; font-weight:700; text-transform:uppercase; font-size:0.8rem;">{k.warna}</span></td>
            <td><b style="font-size:1.05rem;">{k.pertanyaan}</b><br><span style="font-size:0.75rem; color:var(--text-muted); font-weight:600;"><i class="fas fa-tag"></i> {tipe_label}</span></td>
            <td><code style="background:#e0f2ff; padding:6px 12px; border-radius:8px; font-weight:bold; color:#4f46e5;">{k.jawaban}</code>{kw_info}</td>
            <td>
                <button onclick="document.getElementById('editKartu_{k.id}').showModal()" class="btn btn-sm btn-warning"><i class="fas fa-edit"></i> Edit</button>
                <form method="POST" style="display:inline;" onsubmit="return confirm('Hapus kartu soal ini?');">
                    <input type="hidden" name="action" value="delete">
                    <input type="hidden" name="kartu_id" value="{k.id}">
                    <button type="submit" class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                </form>
            </td>
        </tr>
        
        <dialog id="editKartu_{k.id}" style="border:none; border-radius:24px; padding:36px; max-width:480px; width:90%; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
            <h3 style="margin-bottom:20px; font-size:1.4rem;"><i class="fas fa-edit"></i> Edit Kartu Soal</h3>
            <form method="POST">
                <input type="hidden" name="action" value="edit">
                <input type="hidden" name="kartu_id" value="{k.id}">
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Warna Kartu:</label>
                <select name="warna" class="form-control">
                    <option value="hijau" {sel_h}>Hijau</option>
                    <option value="biru" {sel_b}>Biru</option>
                    <option value="kuning" {sel_k}>Kuning</option>
                    <option value="merah" {sel_m}>Merah</option>
                </select>
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Tipe Soal:</label>
                <select name="tipe_soal" class="form-control" onchange="toggleEditKeyword(this.value, {k.id})">
                    <option value="angka" {sel_t_angka}>Jawaban Cepat (Angka)</option>
                    <option value="uraian" {sel_t_uraian}>Uraian (Teks / Kata Kunci)</option>
                </select>
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Pertanyaan:</label>
                <input type="text" name="pertanyaan" class="form-control" value="{k.pertanyaan}" required>
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Kunci Jawaban Utama:</label>
                <input type="text" name="jawaban" class="form-control" value="{k.jawaban}" required>
                
                <div id="editKeywordContainer_{k.id}" style="display: {disp_kw};">
                    <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;"><i class="fas fa-key"></i> Kata Kunci Guru (Pisahkan dengan koma):</label>
                    <input type="text" name="keyword_jawaban" class="form-control" placeholder="Contoh: sejajar, tegak lurus, sudut" value="{k.keyword_jawaban or ''}">
                </div>

                <div style="display:flex; gap:12px; margin-top:12px;">
                    <button type="submit" class="btn btn-success" style="flex:1;">Simpan</button>
                    <button type="button" class="btn btn-danger" onclick="document.getElementById('editKartu_{k.id}').close()" style="flex:1;">Batal</button>
                </div>
            </form>
        </dialog>
        """
        
    if not rows: rows = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted); padding:30px;">Belum ada kartu soal ular tangga.</td></tr>'

    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:32px;">
        <div>
            <h1 style="font-size:2rem; font-weight:800; margin-bottom:6px;">Kelola Kartu Soal Ular Tangga</h1>
            <p style="color:var(--text-muted); font-size:1.05rem;">Atur pertanyaan kartu interaktif berupa jawaban cepat (angka) atau uraian beserta kata kunci guru.</p>
        </div>
        <button onclick="document.getElementById('formAddKartu').showModal()" class="btn btn-success"><i class="fas fa-plus-circle"></i> Tambah Kartu Soal</button>
    </div>

    <dialog id="formAddKartu" style="border:none; border-radius:24px; padding:36px; max-width:480px; width:90%; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
        <h3 style="margin-bottom:20px; color:var(--success); font-size:1.4rem;"><i class="fas fa-plus-circle"></i> Tambah Kartu Soal Baru</h3>
        <form method="POST">
            <input type="hidden" name="action" value="add">
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Warna Kartu:</label>
            <select name="warna" class="form-control">
                <option value="hijau">Hijau</option>
                <option value="biru">Biru</option>
                <option value="kuning">Kuning</option>
                <option value="merah">Merah</option>
            </select>
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Tipe Soal:</label>
            <select name="tipe_soal" class="form-control" onchange="toggleAddKeyword(this.value)">
                <option value="angka">Jawaban Cepat (Angka)</option>
                <option value="uraian">Uraian (Teks / Kata Kunci)</option>
            </select>
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Pertanyaan Matematika:</label>
            <input type="text" name="pertanyaan" class="form-control" placeholder="Contoh: Sebutkan jenis sudut 90 derajat?" required>
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Kunci Jawaban Utama:</label>
            <input type="text" name="jawaban" class="form-control" placeholder="Contoh: Siku-siku / 90" required>
            
            <div id="addKeywordContainer" style="display:none;">
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;"><i class="fas fa-key"></i> Kata Kunci Guru (Pisahkan dengan koma):</label>
                <input type="text" name="keyword_jawaban" class="form-control" placeholder="Contoh: siku, siku-siku, 90 derajat">
            </div>

            <div style="display:flex; gap:12px; margin-top:12px;">
                <button type="submit" class="btn btn-success" style="flex:1;">Simpan Kartu</button>
                <button type="button" class="btn btn-danger" onclick="document.getElementById('formAddKartu').close()" style="flex:1;">Batal</button>
            </div>
        </form>
    </dialog>

    <script>
        function toggleAddKeyword(val) {{
            document.getElementById('addKeywordContainer').style.display = (val === 'uraian') ? 'block' : 'none';
        }}
        function toggleEditKeyword(val, kid) {{
            document.getElementById('editKeywordContainer_' + kid).style.display = (val === 'uraian') ? 'block' : 'none';
        }}
    </script>

    <div class="card">
        <h3 style="margin-bottom:20px; font-size:1.3rem;">Daftar Kartu Soal Aktif</h3>
        <table>
            <thead><tr><th>Warna</th><th>Pertanyaan & Tipe</th><th>Kunci Jawaban / Keyword</th><th>Aksi Kontrol</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """
    return render_page("Kelola Kartu Ular Tangga", content)

# ==========================================
# 9. BANK SOAL & UJIAN SISWA (DENGAN EKSPOR/IMPOR JSON)
# ==========================================
@app.route('/bank_soal', methods=['GET', 'POST'])
@login_required
def bank_soal():
    if request.method == 'POST' and session.get('role') == 'admin':
        action = request.form.get('action')
        if action == 'add':
            db.session.add(MateriSoal(
                judul=request.form.get('judul'),
                status=request.form.get('status'),
                waktu_mulai=request.form.get('waktu_mulai'),
                waktu_selesai=request.form.get('waktu_selesai'),
                durasi_menit=int(request.form.get('durasi_menit') or 60)
            ))
            flash('Materi dan Bank Soal baru berhasil ditambahkan!', 'success')
        elif action == 'edit':
            m = MateriSoal.query.get(request.form.get('id'))
            if m:
                m.judul = request.form.get('judul')
                m.status = request.form.get('status')
                m.waktu_mulai = request.form.get('waktu_mulai')
                m.waktu_selesai = request.form.get('waktu_selesai')
                m.durasi_menit = int(request.form.get('durasi_menit') or 60)
                flash('Pengaturan ujian berhasil diperbarui!', 'success')
        elif action == 'delete':
            m = MateriSoal.query.get(request.form.get('id'))
            if m: db.session.delete(m)
            flash('Materi ujian dihapus!', 'success')
        db.session.commit()
        return redirect(url_for('bank_soal'))

    materis = MateriSoal.query.all()
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    cards_html = ""
    for m in materis:
        if session.get('role') == 'admin':
            action_buttons = f"""
                <a href="{url_for('kelola_soal', materi_id=m.id)}" class="btn btn-success" style="flex:1;"><i class="fas fa-tasks"></i> Kelola Soal</a>
                <a href="{url_for('ekspor_bank_soal', materi_id=m.id)}" class="btn btn-warning" title="Ekspor ke File JSON"><i class="fas fa-file-export"></i></a>
                <button onclick="document.getElementById('editMateri_{m.id}').showModal()" class="btn btn-warning" title="Pengaturan"><i class="fas fa-cog"></i></button>
                <form method="POST" style="display:inline;" onsubmit="return confirm('Hapus materi ujian ini?');">
                    <input type="hidden" name="action" value="delete"><input type="hidden" name="id" value="{m.id}">
                    <button type="submit" class="btn btn-danger" title="Hapus"><i class="fas fa-trash"></i></button>
                </form>
            """
        else:
            status_badge = ""
            btn_kuis = ""
            sudah_dikerjakan = RiwayatPengerjaan.query.filter_by(user_id=session['user_id'], materi_id=m.id).first()
            jumlah_jawaban_siswa = JawabanSiswa.query.filter_by(user_id=session['user_id'], materi_id=m.id).count()
            
            if sudah_dikerjakan and jumlah_jawaban_siswa > 0:
                status_badge = '<span style="color:var(--success); font-weight:700;"><i class="fas fa-check-circle"></i> Selesai Dikerjakan</span>'
                btn_kuis = f'<a href="{url_for("kuis_hasil_sementara", materi_id=m.id)}" class="btn btn-success" style="flex:1;"><i class="fas fa-poll"></i> Hasil Pengerjaan</a>'
            elif m.status == 'tutup':
                status_badge = '<span style="color:var(--danger); font-weight:700;"><i class="fas fa-lock"></i> Ujian Ditutup</span>'
                btn_kuis = '<button class="btn" style="background:#cbd5e1; cursor:not-allowed; flex:1;" disabled>Ditutup</button>'
            else:
                can_start = True
                reason = ""
                if m.waktu_mulai and now_str < m.waktu_mulai.replace('T', ' '):
                    can_start = False; reason = f"Mulai: {m.waktu_mulai.replace('T', ' ')}"
                if m.waktu_selesai and now_str > m.waktu_selesai.replace('T', ' '):
                    can_start = False; reason = "Waktu Berakhir"
                
                if not can_start:
                    status_badge = f'<span style="color:var(--warning); font-size:0.85rem; font-weight:700;"><i class="fas fa-clock"></i> {reason}</span>'
                    btn_kuis = '<button class="btn" style="background:#cbd5e1; cursor:not-allowed; flex:1;" disabled>Belum / Habis</button>'
                else:
                    status_badge = '<span style="color:var(--success); font-weight:700;"><i class="fas fa-unlock"></i> Ujian Dibuka</span>'
                    btn_kuis = f'<a href="{url_for("kuis_mulai", materi_id=m.id)}" class="btn" style="flex:1; background:#4f46e5;"><i class="fas fa-play"></i> Kerjakan Soal</a>'

            action_buttons = f"""
                <div style="display:flex; flex-direction:column; width:100%; gap:12px;">
                    <div>{status_badge}</div>
                    <div style="display:flex; gap:8px;">{btn_kuis}</div>
                </div>
            """

        edit_form_modal = ""
        if session.get('role') == 'admin':
            sel_buka = "selected" if m.status=='buka' else ""
            sel_tutup = "selected" if m.status=='tutup' else ""
            edit_form_modal = f"""
            <dialog id="editMateri_{m.id}" style="border:none; border-radius:24px; padding:36px; max-width:520px; width:90%; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
                <h3 style="margin-bottom:20px; font-size:1.4rem;"><i class="fas fa-cog"></i> Pengaturan Ujian: {m.judul}</h3>
                <form method="POST">
                    <input type="hidden" name="action" value="edit"><input type="hidden" name="id" value="{m.id}">
                    <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Judul Materi:</label>
                    <input type="text" name="judul" class="form-control" value="{m.judul}" required>
                    <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Status Akses:</label>
                    <select name="status" class="form-control">
                        <option value="buka" {sel_buka}>Buka (Bisa Dikerjakan)</option>
                        <option value="tutup" {sel_tutup}>Tutup (Dikunci)</option>
                    </select>
                    <div style="display:flex; gap:12px;">
                        <div style="flex:1;"><label style="font-size:0.8rem; font-weight:bold; display:block; margin-bottom:6px;">Mulai:</label><input type="datetime-local" name="waktu_mulai" class="form-control" value="{m.waktu_mulai or ''}"></div>
                        <div style="flex:1;"><label style="font-size:0.8rem; font-weight:bold; display:block; margin-bottom:6px;">Selesai:</label><input type="datetime-local" name="waktu_selesai" class="form-control" value="{m.waktu_selesai or ''}"></div>
                    </div>
                    <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Durasi (Menit):</label>
                    <input type="number" name="durasi_menit" class="form-control" value="{m.durasi_menit or 60}" min="1" required>
                    <div style="display:flex; gap:12px; margin-top:12px;">
                        <button type="submit" class="btn btn-success" style="flex:1;">Simpan</button>
                        <button type="button" class="btn btn-danger" onclick="document.getElementById('editMateri_{m.id}').close()" style="flex:1;">Batal</button>
                    </div>
                </form>
            </dialog>
            """

        waktu_info = f"<p style='font-size:0.85rem; color:var(--text-muted); margin-bottom:18px;'><i class='fas fa-stopwatch'></i> Durasi Ujian: {m.durasi_menit} Menit</p>" if session.get('role') != 'admin' else f"<p style='font-size:0.85rem; color:var(--text-muted); margin-bottom:18px;'><i class='fas fa-stopwatch'></i> Durasi: {m.durasi_menit} Menit | Status: <b>{m.status.upper()}</b></p>"

        cards_html += f"""
        <div class="card" style="display:flex; flex-direction:column; border-top: 6px solid #4f46e5;">
            <h3 style="margin-bottom:8px; font-size:1.3rem;">{m.judul}</h3>
            <p style="color:var(--text-muted); font-size:0.95rem; margin-bottom:8px;"><i class="fas fa-list-ol"></i> {len(m.soals)} Butir Soal Tersedia</p>
            {waktu_info}
            <div style="margin-top:auto; display:flex; gap:8px; align-items:center;">{action_buttons}</div>
            {edit_form_modal}
        </div>
        """
        
    if not cards_html: cards_html = "<div class='card' style='text-align:center; color:var(--text-muted); padding:40px;'><p>Belum ada materi soal atau ujian yang aktif.</p></div>"

    if session.get('role') == 'admin':
        add_form_html = f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:32px;">
            <div>
                <h1 style="font-size:2rem; font-weight:800; margin-bottom:6px;">Bank Soal & Ujian Interaktif</h1>
                <p style="color:var(--text-muted); font-size:1.05rem;">Modul latihan pilihan ganda dan uraian evaluasi belajar siswa.</p>
            </div>
            <div style="display:flex; gap:10px;">
                <button onclick="document.getElementById('formImporBankSoal').showModal()" class="btn btn-warning"><i class="fas fa-file-import"></i> Impor dari File JSON</button>
                <button onclick="document.getElementById('formAddMateri').showModal()" class="btn btn-success"><i class="fas fa-plus"></i> Tambah Bank Soal</button>
            </div>
        </div>
        
        <dialog id="formImporBankSoal" style="border:none; border-radius:24px; padding:36px; max-width:480px; width:90%; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
            <h3 style="margin-bottom:20px; color:var(--warning); font-size:1.4rem;"><i class="fas fa-file-import"></i> Impor Bank Soal (.json)</h3>
            <form method="POST" action="{url_for('impor_bank_soal')}" enctype="multipart/form-data">
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Pilih File Cadangan JSON:</label>
                <input type="file" name="file_json" class="form-control" accept=".json" required>
                <div style="display:flex; gap:12px; margin-top:12px;">
                    <button type="submit" class="btn btn-success" style="flex:1;">Unggah & Impor</button>
                    <button type="button" class="btn btn-danger" onclick="document.getElementById('formImporBankSoal').close()" style="flex:1;">Batal</button>
                </div>
            </form>
        </dialog>
        
        <dialog id="formAddMateri" style="border:none; border-radius:24px; padding:36px; max-width:520px; width:90%; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
            <h3 style="margin-bottom:20px; color:var(--success); font-size:1.4rem;"><i class="fas fa-book-medical"></i> Buat Bank Soal Baru</h3>
            <form method="POST">
                <input type="hidden" name="action" value="add">
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Judul Materi / Ujian:</label>
                <input type="text" name="judul" class="form-control" placeholder="Contoh: Evaluasi Bab Aljabar Lanjutan" required>
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Status Ujian:</label>
                <select name="status" class="form-control"><option value="buka">Buka</option><option value="tutup">Tutup</option></select>
                <div style="display:flex; gap:12px;">
                    <div style="flex:1;"><label style="font-size:0.8rem; font-weight:bold; display:block; margin-bottom:6px;">Mulai:</label><input type="datetime-local" name="waktu_mulai" class="form-control"></div>
                    <div style="flex:1;"><label style="font-size:0.8rem; font-weight:bold; display:block; margin-bottom:6px;">Selesai:</label><input type="datetime-local" name="waktu_selesai" class="form-control"></div>
                </div>
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Durasi Pengerjaan (Menit):</label>
                <input type="number" name="durasi_menit" class="form-control" value="60" min="1" required>
                <div style="display:flex; gap:12px; margin-top:12px;">
                    <button type="submit" class="btn btn-success" style="flex:1;">Simpan Bank Soal</button>
                    <button type="button" class="btn btn-danger" onclick="document.getElementById('formAddMateri').close()" style="flex:1;">Batal</button>
                </div>
            </form>
        </dialog>
        """
    else:
        add_form_html = '<div style="margin-bottom:32px;"><h1 style="font-size:2rem; font-weight:800; margin-bottom:6px;">Bank Soal & Ujian Interaktif</h1><p style="color:var(--text-muted); font-size:1.05rem;">Pilih ujian yang tersedia untuk mulai mengerjakan tes.</p></div>'

    content = f"{add_form_html}<div class=\"grid-3\">{cards_html}</div>"
    return render_page("Bank Soal", content)

@app.route('/bank_soal/ekspor/<int:materi_id>')
@admin_required
def ekspor_bank_soal(materi_id):
    materi = MateriSoal.query.get_or_404(materi_id)
    
    data_export = {
        "judul": materi.judul,
        "status": materi.status,
        "waktu_mulai": materi.waktu_mulai,
        "waktu_selesai": materi.waktu_selesai,
        "durasi_menit": materi.durasi_menit,
        "soals": []
    }
    
    for s in materi.soals:
        data_export["soals"].append({
            "tipe": s.tipe,
            "pertanyaan": s.pertanyaan,
            "foto": s.foto,
            "pilihan_a": s.pilihan_a,
            "pilihan_b": s.pilihan_b,
            "pilihan_c": s.pilihan_c,
            "pilihan_d": s.pilihan_d,
            "kunci_jawaban": s.kunci_jawaban,
            "keyword_jawaban": s.keyword_jawaban,
            "pembahasan": s.pembahasan,
            "poin_soal": s.poin_soal
        })
        
    filename = secure_filename(f"bank_soal_{materi.judul.lower().replace(' ', '_')}.json")
    filepath = os.path.join(BACKUP_FOLDER, filename)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data_export, f, ensure_ascii=False, indent=4)
        
    return send_file(filepath, as_attachment=True, download_name=filename)

@app.route('/bank_soal/impor', methods=['POST'])
@admin_required
def impor_bank_soal():
    file_json = request.files.get('file_json')
    if not file_json or file_json.filename == '':
        flash('File JSON tidak valid atau tidak dipilih!', 'danger')
        return redirect(url_for('bank_soal'))
        
    try:
        content = file_json.read().decode('utf-8')
        data = json.loads(content)
        
        m_baru = MateriSoal(
            judul=data.get('judul', 'Ujian Impor JSON'),
            status=data.get('status', 'buka'),
            waktu_mulai=data.get('waktu_mulai'),
            waktu_selesai=data.get('waktu_selesai'),
            durasi_menit=data.get('durasi_menit', 60)
        )
        db.session.add(m_baru)
        db.session.commit()
        
        for s_data in data.get('soals', []):
            db.session.add(SoalDetail(
                materi_id=m_baru.id,
                tipe=s_data.get('tipe', 'pg'),
                pertanyaan=s_data.get('pertanyaan', ''),
                foto=s_data.get('foto'),
                pilihan_a=s_data.get('pilihan_a'),
                pilihan_b=s_data.get('pilihan_b'),
                pilihan_c=s_data.get('pilihan_c'),
                pilihan_d=s_data.get('pilihan_d'),
                kunci_jawaban=s_data.get('kunci_jawaban', ''),
                keyword_jawaban=s_data.get('keyword_jawaban'),
                pembahasan=s_data.get('pembahasan'),
                poin_soal=s_data.get('poin_soal', 10.0)
            ))
        db.session.commit()
        flash('Bank soal beserta seluruh butir soal berhasil diimpor dari file JSON!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Gagal mengimpor file JSON: {str(e)}', 'danger')
        
    return redirect(url_for('bank_soal'))

@app.route('/kelola_soal/<int:materi_id>', methods=['GET', 'POST'])
@admin_required
def kelola_soal(materi_id):
    materi = MateriSoal.query.get_or_404(materi_id)
    if request.method == 'POST':
        action = request.form.get('action')
        foto_file = request.files.get('foto')
        filename = None
        if foto_file and foto_file.filename != '':
            filename = secure_filename(foto_file.filename)
            foto_file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        if action == 'add':
            db.session.add(SoalDetail(
                materi_id=materi.id, tipe=request.form.get('tipe'),
                pertanyaan=request.form.get('pertanyaan'), foto=filename,
                pilihan_a=request.form.get('pilihan_a'), pilihan_b=request.form.get('pilihan_b'),
                pilihan_c=request.form.get('pilihan_c'), pilihan_d=request.form.get('pilihan_d'),
                kunci_jawaban=request.form.get('kunci_jawaban').strip(),
                keyword_jawaban=request.form.get('keyword_jawaban', '').strip(),
                pembahasan=request.form.get('pembahasan', '').strip(),
                poin_soal=float(request.form.get('poin_soal') or 10.0)
            ))
            flash('Butir soal berhasil ditambahkan!', 'success')
        elif action == 'edit':
            s = SoalDetail.query.get(request.form.get('soal_id'))
            if s:
                s.tipe = request.form.get('tipe')
                s.pertanyaan = request.form.get('pertanyaan')
                if filename: s.foto = filename
                s.pilihan_a = request.form.get('pilihan_a')
                s.pilihan_b = request.form.get('pilihan_b')
                s.pilihan_c = request.form.get('pilihan_c')
                s.pilihan_d = request.form.get('pilihan_d')
                s.kunci_jawaban = request.form.get('kunci_jawaban').strip()
                s.keyword_jawaban = request.form.get('keyword_jawaban', '').strip()
                s.pembahasan = request.form.get('pembahasan', '').strip()
                s.poin_soal = float(request.form.get('poin_soal') or 10.0)
                flash('Soal berhasil diperbarui!', 'success')
        elif action == 'delete':
            s = SoalDetail.query.get(request.form.get('soal_id'))
            if s: db.session.delete(s)
            flash('Soal berhasil dihapus!', 'success')
        db.session.commit()
        return redirect(url_for('kelola_soal', materi_id=materi.id))

    soal_list_html = ""
    for idx, s in enumerate(materi.soals, 1):
        pg_details = ""
        if s.tipe == 'pg':
            pg_details = f"""
            <div style="display:grid; grid-template-columns: 1fr 1fr; gap:12px; margin: 18px 0;">
                <div style="background:#f8fafc; padding:14px; border-radius:12px; border:1px solid #e2e8f0;"><b>A.</b> {s.pilihan_a}</div>
                <div style="background:#f8fafc; padding:14px; border-radius:12px; border:1px solid #e2e8f0;"><b>B.</b> {s.pilihan_b}</div>
                <div style="background:#f8fafc; padding:14px; border-radius:12px; border:1px solid #e2e8f0;"><b>C.</b> {s.pilihan_c}</div>
                <div style="background:#f8fafc; padding:14px; border-radius:12px; border:1px solid #e2e8f0;"><b>D.</b> {s.pilihan_d}</div>
            </div>
            """
        
        foto_display = f'<img src="{url_for("static", filename="uploads/" + s.foto)}" style="max-height:240px; border-radius:14px; display:block; margin: 16px 0; border: 1px solid #cbd5e1;" alt="Foto Soal">' if s.foto else ''
        keyword_display = f'<div style="margin-top:10px; font-size:0.9rem; color:#b45309;"><i class="fas fa-key"></i> <b>Keyword Koreksi Otomatis:</b> {s.keyword_jawaban}</div>' if s.keyword_jawaban else ''
        pembahasan_display = f'<div style="margin-top:10px; font-size:0.95rem; color:#1e40af;"><i class="fas fa-lightbulb"></i> <b>Pembahasan:</b> {s.pembahasan}</div>' if s.pembahasan else ''

        sel_pg = "selected" if s.tipe=='pg' else ""
        sel_ur = "selected" if s.tipe=='uraian' else ""
        disp_pg = 'block' if s.tipe=='pg' else 'none'

        soal_list_html += f"""
        <div class="card" style="position:relative; margin-bottom:24px;">
            <div style="position:absolute; top:24px; right:24px; display:flex; gap:8px;">
                <button onclick="document.getElementById('editSoal_{s.id}').showModal()" class="btn btn-sm btn-warning"><i class="fas fa-edit"></i> Edit</button>
                <form method="POST" onsubmit="return confirm('Hapus soal ini?');" style="margin:0;">
                    <input type="hidden" name="action" value="delete"><input type="hidden" name="soal_id" value="{s.id}">
                    <button type="submit" class="btn btn-sm btn-danger"><i class="fas fa-trash"></i></button>
                </form>
            </div>
            
            <h4 style="color:#4f46e5; margin-bottom:12px; font-size:1.1rem;">Soal #{idx} &bull; <span style="text-transform:uppercase; font-size:0.75rem; background:#e0e7ff; color:#4f46e5; padding:4px 12px; border-radius:20px; font-weight:700;">{s.tipe}</span> &bull; <span style="font-size:0.85rem; color:var(--success);">Poin: {s.poin_soal}</span></h4>
            <div style="white-space:pre-wrap; font-size:1.05rem; margin-bottom:14px; font-weight:500; line-height:1.6;">{s.pertanyaan}</div>
            {foto_display}
            {pg_details}
            <div style="margin-top:18px; padding:14px 20px; background:#ecfdf5; border-radius:14px; border:1px solid #a7f3d0;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                    <i class="fas fa-key" style="color:var(--success);"></i>
                    <span style="font-size:0.75rem; color:#065f46; font-weight:bold; letter-spacing:0.5px;">KUNCI JAWABAN GURU:</span>
                </div>
                <div style="white-space:pre-wrap; font-weight:700; color:#047857; font-size:1.05rem; line-height:1.5;">{s.kunci_jawaban}</div>
                {keyword_display}
                {pembahasan_display}
            </div>
        </div>

        <dialog id="editSoal_{s.id}" style="border:none; border-radius:24px; padding:36px; max-width:600px; width:95%; max-height:90vh; overflow-y:auto; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
            <h3 style="margin-bottom:20px; font-size:1.4rem;"><i class="fas fa-edit"></i> Edit Soal #{idx}</h3>
            <form method="POST" enctype="multipart/form-data">
                <input type="hidden" name="action" value="edit"><input type="hidden" name="soal_id" value="{s.id}">
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Tipe Soal:</label>
                <select name="tipe" class="form-control" onchange="document.getElementById('edit_pg_{s.id}').style.display = (this.value === 'pg') ? 'block' : 'none';">
                    <option value="pg" {sel_pg}>Pilihan Ganda</option>
                    <option value="uraian" {sel_ur}>Uraian / Isian Singkat</option>
                </select>
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Pertanyaan:</label>
                <textarea name="pertanyaan" class="form-control" rows="3" required>{s.pertanyaan}</textarea>
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Ganti Foto (Opsional):</label>
                <input type="file" name="foto" class="form-control" accept="image/*">
                
                <div id="edit_pg_{s.id}" style="display: {disp_pg};">
                    <input type="text" name="pilihan_a" class="form-control" placeholder="Pilihan A" value="{s.pilihan_a or ''}">
                    <input type="text" name="pilihan_b" class="form-control" placeholder="Pilihan B" value="{s.pilihan_b or ''}">
                    <input type="text" name="pilihan_c" class="form-control" placeholder="Pilihan C" value="{s.pilihan_c or ''}">
                    <input type="text" name="pilihan_d" class="form-control" placeholder="Pilihan D" value="{s.pilihan_d or ''}">
                </div>
                
                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Kunci Jawaban Benar:</label>
                <textarea name="kunci_jawaban" class="form-control" rows="3" required>{s.kunci_jawaban}</textarea>

                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;"><i class="fas fa-key"></i> Keyword / Angka Kunci Otomatis (Uraian):</label>
                <input type="text" name="keyword_jawaban" class="form-control" placeholder="Pisahkan dengan koma, misal: 25, x, 3.14" value="{s.keyword_jawaban or ''}">

                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;"><i class="fas fa-lightbulb"></i> Pembahasan Soal:</label>
                <textarea name="pembahasan" class="form-control" rows="3" placeholder="Tuliskan pembahasan jawaban...">{s.pembahasan or ''}</textarea>

                <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Bobot Poin Soal:</label>
                <input type="number" step="0.5" name="poin_soal" class="form-control" value="{s.poin_soal}" required>

                <div style="display:flex; gap:12px; margin-top:16px;">
                    <button type="submit" class="btn btn-success" style="flex:1;">Simpan</button>
                    <button type="button" class="btn btn-danger" onclick="document.getElementById('editSoal_{s.id}').close()" style="flex:1;">Batal</button>
                </div>
            </form>
        </dialog>
        """

    content = f"""
    <a href="{url_for('bank_soal')}" class="btn" style="background:#64748b; margin-bottom:24px;"><i class="fas fa-arrow-left"></i> Kembali ke Daftar Bank Soal</a>
    
    <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color:white; padding:36px; border-radius:24px; margin-bottom:32px; box-shadow: 0 15px 35px rgba(79,70,229,0.15);">
        <h1 style="margin-bottom:8px; font-size:2rem;"><i class="fas fa-tasks"></i> Kelola Butir Soal</h1>
        <p style="color:#c7d2fe; font-size:1.1rem;">Materi: <b>{materi.judul}</b></p>
    </div>
    
    <div class="card" style="background:#f8fafc; border:2px dashed var(--success); margin-bottom:32px;">
        <h3 style="margin-bottom:20px; color:var(--success); font-size:1.3rem;"><i class="fas fa-plus-circle"></i> Tambah Soal Baru</h3>
        <form method="POST" enctype="multipart/form-data">
            <input type="hidden" name="action" value="add">
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Tipe Soal:</label>
            <select name="tipe" class="form-control" onchange="document.getElementById('pg-options').style.display = (this.value === 'pg') ? 'block' : 'none';">
                <option value="pg">Pilihan Ganda</option>
                <option value="uraian">Uraian / Isian Singkat</option>
            </select>
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Pertanyaan:</label>
            <textarea name="pertanyaan" class="form-control" rows="3" placeholder="Tuliskan pertanyaan tes..." required></textarea>
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Foto Pendukung (Opsional):</label>
            <input type="file" name="foto" class="form-control" accept="image/*">
            
            <div id="pg-options">
                <input type="text" name="pilihan_a" class="form-control" placeholder="Pilihan A">
                <input type="text" name="pilihan_b" class="form-control" placeholder="Pilihan B">
                <input type="text" name="pilihan_c" class="form-control" placeholder="Pilihan C">
                <input type="text" name="pilihan_d" class="form-control" placeholder="Pilihan D">
            </div>
            
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Kunci Jawaban Benar:</label>
            <textarea name="kunci_jawaban" class="form-control" rows="3" placeholder="Contoh: A atau uraian kunci..." required></textarea>

            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;"><i class="fas fa-key"></i> Keyword / Angka Kunci Otomatis (Uraian):</label>
            <input type="text" name="keyword_jawaban" class="form-control" placeholder="Kata kunci atau angka, dipisahkan koma (misal: 25, x, 3.14)">

            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;"><i class="fas fa-lightbulb"></i> Pembahasan Soal:</label>
            <textarea name="pembahasan" class="form-control" rows="3" placeholder="Tuliskan pembahasan lengkap untuk siswa..."></textarea>

            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Bobot Poin Soal:</label>
            <input type="number" step="0.5" name="poin_soal" class="form-control" value="10.0" required>

            <button type="submit" class="btn btn-success" style="width:100%; padding:14px; font-size:1.05rem; margin-top:8px;">Simpan Soal</button>
        </form>
    </div>
    {soal_list_html}
    """
    return render_page(f"Kelola Soal - {materi.judul}", content)

@app.route('/kuis/mulai/<int:materi_id>')
@login_required
def kuis_mulai(materi_id):
    materi = MateriSoal.query.get_or_404(materi_id)
    sudah_dikerjakan = RiwayatPengerjaan.query.filter_by(user_id=session['user_id'], materi_id=materi_id).first()
    jumlah_jawaban_siswa = JawabanSiswa.query.filter_by(user_id=session['user_id'], materi_id=materi_id).count()
    
    if sudah_dikerjakan and jumlah_jawaban_siswa > 0:
        flash('Anda sudah pernah mengerjakan ujian ini.', 'danger')
        return redirect(url_for('bank_soal'))
    if materi.status == 'tutup':
        flash('Ujian sedang ditutup oleh guru.', 'danger')
        return redirect(url_for('bank_soal'))
        
    soal_ids = [s.id for s in materi.soals]
    session['kuis'] = {
        'materi_id': materi_id, 
        'soal_ids': soal_ids, 
        'current_idx': 0,
        'jawaban_sementara': {},
        'end_time': datetime.now().timestamp() + (materi.durasi_menit * 60)
    }
    return redirect(url_for('kuis_soal', idx=0))

@app.route('/kuis/soal/<int:idx>', methods=['GET', 'POST'])
@login_required
def kuis_soal(idx):
    kuis_state = session.get('kuis')
    if not kuis_state: return redirect(url_for('bank_soal'))
    
    soal_ids = kuis_state['soal_ids']
    if idx < 0 or idx >= len(soal_ids): return redirect(url_for('kuis_konfirmasi'))
    
    kuis_state['current_idx'] = idx
    session.modified = True
    soal = SoalDetail.query.get(soal_ids[idx])

    if request.method == 'POST':
        jawaban_user = request.form.get('jawaban', '').strip()
        
        lampiran_file = request.files.get('lampiran_file')
        lampiran_filename = kuis_state.get('lampiran_sementara', {}).get(str(soal.id))
        
        if lampiran_file and lampiran_file.filename != '':
            lampiran_filename = secure_filename(f"user_{session['user_id']}_{datetime.now().strftime('%Y%m%d%H%M%S')}_{lampiran_file.filename}")
            lampiran_file.save(os.path.join(app.config['UPLOAD_FOLDER'], lampiran_filename))
            if 'lampiran_sementara' not in kuis_state: kuis_state['lampiran_sementara'] = {}
            kuis_state['lampiran_sementara'][str(soal.id)] = lampiran_filename

        kuis_state['jawaban_sementara'][str(soal.id)] = jawaban_user
        session.modified = True
        
        aksi = request.form.get('aksi')
        if aksi == 'lanjut':
            return redirect(url_for('kuis_soal', idx=idx+1))
        elif aksi == 'sebelumnya':
            return redirect(url_for('kuis_soal', idx=idx-1))
        elif aksi == 'selesai':
            return redirect(url_for('kuis_konfirmasi'))

    saved_ans = kuis_state['jawaban_sementara'].get(str(soal.id), '')
    saved_file = kuis_state.get('lampiran_sementara', {}).get(str(soal.id), '')
    end_time_ts = kuis_state.get('end_time', datetime.now().timestamp() + 3600)

    nav_buttons = ""
    for i, sid in enumerate(soal_ids):
        is_answered = bool(kuis_state['jawaban_sementara'].get(str(sid), '').strip())
        bg_color = "#059669" if is_answered else "#e2e8f0"
        text_color = "white" if is_answered else "#475569"
        border_style = "border: 3px solid #1e1b4b;" if i == idx else "border: 1px solid transparent;"
        
        nav_buttons += f"""
        <a href="{url_for('kuis_soal', idx=i)}" style="width:40px; height:40px; background:{bg_color}; color:{text_color}; display:flex; align-items:center; justify-content:center; border-radius:10px; font-weight:700; font-size:0.95rem; {border_style} text-decoration:none; transition:all 0.2s;" title="Soal {i+1}">{i+1}</a>
        """

    file_upload_section = f"""
    <div style="margin-top:24px; padding:20px; background:#f8fafc; border-radius:16px; border:2px dashed var(--border-color);">
        <label style="font-size:0.9rem; font-weight:700; color:var(--text-main); display:block; margin-bottom:8px;"><i class="fas fa-camera"></i> Unggah Foto / Lampiran Jawaban (Opsional - Kamera / File):</label>
        <input type="file" name="lampiran_file" class="form-control" accept="image/*" capture="environment" style="margin-bottom:6px;">
        <span style="font-size:0.8rem; color:var(--text-muted);">Anda dapat langsung mengambil foto dari kamera HP/laptop atau memilih file gambar dari galeri.</span>
        {f'<br><div style="margin-top:10px;"><i class="fas fa-check-circle" style="color:var(--success);"></i> <b>File terlampir:</b> {saved_file}</div>' if saved_file else ''}
    </div>
    """

    if soal.tipe == 'pg':
        input_html = f"""
        <label style="display:flex; gap:16px; align-items:center; padding:18px; border:2px solid var(--border-color); border-radius:14px; margin-bottom:14px; cursor:pointer; background:#f8fafc; transition:all 0.2s;">
            <input type="radio" name="jawaban" value="A" {'checked' if saved_ans=='A' else ''} style="width:20px; height:20px;"> <span style="font-size:1.05rem;"><b>A.</b> {soal.pilihan_a}</span>
        </label>
        <label style="display:flex; gap:16px; align-items:center; padding:18px; border:2px solid var(--border-color); border-radius:14px; margin-bottom:14px; cursor:pointer; background:#f8fafc; transition:all 0.2s;">
            <input type="radio" name="jawaban" value="B" {'checked' if saved_ans=='B' else ''} style="width:20px; height:20px;"> <span style="font-size:1.05rem;"><b>B.</b> {soal.pilihan_b}</span>
        </label>
        <label style="display:flex; gap:16px; align-items:center; padding:18px; border:2px solid var(--border-color); border-radius:14px; margin-bottom:14px; cursor:pointer; background:#f8fafc; transition:all 0.2s;">
            <input type="radio" name="jawaban" value="C" {'checked' if saved_ans=='C' else ''} style="width:20px; height:20px;"> <span style="font-size:1.05rem;"><b>C.</b> {soal.pilihan_c}</span>
        </label>
        <label style="display:flex; gap:16px; align-items:center; padding:18px; border:2px solid var(--border-color); border-radius:14px; margin-bottom:14px; cursor:pointer; background:#f8fafc; transition:all 0.2s;">
            <input type="radio" name="jawaban" value="D" {'checked' if saved_ans=='D' else ''} style="width:20px; height:20px;"> <span style="font-size:1.05rem;"><b>D.</b> {soal.pilihan_d}</span>
        </label>
        {file_upload_section}
        """
    else:
        input_html = f"""
        <textarea name="jawaban" class="form-control" rows="5" placeholder="Ketik jawaban uraian Anda di sini..." style="font-size:1.1rem;">{saved_ans}</textarea>
        {file_upload_section}
        """

    foto_html = f'<img src="{url_for("static", filename="uploads/" + soal.foto)}" style="max-width:100%; max-height:380px; border-radius:14px; margin-bottom:24px; display:block; border:1px solid #cbd5e1;" alt="Foto Soal">' if soal.foto else ''

    prev_btn_style = "display:none;" if idx == 0 else "display:inline-flex;"
    next_btn_label = "Selesai / Konfirmasi &rarr;" if idx == len(soal_ids) - 1 else "Simpan & Lanjut &rarr;"
    next_aksi_val = "selesai" if idx == len(soal_ids) - 1 else "lanjut"
    url_konf = url_for('kuis_konfirmasi')

    content = f"""
    <div style="display: grid; grid-template-columns: 1fr 360px; gap: 28px; align-items: start;">
        <div>
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
                <span style="background:var(--primary); color:white; padding:8px 18px; border-radius:20px; font-weight:700; font-size:0.9rem;">Soal Nomor {idx+1} dari {len(soal_ids)} (Bobot Poin: {soal.poin_soal})</span>
            </div>
            
            <div class="card" style="padding:40px;">
                <p style="font-size:1.25rem; font-weight:600; line-height:1.6; margin-bottom:24px; color:var(--text-main);">{soal.pertanyaan}</p>
                {foto_html}
                
                <form method="POST" enctype="multipart/form-data">
                    {input_html}
                    <div style="display:flex; justify-content:space-between; gap:12px; margin-top:24px;">
                        <button type="submit" name="aksi" value="sebelumnya" class="btn" style="background:#64748b; {prev_btn_style} padding:14px 24px;"><i class="fas fa-arrow-left"></i> Sebelumnya</button>
                        <button type="submit" name="aksi" value="{next_aksi_val}" class="btn btn-success" style="margin-left:auto; padding:14px 28px; font-size:1.1rem;">{next_btn_label}</button>
                    </div>
                </form>
            </div>
        </div>

        <div class="card" style="position: sticky; top: 20px; padding: 28px; border-top: 6px solid var(--danger);">
            <div style="text-align: center; margin-bottom: 24px; background: #fee2e2; padding: 20px; border-radius: 16px; border: 1px solid #fecaca;">
                <span style="font-size: 0.8rem; font-weight: bold; color: var(--danger); text-transform: uppercase; display: block; margin-bottom: 6px; letter-spacing: 0.5px;"><i class="fas fa-clock"></i> Sisa Waktu Ujian</span>
                <div id="countdownTimer" style="font-size: 2rem; font-weight: 800; color: #dc2626; letter-spacing: 1px;">00:00:00</div>
            </div>

            <div style="font-size: 0.9rem; font-weight: bold; color: var(--text-muted); margin-bottom: 14px; display: flex; justify-content: space-between; align-items: center;">
                <span><i class="fas fa-th"></i> Navigasi Soal</span>
            </div>
            <div style="display:flex; gap:10px; flex-wrap:wrap; margin-bottom: 20px;">{nav_buttons}</div>
            
            <div style="font-size: 0.8rem; color: var(--text-muted); border-top: 1px solid var(--border-color); padding-top: 16px; display: flex; justify-content: space-between;">
                <span><b style="color:var(--success); font-size:1.1rem;">■</b> Terjawab</span>
                <span><b style="color:#cbd5e1; font-size:1.1rem;">■</b> Belum</span>
            </div>
        </div>
    </div>

    <script>
        const endTime = {end_time_ts} * 1000;
        function updateTimer() {{
            const now = new Date().getTime();
            const distance = endTime - now;
            
            if (distance < 0) {{
                document.getElementById("countdownTimer").innerText = "Waktu Habis!";
                alert("Waktu ujian telah habis! Sistem akan mengirimkan jawaban Anda secara otomatis.");
                window.location.href = "{url_konf}";
                return;
            }}
            
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            document.getElementById("countdownTimer").innerText = 
                String(hours).padStart(2, '0') + ":" + 
                String(minutes).padStart(2, '0') + ":" + 
                String(seconds).padStart(2, '0');
        }}
        setInterval(updateTimer, 1000);
        updateTimer();
    </script>
    """
    return render_page(f"Ujian - Soal {idx+1}", content)

@app.route('/kuis/konfirmasi', methods=['GET', 'POST'])
@login_required
def kuis_konfirmasi():
    kuis_state = session.get('kuis')
    if not kuis_state: return redirect(url_for('bank_soal'))
    
    materi = MateriSoal.query.get_or_404(kuis_state['materi_id'])
    soal_ids = kuis_state['soal_ids']
    
    if request.method == 'POST':
        total_otomatis_nilai = 0.0
        
        for sid_str, jwb in kuis_state['jawaban_sementara'].items():
            sid = int(sid_str)
            soal_obj = SoalDetail.query.get(sid)
            lampiran_file = kuis_state.get('lampiran_sementara', {}).get(sid_str)
            
            poin_diberikan = 0.0
            status_kor = 'Menunggu Koreksi'
            
            jwb_clean = jwb.strip().lower()
            kunci_clean = soal_obj.kunci_jawaban.strip().lower()

            if soal_obj.tipe == 'pg':
                if jwb_clean == kunci_clean:
                    poin_diberikan = soal_obj.poin_soal
                    status_kor = 'Dinilai Otomatis'
                else:
                    poin_diberikan = 0.0
                    status_kor = 'Dinilai Otomatis'
            elif soal_obj.tipe == 'uraian':
                matched = False
                
                angka_siswa = set(re.findall(r'\d+(?:\.\d+)?', jwb_clean))
                angka_kunci = set(re.findall(r'\d+(?:\.\d+)?', kunci_clean))
                
                if soal_obj.keyword_jawaban:
                    for kw in soal_obj.keyword_jawaban.split(','):
                        kw_clean = kw.strip().lower()
                        if kw_clean:
                            angka_kunci.update(re.findall(r'\d+(?:\.\d+)?', kw_clean))

                if angka_siswa and angka_kunci and not angka_siswa.isdisjoint(angka_kunci):
                    matched = True
                else:
                    all_keywords = []
                    if soal_obj.keyword_jawaban:
                        all_keywords = [kw.strip().lower() for kw in soal_obj.keyword_jawaban.split(',') if kw.strip()]
                    
                    kunci_words = [w.strip(".,;()[]{}'\":?!") for w in kunci_clean.split() if len(w) > 1]
                    
                    for kw in all_keywords:
                        if kw in jwb_clean:
                            matched = True
                            break
                    
                    if not matched:
                        jwb_tokens = set(w.strip(".,;()[]{}'\":?!") for w in jwb_clean.split())
                        for kw in all_keywords:
                            if kw in jwb_tokens:
                                matched = True
                                break
                        
                        if not all_keywords:
                            common = set(kunci_words).intersection(jwb_tokens)
                            if len(common) > 0:
                                matched = True

                if matched:
                    poin_diberikan = soal_obj.poin_soal
                    status_kor = 'Dinilai Otomatis (Match Angka/Keyword)'
                else:
                    poin_diberikan = 0.0
                    status_kor = 'Menunggu Koreksi Guru'

            total_otomatis_nilai += poin_diberikan

            js = JawabanSiswa.query.filter_by(user_id=session['user_id'], materi_id=materi.id, soal_id=sid).first()
            if js:
                js.jawaban_teks = jwb
                if lampiran_file: js.lampiran_file = lampiran_file
                js.nilai_diperoleh = poin_diberikan
                js.status_koreksi = status_kor
            else:
                db.session.add(JawabanSiswa(
                    user_id=session['user_id'], materi_id=materi.id, soal_id=sid,
                    jawaban_teks=jwb, lampiran_file=lampiran_file,
                    nilai_diperoleh=poin_diberikan, status_koreksi=status_kor
                ))
        
        riwayat_ada = RiwayatPengerjaan.query.filter_by(user_id=session['user_id'], materi_id=materi.id).first()
        if riwayat_ada:
            riwayat_ada.skor_tertinggi = total_otomatis_nilai
            riwayat_ada.status_ujian = 'Selesai Dikerjakan'
            riwayat_ada.terakhir_dikerjakan = datetime.now()
        else:
            db.session.add(RiwayatPengerjaan(
                user_id=session['user_id'], materi_id=materi.id,
                skor_tertinggi=total_otomatis_nilai, status_ujian='Selesai Dikerjakan'
            ))
            
        db.session.commit()
        session.pop('kuis', None)
        return redirect(url_for('kuis_selesai'))

    ringkasan_rows = ""
    terjawab_count = 0
    for i, sid in enumerate(soal_ids):
        ans = kuis_state['jawaban_sementara'].get(str(sid), '').strip()
        if ans: terjawab_count += 1
        
        status_badge = '<span style="color:var(--success); font-weight:700;"><i class="fas fa-check-circle"></i> Terjawab</span>' if ans else '<span style="color:var(--danger); font-weight:700;"><i class="fas fa-exclamation-triangle"></i> Belum (Kosong)</span>'
        preview_ans = ans if ans else '(Belum diisi)'
        
        ringkasan_rows += f"""
        <tr>
            <td style="font-weight:bold;">Soal #{i+1}</td>
            <td>{status_badge}</td>
            <td><code style="background:#f1f5f9; padding:6px 12px; border-radius:8px; font-weight:600;">{preview_ans}</code></td>
            <td><a href="{url_for('kuis_soal', idx=i)}" class="btn btn-sm btn-warning"><i class="fas fa-edit"></i> Revisi</a></td>
        </tr>
        """

    content = f"""
    <div style="max-width:850px; margin:0 auto;">
        <div class="card" style="padding:48px;">
            <div style="text-align:center; margin-bottom:32px;">
                <div style="font-size:4rem; color:var(--warning); margin-bottom:14px;"><i class="fas fa-clipboard-check"></i></div>
                <h2 style="font-size:2rem; margin-bottom:8px; font-weight:800;">Konfirmasi & Verifikasi Jawaban</h2>
                <p style="color:var(--text-muted); font-size:1.1rem;">Periksa ringkasan jawaban ujian <b>{materi.judul}</b> sebelum dikirim.</p>
            </div>
            
            <div style="background:#f8fafc; padding:20px; border-radius:16px; margin-bottom:28px; display:flex; justify-content:space-around; text-align:center; border:1px solid var(--border-color);">
                <div><span style="font-size:0.85rem; color:var(--text-muted); display:block; margin-bottom:4px;">Total Soal</span><b style="font-size:1.4rem;">{len(soal_ids)}</b></div>
                <div><span style="font-size:0.85rem; color:var(--text-muted); display:block; margin-bottom:4px;">Sudah Terjawab</span><b style="font-size:1.4rem; color:var(--success);">{terjawab_count}</b></div>
                <div><span style="font-size:0.85rem; color:var(--text-muted); display:block; margin-bottom:4px;">Belum Terjawab</span><b style="font-size:1.4rem; color:var(--danger);">{len(soal_ids) - terjawab_count}</b></div>
            </div>

            <table>
                <thead><tr><th>Nomor Soal</th><th>Status</th><th>Jawaban Anda</th><th>Aksi</th></tr></thead>
                <tbody>{ringkasan_rows}</tbody>
            </table>

            <form method="POST" style="margin-top:36px; display:flex; gap:16px;">
                <a href="{url_for('kuis_soal', idx=0)}" class="btn" style="background:#64748b; flex:1; padding:16px; font-size:1.05rem;"><i class="fas fa-arrow-left"></i> Periksa Kembali</a>
                <button type="submit" class="btn btn-success" style="flex:1; padding:16px; font-size:1.1rem;" onclick="return confirm('Yakin ingin mengirimkan jawaban ujian ini? Jawaban tidak dapat diubah setelah dikirim.');"><i class="fas fa-paper-plane"></i> Ya, Kirim Sekarang</button>
            </form>
        </div>
    </div>
    """
    return render_page("Konfirmasi Ujian", content)

@app.route('/kuis/selesai')
@login_required
def kuis_selesai():
    content = f"""
    <div class="card" style="text-align:center; max-width:540px; margin:60px auto; padding:50px;">
        <div style="font-size:4.5rem; color:var(--success); margin-bottom:20px;"><i class="fas fa-check-circle"></i></div>
        <h2 style="font-size:2rem; font-weight:800; margin-bottom:12px;">Ujian Berhasil Dikirim!</h2>
        <p style="color:var(--text-muted); margin-bottom:32px; line-height:1.6; font-size:1.05rem;">Jawaban Anda telah dikoreksi secara otomatis berdasarkan kunci jawaban. Anda sekarang dapat memeriksa hasil pengerjaan, skor, dan pembahasan lengkap.</p>
        <a href="{url_for('bank_soal')}" class="btn btn-success" style="width:100%; padding:16px; font-size:1.1rem;">Kembali ke Bank Soal & Periksa Hasil</a>
    </div>
    """
    return render_page("Ujian Selesai", content)

@app.route('/kuis/hasil-sementara/<int:materi_id>', methods=['GET', 'POST'])
@login_required
def kuis_hasil_sementara(materi_id):
    materi = MateriSoal.query.get_or_404(materi_id)
    
    if request.method == 'POST':
        soal_id = request.form.get('soal_id')
        sanggahan_teks = request.form.get('sanggahan', '').strip()
        js_obj = JawabanSiswa.query.filter_by(user_id=session['user_id'], materi_id=materi_id, soal_id=soal_id).first()
        if js_obj:
            js_obj.sanggahan_siswa = sanggahan_teks
            db.session.commit()
            flash('Sanggahan / klarifikasi Anda berhasil dikirim ke guru!', 'success')
        return redirect(url_for('kuis_hasil_sementara', materi_id=materi_id))

    jawaban_siswa = JawabanSiswa.query.filter_by(user_id=session['user_id'], materi_id=materi_id).all()
    riwayat = RiwayatPengerjaan.query.filter_by(user_id=session['user_id'], materi_id=materi_id).first()

    jwb_dict = {js.soal_id: js for js in jawaban_siswa}
    rows_html = ""
    
    total_skor_akumulasi = sum(js.nilai_diperoleh for js in jawaban_siswa if js.nilai_diperoleh is not None)

    for idx, soal in enumerate(materi.soals, 1):
        js = jwb_dict.get(soal.id)
        jwb_user = js.jawaban_teks if js else '(Tidak dijawab)'
        poin = js.nilai_diperoleh if js else 0.0
        feedback_guru = js.feedback_guru if js and js.feedback_guru else 'Belum ada catatan dari guru.'
        sanggahan_val = js.sanggahan_siswa if js and js.sanggahan_siswa else ''
        lampiran_view = f'<br><div style="margin-top:12px;"><i class="fas fa-paperclip"></i> <b>Lampiran Siswa:</b><br><img src="{url_for("static", filename="uploads/" + js.lampiran_file)}" style="max-height:200px; border-radius:10px; margin-top:6px; border:1px solid #cbd5e1;"></div>' if js and js.lampiran_file else ''
        
        is_benar = (poin > 0)
        box_bg = "#ecfdf5" if is_benar else "#fee2e2"
        box_border = "#a7f3d0" if is_benar else "#fecaca"
        status_label_color = "#065f46" if is_benar else "#dc2626"
        status_icon = "fas fa-check-circle" if is_benar else "fas fa-times-circle"
        status_text = "JAWABAN BENAR" if is_benar else "JAWABAN SALAH"

        pembahasan_box = f"""
        <div style="background:#ecfdf5; padding:20px; border-radius:16px; border:2px solid #a7f3d0; margin-bottom:20px;">
            <span style="font-size:0.8rem; color:#065f46; display:block; font-weight:bold; margin-bottom:6px; letter-spacing:0.5px;"><i class="fas fa-lightbulb"></i> PEMBAHASAN & KUNCI JAWABAN:</span>
            <div style="font-weight:700; color:#047857; font-size:1.15rem; white-space:pre-wrap; line-height:1.5;">{soal.pembahasan if soal.pembahasan else soal.kunci_jawaban}</div>
        </div>
        """

        rows_html += f"""
        <div class="card" style="margin-bottom:28px; border-left: 6px solid #4f46e5; padding:32px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:12px;">
                <b style="color:#4f46e5; font-size:1.15rem;">Soal #{idx} ({soal.tipe.upper()}) &bull; Bobot Poin: {soal.poin_soal}</b>
                <span style="background:#e0e7ff; color:#4f46e5; padding:6px 16px; border-radius:12px; font-size:0.9rem; font-weight:bold;">Poin Diperoleh: {poin}</span>
            </div>
            
            <p style="font-weight:600; margin-bottom:20px; font-size:1.15rem; line-height:1.6; color:var(--text-main);">{soal.pertanyaan}</p>
            
            <div style="display:flex; flex-direction:column; gap:16px; margin-bottom:20px;">
                <div style="background:{box_bg}; padding:20px; border-radius:16px; border:2px solid {box_border};">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                        <span style="font-size:0.8rem; color:{status_label_color}; font-weight:bold; letter-spacing:0.5px;"><i class="fas fa-user-graduate"></i> JAWABAN ANDA (SISWA):</span>
                        <span style="font-size:0.85rem; color:{status_label_color}; font-weight:800;"><i class="{status_icon}"></i> {status_text}</span>
                    </div>
                    <b style="color:var(--text-main); font-size:1.15rem;">{jwb_user}</b>
                    {lampiran_view}
                </div>
            </div>

            {pembahasan_box}

            <div style="background:#fdf4ff; padding:18px 22px; border-radius:14px; border:1px solid #f5d0fe; margin-bottom:20px;">
                <span style="font-size:0.8rem; color:#86198f; font-weight:bold; display:block; margin-bottom:4px;"><i class="fas fa-comment-dots"></i> Feedback / Catatan dari Guru:</span>
                <p style="color:#701a75; font-size:1.05rem; font-weight:500;">{feedback_guru}</p>
            </div>

            <div style="background:#fffbeb; padding:20px; border-radius:14px; border:1px solid #fde68a;">
                <span style="font-size:0.85rem; color:#b45309; font-weight:bold; display:block; margin-bottom:8px;"><i class="fas fa-shield-alt"></i> Sanggahan / Klarifikasi Siswa (Jika Anda merasa jawaban benar namun dinilai salah):</span>
                <form method="POST">
                    <input type="hidden" name="soal_id" value="{soal.id}">
                    <textarea name="sanggahan" class="form-control" rows="2" placeholder="Tulis alasan atau sanggahan Anda di sini..." style="background:white; margin-bottom:10px;">{sanggahan_val}</textarea>
                    <button type="submit" class="btn btn-sm btn-warning" style="font-weight:bold;"><i class="fas fa-paper-plane"></i> Kirim Sanggahan ke Guru</button>
                </form>
            </div>
        </div>
        """

    status_teks = riwayat.status_ujian if riwayat else 'Selesai Dikerjakan'

    content = f"""
    <a href="{url_for('bank_soal')}" class="btn" style="background:#64748b; margin-bottom:28px;"><i class="fas fa-arrow-left"></i> Kembali ke Bank Soal</a>
    
    <div class="card" style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color:white; padding:36px; margin-bottom:32px; box-shadow: 0 15px 35px rgba(79,70,229,0.15);">
        <h2 style="margin-bottom:8px; font-size:1.8rem;"><i class="fas fa-poll"></i> Hasil Pengerjaan: {materi.judul}</h2>
        <p style="color:#c7d2fe; font-size:1.05rem;">Status Pengerjaan: <b style="color:#fde047;">{status_teks}</b> | Total Skor Keseluruhan: <b style="color:#34d399;">{total_skor_akumulasi}</b></p>
    </div>

    {rows_html}
    """
    return render_page("Hasil Pengerjaan", content)

# ==========================================
# 10. KOREKSI UJIAN (GURU)
# ==========================================
@app.route('/koreksi_ujian')
@admin_required
def koreksi_ujian():
    materis = MateriSoal.query.all()
    html_materis = ""
    for m in materis:
        total_siswa_ikut = RiwayatPengerjaan.query.filter_by(materi_id=m.id).count()
        sudah_dinilai = RiwayatPengerjaan.query.filter_by(materi_id=m.id, status_ujian='Selesai Dinilai').count()
        
        html_materis += f"""
        <div class="card" style="display:flex; justify-content:space-between; align-items:center; border-left: 6px solid #4f46e5;">
            <div>
                <h3 style="margin-bottom:8px; font-size:1.35rem;"><i class="fas fa-file-alt" style="color:#4f46e5; margin-right:10px;"></i> {m.judul}</h3>
                <div style="display:flex; gap:20px; color:var(--text-muted); font-size:0.95rem;">
                    <span><i class="fas fa-users"></i> Siswa Mengumpulkan: <b>{total_siswa_ikut}</b></span>
                    <span><i class="fas fa-check-circle" style="color:var(--success);"></i> Selesai Dinilai: <b style="color:var(--success);">{sudah_dinilai}</b></span>
                </div>
            </div>
            <a href="{url_for('koreksi_detail', materi_id=m.id)}" class="btn btn-success" style="padding:14px 28px; font-size:1.05rem;"><i class="fas fa-edit"></i> Buka Daftar Siswa &rarr;</a>
        </div>
        """
        
    if not html_materis:
        html_materis = '<div class="card" style="text-align:center; color:var(--text-muted); padding:50px;"><p>Belum ada ujian atau materi yang tersedia untuk dikoreksi.</p></div>'

    content = f"""
    <div style="margin-bottom:36px;">
        <h1 style="font-size:2.2rem; font-weight:800; margin-bottom:8px;"><i class="fas fa-check-double" style="color:#4f46e5;"></i> Panel Koreksi Ujian Siswa</h1>
        <p style="color:var(--text-muted); font-size:1.1rem;">Pilih salah satu ujian di bawah ini untuk melihat daftar siswa yang mengumpulkan.</p>
    </div>
    {html_materis}
    """
    return render_page("Koreksi Ujian", content)

@app.route('/koreksi_ujian/<int:materi_id>')
@admin_required
def koreksi_detail(materi_id):
    materi = MateriSoal.query.get_or_404(materi_id)
    siswas = User.query.filter_by(role='siswa').all()
    
    siswa_list_html = ""
    for sw in siswas:
        jsw_count = JawabanSiswa.query.filter_by(user_id=sw.id, materi_id=materi.id).count()
        if jsw_count == 0: continue
            
        riwayat_siswa = RiwayatPengerjaan.query.filter_by(user_id=sw.id, materi_id=materi.id).first()
        status_teks = riwayat_siswa.status_ujian if riwayat_siswa else 'Selesai Dikerjakan'
        skor_total = riwayat_siswa.skor_tertinggi if riwayat_siswa else 0.0
        badge_bg = '#d1fae5' if status_teks == 'Selesai Dinilai' else '#fef3c7'
        badge_fg = '#059669' if status_teks == 'Selesai Dinilai' else '#d97706'

        siswa_list_html += f"""
        <div class="card" style="display:flex; justify-content:space-between; align-items:center; border-left: 6px solid #4f46e5;">
            <div style="display:flex; align-items:center; gap:20px;">
                <div style="width:60px; height:60px; background:rgba(79,70,229,0.1); border-radius:50%; display:flex; align-items:center; justify-content:center; color:#4f46e5; font-size:1.5rem; font-weight:bold;">
                    {sw.nama[0].upper()}
                </div>
                <div>
                    <h3 style="margin-bottom:6px; font-size:1.3rem;">{sw.nama}</h3>
                    <p style="color:var(--text-muted); font-size:0.9rem;">Username: @{sw.username} | Total Skor: <b style="color:var(--success);">{skor_total}</b></p>
                </div>
            </div>
            <div style="display:flex; align-items:center; gap:20px;">
                <span style="background:{badge_bg}; color:{badge_fg}; padding:8px 16px; border-radius:20px; font-size:0.9rem; font-weight:700;">{status_teks}</span>
                <a href="{url_for('koreksi_siswa_detail', materi_id=materi.id, user_id=sw.id)}" class="btn btn-success" style="padding:12px 24px;"><i class="fas fa-edit"></i> Koreksi Lembar Jawaban &rarr;</a>
            </div>
        </div>
        """

    if not siswa_list_html:
        siswa_list_html = '<div class="card" style="text-align:center; color:var(--text-muted); padding:60px;"><i class="fas fa-folder-open fa-3x" style="margin-bottom:16px; opacity:0.5;"></i><p style="font-size:1.1rem;">Belum ada siswa yang mengumpulkan jawaban untuk ujian ini.</p></div>'

    content = f"""
    <a href="{url_for('koreksi_ujian')}" class="btn" style="background:#64748b; margin-bottom:28px;"><i class="fas fa-arrow-left"></i> Kembali ke Daftar Ujian</a>
    <div style="background: linear-gradient(135deg, #1e1b4b 0%, #312e81 100%); color: white; margin-bottom: 32px; padding: 36px; border-radius:24px; box-shadow: 0 15px 35px rgba(79,70,229,0.15);">
        <h2 style="margin-bottom:8px; font-size:2rem;"><i class="fas fa-clipboard-check"></i> {materi.judul}</h2>
        <p style="color:#c7d2fe; font-size:1.1rem;">Pilih siswa di bawah ini untuk mengoreksi lembar jawaban secara terpisah per individu.</p>
    </div>
    {siswa_list_html}
    """
    return render_page(f"Daftar Siswa - {materi.judul}", content)

@app.route('/koreksi_ujian/<int:materi_id>/siswa/<int:user_id>', methods=['GET', 'POST'])
@admin_required
def koreksi_siswa_detail(materi_id, user_id):
    materi = MateriSoal.query.get_or_404(materi_id)
    siswa = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        total = 0.0
        for s in materi.soals:
            val = float(request.form.get(f'nilai_{s.id}') or 0)
            feedback_val = request.form.get(f'feedback_{s.id}', '').strip()
            total += val
            js = JawabanSiswa.query.filter_by(user_id=siswa.id, materi_id=materi.id, soal_id=s.id).first()
            if js:
                js.nilai_diperoleh = val
                js.feedback_guru = feedback_val
                js.status_koreksi = 'Dinilai Guru'
        
        r = RiwayatPengerjaan.query.filter_by(user_id=siswa.id, materi_id=materi.id).first()
        if r:
            r.skor_tertinggi = total
            r.status_ujian = 'Selesai Dinilai'
        db.session.commit()
        flash(f'Nilai dan feedback untuk {siswa.nama} berhasil disimpan dan divalidasi!', 'success')
        return redirect(url_for('koreksi_detail', materi_id=materi.id))

    jsw = JawabanSiswa.query.filter_by(user_id=siswa.id, materi_id=materi.id).all()
    jwb_dict = {j.soal_id: j for j in jsw}
    
    soal_rows_html = ""
    total_initial_score = 0.0
    
    for idx, soal_obj in enumerate(materi.soals, 1):
        j = jwb_dict.get(soal_obj.id)
        poin_val = j.nilai_diperoleh if j and j.nilai_diperoleh is not None else 0.0
        total_initial_score += poin_val
        jwb_teks = j.jawaban_teks if j else '(Tidak dijawab)'
        feedback_val = j.feedback_guru if j and j.feedback_guru else ''
        sanggahan_val = j.sanggahan_siswa if j and j.sanggahan_siswa else ''
        lampiran_view = f'<br><div style="margin-top:12px;"><i class="fas fa-paperclip"></i> <b>Lampiran Foto/File Siswa:</b><br><img src="{url_for("static", filename="uploads/" + j.lampiran_file)}" style="max-height:220px; border-radius:12px; margin-top:8px; border:1px solid #cbd5e1;"></div>' if j and j.lampiran_file else ''
        foto_soal = f'<br><img src="{url_for("static", filename="uploads/" + soal_obj.foto)}" style="max-height:220px; border-radius:12px; margin-top:12px; border:1px solid #cbd5e1;">' if soal_obj.foto else ''
        
        sanggahan_box = f"""
        <div style="background:#fffbeb; padding:16px; border-radius:12px; border:1px solid #fde68a; margin-bottom:18px;">
            <span style="font-size:0.75rem; text-transform:uppercase; color:#b45309; font-weight:bold; display:block; margin-bottom:4px;"><i class="fas fa-comment-alt"></i> Sanggahan dari Siswa:</span>
            <p style="color:#92400e; font-size:1.05rem; font-weight:600;">{sanggahan_val}</p>
        </div>
        """ if sanggahan_val else ""

        keyword_view_html = f'<div style="margin-top:8px; font-size:0.9rem; color:#b45309;"><i class="fas fa-key"></i> <b>Keyword/Angka Kunci:</b> {soal_obj.keyword_jawaban}</div>' if soal_obj.keyword_jawaban else ''

        soal_rows_html += f"""
        <div class="card" style="background:#f8fafc; padding:32px; border-radius:20px; border:1px solid var(--border-color); margin-bottom:28px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                <span style="font-weight:700; color:#4f46e5; font-size:1.15rem;"><i class="fas fa-question-circle"></i> Soal #{idx} ({soal_obj.tipe.upper()}) &bull; Maks Poin: {soal_obj.poin_soal}</span>
            </div>
            
            <p style="margin-bottom:20px; font-weight:600; color:var(--text-main); font-size:1.15rem; line-height:1.6;">{soal_obj.pertanyaan}{foto_soal}</p>
            
            <div style="display:flex; flex-direction:column; gap:16px; margin-bottom:20px;">
                <div style="background:white; padding:20px; border-radius:16px; border:1px dashed #cbd5e1;">
                    <span style="font-size:0.8rem; text-transform:uppercase; color:var(--text-muted); font-weight:bold; display:block; margin-bottom:6px; letter-spacing:0.5px;"><i class="fas fa-user-graduate"></i> Jawaban Siswa:</span>
                    <span style="font-weight:700; color:var(--text-main); font-size:1.2rem;">{jwb_teks}</span>
                    {lampiran_view}
                </div>

                <div style="background:#ecfdf5; padding:20px; border-radius:16px; border:1px solid #a7f3d0;">
                    <span style="font-size:0.8rem; text-transform:uppercase; color:#065f46; font-weight:bold; display:block; margin-bottom:4px; letter-spacing:0.5px;"><i class="fas fa-key"></i> Kunci Jawaban Guru & Keyword Otomatis:</span>
                    <div style="font-weight:700; color:#047857; font-size:1.1rem; white-space:pre-wrap; line-height:1.5;">{soal_obj.kunci_jawaban}</div>
                    {keyword_view_html}
                </div>
            </div>

            {sanggahan_box}

            <div style="margin-bottom:20px;">
                <label style="font-size:0.9rem; font-weight:700; color:var(--text-main); display:block; margin-bottom:6px;"><i class="fas fa-comment-dots"></i> Feedback / Catatan untuk Siswa pada Soal Ini:</label>
                <textarea name="feedback_{soal_obj.id}" class="form-control" rows="2" placeholder="Tulis catatan atau arahan perbaikan untuk siswa...">{feedback_val}</textarea>
            </div>

            <div style="display:flex; align-items:center; gap:16px;">
                <label style="font-size:1rem; font-weight:700; color:var(--text-main);">Poin / Nilai Soal (Maks: {soal_obj.poin_soal}):</label>
                <input type="number" step="0.5" max="{soal_obj.poin_soal}" min="0" name="nilai_{soal_obj.id}" value="{poin_val}" class="form-control score-input" oninput="hitungTotalNilai()" style="margin-bottom:0; max-width:180px; font-weight:bold; font-size:1.15rem;" required>
            </div>
        </div>
        """

    content = f"""
    <a href="{url_for('koreksi_detail', materi_id=materi.id)}" class="btn" style="background:#64748b; margin-bottom:28px;"><i class="fas fa-arrow-left"></i> Kembali ke Daftar Siswa</a>
    
    <div class="card" style="border: 1px solid var(--border-color); margin-bottom:32px; box-shadow: 0 15px 35px rgba(0,0,0,0.05); padding:36px;">
        <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #f1f5f9; padding-bottom:20px; margin-bottom:28px;">
            <div style="display:flex; align-items:center; gap:20px;">
                <div style="width:65px; height:65px; background:rgba(79,70,229,0.1); border-radius:50%; display:flex; align-items:center; justify-content:center; color:#4f46e5; font-size:1.6rem; font-weight:bold;">
                    {siswa.nama[0].upper()}
                </div>
                <div>
                    <h2 style="color:var(--text-main); margin-bottom:4px; font-size:1.5rem;">{siswa.nama}</h2>
                    <span style="font-size:0.95rem; color:var(--text-muted);">Ujian: <b>{materi.judul}</b> | Username: @{siswa.username}</span>
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.05rem; font-weight:bold; color:var(--text-muted);">Total Nilai: <span id="total-display" style="color:var(--success); font-size:1.8rem; font-weight:800;">{total_initial_score}</span></div>
            </div>
        </div>
        
        <form method="POST">
            {soal_rows_html}
            <button type="submit" class="btn btn-success" style="width:100%; padding:18px; font-size:1.15rem; margin-top:16px;"><i class="fas fa-save"></i> Validasi & Simpan Nilai & Feedback Siswa Ini</button>
        </form>
    </div>

    <script>
        function hitungTotalNilai() {{
            const inputs = document.querySelectorAll('.score-input');
            let total = 0;
            inputs.forEach(input => {{
                let val = parseFloat(input.value);
                if (!isNaN(val)) {{
                    total += val;
                }}
            }});
            document.getElementById('total-display').innerText = total;
        }}
    </script>
    """
    return render_page(f"Koreksi - {siswa.nama}", content)

# ==========================================
# 11. GAME & FITUR LAINNYA
# ==========================================
@app.route('/gamemath')
@login_required
def gamemath():
    content = f"""
    <div style="margin-bottom:36px;">
        <h1 style="font-size:2.2rem; font-weight:800; margin-bottom:8px;"><i class="fas fa-gamepad" style="color:var(--success);"></i> GameMath Edukatif</h1>
        <p style="color:var(--text-muted); font-size:1.1rem;">Pilih permainan matematika seru untuk mengasah kemampuan berhitungmu.</p>
    </div>
    
    <div class="grid-3">
        <div class="card" style="border-top: 6px solid #4f46e5; text-align:center; padding:40px 32px;">
            <div style="font-size: 4.5rem; margin-bottom: 20px;">🐍</div>
            <h3 style="margin-bottom:12px; font-size:1.4rem;">Ular Tangga Math</h3>
            <p style="color:var(--text-muted); font-size:0.95rem; margin-bottom:28px; line-height:1.5;">Permainan kelompok interaktif dengan tantangan kartu soal matematika otomatis.</p>
            <a href="{url_for('setup_ular_tangga')}" class="btn" style="width:100%; padding:14px; font-size:1.05rem; background:#4f46e5;">Mulai Main &rarr;</a>
        </div>
    </div>
    """
    return render_page("GameMath", content)

@app.route('/gamemath/ular_tangga/setup', methods=['GET', 'POST'])
@login_required
def setup_ular_tangga():
    if request.method == 'POST':
        teams_raw = request.form.getlist('team_names')
        teams = [t.strip() for t in teams_raw if t.strip()]
        if not teams: teams = ["Kelompok 1", "Kelompok 2"]
        session['ut_teams'] = teams
        return redirect(url_for('game_ular_tangga'))
        
    content = f"""
    <div class="card" style="max-width:580px; margin:40px auto; padding:48px;">
        <a href="{url_for('gamemath')}" class="btn btn-sm" style="background:#64748b; margin-bottom:24px;"><i class="fas fa-arrow-left"></i> Kembali</a>
        <h2 style="margin-bottom:8px; font-size:1.8rem; font-weight:800;"><i class="fas fa-users-cog"></i> Setup Tim Ular Tangga</h2>
        <p style="color:var(--text-muted); font-size:1rem; margin-bottom:28px;">Masukkan nama kelompok atau tim yang akan bertanding dalam permainan:</p>
        <form method="POST">
            <div id="teamContainer" style="display:flex; flex-direction:column; gap:14px; margin-bottom:24px;">
                <input type="text" name="team_names" class="form-control" value="Kelompok A" required style="margin-bottom:0;">
                <input type="text" name="team_names" class="form-control" value="Kelompok B" required style="margin-bottom:0;">
            </div>
            <button type="button" onclick="tambahTim()" class="btn" style="background:#8b5cf6; width:100%; margin-bottom:20px; padding:14px;"><i class="fas fa-plus"></i> Tambah Tim Lain</button>
            <button type="submit" class="btn btn-success" style="width:100%; padding:16px; font-size:1.1rem;">Mulai Pertandingan Ular Tangga &rarr;</button>
        </form>
    </div>
    <script>
        function tambahTim() {{
            let container = document.getElementById('teamContainer');
            let count = container.children.length + 1;
            let input = document.createElement('input');
            input.type = 'text'; input.name = 'team_names'; input.className = 'form-control';
            input.value = `Kelompok ${{String.fromCharCode(64 + count)}}`;
            input.required = true; input.style.marginBottom = '0';
            container.appendChild(input);
        }}
    </script>
    """
    return render_page("Setup Ular Tangga", content)

@app.route('/gamemath/ular_tangga')
@login_required
def game_ular_tangga():
    teams = session.get('ut_teams', ["Kelompok A", "Kelompok B"])
    kartus = KartuSoalUlarTangga.query.all()
    kartu_dict = {'hijau': [], 'biru': [], 'kuning': [], 'merah': []}
    for k in kartus:
        kartu_dict[k.warna].append({
            'tipe_soal': k.tipe_soal or 'angka',
            'pertanyaan': k.pertanyaan, 
            'jawaban': k.jawaban,
            'keyword_jawaban': k.keyword_jawaban or ''
        })
    for w in kartu_dict:
        if not kartu_dict[w]: 
            kartu_dict[w].append({'tipe_soal': 'angka', 'pertanyaan': '1 + 1', 'jawaban': '2', 'keyword_jawaban': ''})

    teams_json = json.dumps(teams)
    kartu_json = json.dumps(kartu_dict)

    content = '''
    <style>
        .board { display: grid; grid-template-columns: repeat(10, 1fr); gap: 6px; max-width: 720px; margin: 0 auto; background: white; padding: 18px; border-radius: 24px; box-shadow: 0 15px 35px rgba(0,0,0,0.06); }
        .cell { aspect-ratio: 1; border-radius: 12px; position: relative; display: flex; flex-direction: column; align-items: center; justify-content: center; font-weight: 700; font-size: 0.85rem; }
        .cell .num { position: absolute; top: 6px; left: 8px; font-size: 0.75rem; color: rgba(0,0,0,0.6); }
        .cell .map-info { font-size: 0.65rem; text-align: center; color: #1e293b; background: rgba(255,255,255,0.95); padding: 3px 6px; border-radius: 6px; margin-top: 14px; font-weight: 800; }
        .tokens-container { display: flex; gap: 4px; position: absolute; bottom: 6px; flex-wrap: wrap; justify-content: center; max-width: 90%; }
        .team-token { width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 6px rgba(0,0,0,0.3); }
        .dice-box { text-align: center; margin: 28px auto; max-width: 520px; padding: 32px; background: white; border-radius: 24px; box-shadow: 0 15px 35px rgba(0,0,0,0.05); }
        dialog { border: none; border-radius: 28px; padding: 0; box-shadow: 0 25px 60px rgba(0,0,0,0.4); max-width: 480px; width: 90%; margin: auto; animation: popIn 0.35s cubic-bezier(0.16, 1, 0.3, 1); }
        dialog::backdrop { background: rgba(15, 23, 42, 0.75); backdrop-filter: blur(8px); }
        @keyframes popIn { from { transform: scale(0.85); opacity: 0; } to { transform: scale(1); opacity: 1; } }
        .color-badge { display:inline-block; padding: 8px 18px; border-radius: 20px; font-size:0.9rem; font-weight:bold; margin-bottom:14px; }
        .modal-body { padding: 40px; text-align: center; }
        .team-scoreboard { display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; margin-bottom: 28px; }
        .team-card { background: white; padding: 14px 22px; border-radius: 16px; box-shadow: 0 6px 20px rgba(0,0,0,0.05); font-weight: bold; border-left: 6px solid #ccc; transition: all 0.3s ease; }
    </style>

    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:24px;">
        <div>
            <a href="/gamemath/ular_tangga/setup" class="btn btn-sm" style="background:#64748b; margin-bottom:10px;"><i class="fas fa-cog"></i> Ubah Tim / Setup Ulang</a>
            <h1 style="font-size:2rem; font-weight:800;">🐍 Ular Tangga Berkelompok</h1>
        </div>
    </div>

    <div id="scoreboard" class="team-scoreboard"></div>

    <div style="display:flex; gap:12px; margin-bottom:28px; justify-content:center; flex-wrap:wrap;">
        <span class="color-badge" style="background:#d1fae5; color:#059669;">Kartu Hijau</span>
        <span class="color-badge" style="background:#e0f2fe; color:#2563eb;">Kartu Biru</span>
        <span class="color-badge" style="background:#fef3c7; color:#d97706;">Kartu Kuning</span>
        <span class="color-badge" style="background:#fee2e2; color:#dc2626;">Kartu Merah</span>
    </div>

    <div id="board" class="board"></div>

    <div class="dice-box">
        <h3 id="giliranInfo" style="color:#4f46e5; margin-bottom:10px; font-size:1.3rem;">Giliran: Tim</h3>
        <div id="diceDisplay" style="font-size: 4.5rem; color: #4f46e5; margin-bottom: 16px;">🎲</div>
        <button id="btnRoll" onclick="kocokDaduTim()" class="btn btn-success" style="font-size:1.15rem; padding:14px 36px; border-radius:30px;"><i class="fas fa-dice"></i> Kocok Dadu Sekarang</button>
        <p id="gameMessage" style="margin-top:16px; font-weight:700; color:var(--text-muted); height:24px;"></p>
    </div>

    <dialog id="soalModal">
        <div class="modal-body">
            <h2 style="margin-bottom:8px; color:var(--text-main); font-size:1.6rem;">Tantangan Kartu Soal!</h2>
            <span id="soalBadge" class="color-badge"></span>
            <div id="mathQuestion" style="font-size:1.4rem; font-weight:700; margin: 18px 0; color:#1e293b; line-height:1.5;">?</div>
            <div id="inputWrapper">
                <input type="text" id="jawabanInput" class="form-control" style="font-size:1.2rem; text-align:center; padding:16px; margin-bottom:24px;" placeholder="Ketik jawaban Anda...">
            </div>
            <button onclick="cekJawabanTim()" class="btn btn-success" style="width:100%; font-size:1.15rem; padding:16px; border-radius:14px;">Kirim Jawaban</button>
        </div>
    </dialog>

    <dialog id="infoModal">
        <div class="modal-body">
            <div id="infoIcon" style="font-size: 4.5rem; margin-bottom: 18px;">🎉</div>
            <h2 id="infoTitle" style="margin-bottom: 10px; color:var(--text-main); font-size:1.6rem;">Informasi Game</h2>
            <p id="infoText" style="color:var(--text-muted); margin-bottom: 32px; font-size: 1.15rem; line-height: 1.6;"></p>
            <button onclick="tutupInfoModal()" class="btn btn-success" style="width:100%; padding:16px; border-radius:16px; font-size:1.1rem;">OK, Lanjutkan Permainan</button>
        </div>
    </dialog>

    <script>
        const teams = __TEAMS_JSON__;
        const kartuSoalDB = __KARTU_JSON__;
        
        const ladders = { 4:14, 9:31, 21:42, 28:84, 51:67, 71:91, 80:100 };
        const snakes = { 17:7, 54:34, 62:19, 64:60, 87:24, 93:73, 95:75, 99:78 };
        
        let teamData = {};
        let activeTeamIdx = 0;
        let oldPos = 1, currentActiveCard = null;
        let callbackSetelahInfo = null;

        const teamColors = ['#dc2626', '#2563eb', '#059669', '#d97706', '#8b5cf6', '#ec4899', '#14b8a6'];

        teams.forEach(function(t, idx) {
            teamData[t] = { pos: 1, color: teamColors[idx % teamColors.length], score: 0 };
        });

        function renderScoreboard() {
            let html = '';
            teams.forEach(function(t, idx) {
                let activeMark = (idx === activeTeamIdx) ? 'border-width:6px; transform:scale(1.08); box-shadow:0 10px 25px rgba(0,0,0,0.18);' : '';
                html += '<div class="team-card" style="border-color:' + teamData[t].color + '; ' + activeMark + '">' +
                        t + '<br><span style="font-size:0.9rem; color:var(--text-muted);">Petak: ' + teamData[t].pos + ' | Skor: ' + teamData[t].score + '</span>' +
                       '</div>';
            });
            document.getElementById('scoreboard').innerHTML = html;
            document.getElementById('giliranInfo').innerText = 'Giliran Tim: ' + teams[activeTeamIdx];
        }

        function tampilkanPesanCustom(judul, pesan, icon, callback) {
            document.getElementById('infoTitle').innerText = judul;
            document.getElementById('infoText').innerHTML = pesan;
            document.getElementById('infoIcon').innerText = icon || "🎉";
            callbackSetelahInfo = callback;
            document.getElementById('infoModal').showModal();
        }

        function tutupInfoModal() {
            document.getElementById('infoModal').close();
            if (callbackSetelahInfo) {
                let cb = callbackSetelahInfo;
                callbackSetelahInfo = null;
                cb();
            }
        }

        function renderBoard() {
            let html = '';
            for (let row = 9; row >= 0; row--) {
                let start = row * 10 + 1;
                let rowCells = [];
                for (let i = 0; i < 10; i++) rowCells.push(start + i);
                if (row % 2 !== 0) rowCells.reverse();
                
                for (let num of rowCells) {
                    let c = num % 4;
                    let bg = ['#fee2e2', '#e0f2fe', '#d1fae5', '#fef3c7'][c];
                    let border = ['#dc2626', '#2563eb', '#059669', '#d97706'][c];
                    
                    let extraLabel = '';
                    if (ladders[num]) extraLabel = '<div class="map-info" style="color:#059669;">🪜 Naik ➔ ' + ladders[num] + '</div>';
                    if (snakes[num]) extraLabel = '<div class="map-info" style="color:#dc2626;">🐍 Turun ➔ ' + snakes[num] + '</div>';
                    if (num === 100) extraLabel = '<div class="map-info" style="color:#d97706;">🏆 FINIS</div>';
                    if (num === 1) extraLabel = '<div class="map-info">🏁 START</div>';

                    html += '<div id="cell-' + num + '" class="cell" style="background:' + bg + '; border:2px solid ' + border + '">' +
                            '<span class="num">' + num + '</span>' +
                            extraLabel +
                            '<div id="tokens-' + num + '" class="tokens-container"></div>' +
                           '</div>';
                }
            }
            document.getElementById('board').innerHTML = html;
            updateAllTokens();
            renderScoreboard();
        }

        function updateAllTokens() {
            for(let i=1; i<=100; i++) {
                let container = document.getElementById('tokens-' + i);
                if(container) container.innerHTML = '';
            }
            teams.forEach(function(t) {
                let p = teamData[t].pos;
                let container = document.getElementById('tokens-' + p);
                if(container) {
                    container.innerHTML += '<div class="team-token" style="background:' + teamData[t].color + '" title="' + t + '"></div>';
                }
            });
        }

        function kocokDaduTim() {
            document.getElementById('btnRoll').disabled = true;
            document.getElementById('gameMessage').innerText = "Mengocok dadu...";
            let dice = Math.floor(Math.random() * 6) + 1;
            let count = 0;
            let interval = setInterval(function() {
                let diceFaces = ['⚀','⚁','⚂','⚃','⚄','⚅'];
                document.getElementById('diceDisplay').innerText = diceFaces[Math.floor(Math.random()*6)];
                count++;
                if (count > 12) {
                    clearInterval(interval);
                    document.getElementById('diceDisplay').innerText = diceFaces[dice - 1];
                    prosesJalanTim(dice);
                }
            }, 50);
        }

        function prosesJalanTim(dice) {
            let tName = teams[activeTeamIdx];
            oldPos = teamData[tName].pos;
            teamData[tName].pos += dice;
            if (teamData[tName].pos > 100) teamData[tName].pos = 100 - (teamData[tName].pos - 100);
            
            updateAllTokens();
            document.getElementById('gameMessage').innerText = tName + ' maju ' + dice + ' langkah ke petak ' + teamData[tName].pos + '...';
            setTimeout(function() { ambilKartuSoal(teamData[tName].pos); }, 900);
        }

        function ambilKartuSoal(pos) {
            if (pos === 100) {
                let tName = teams[activeTeamIdx];
                tampilkanPesanCustom("Tim Pemenang!", '🎉 Luar biasa! <b>' + tName + '</b> berhasil mencapai garis finis dan keluar sebagai juara!', "🏆", function() {
                    location.reload();
                });
                return;
            }

            let c = pos % 4;
            let warnaKey = ['merah', 'biru', 'hijau', 'kuning'][c];
            let daftarSoal = kartuSoalDB[warnaKey];
            currentActiveCard = daftarSoal[Math.floor(Math.random() * daftarSoal.length)];

            const badge = document.getElementById('soalBadge');
            let tipeLabelText = (currentActiveCard.tipe_soal === 'uraian') ? 'Soal Uraian' : 'Jawaban Cepat (Angka)';
            badge.innerText = 'Kartu Soal (' + warnaKey.toUpperCase() + ') - ' + tipeLabelText;
            
            let bgMap = {'hijau':'#d1fae5','biru':'#e0f2fe','kuning':'#fef3c7','merah':'#fee2e2'};
            let colorMap = {'hijau':'#059669','biru':'#2563eb','kuning':'#d97706','merah':'#dc2626'};
            
            badge.style.background = bgMap[warnaKey];
            badge.style.color = colorMap[warnaKey];

            document.getElementById('mathQuestion').innerText = currentActiveCard.pertanyaan;
            
            let inputWrapper = document.getElementById('inputWrapper');
            if (currentActiveCard.tipe_soal === 'uraian') {
                inputWrapper.innerHTML = '<textarea id="jawabanInput" class="form-control" rows="3" style="font-size:1.1rem; padding:14px; margin-bottom:24px;" placeholder="Ketik jawaban uraian Anda..."></textarea>';
            } else {
                inputWrapper.innerHTML = '<input type="text" id="jawabanInput" class="form-control" style="font-size:1.4rem; text-align:center; padding:16px; margin-bottom:24px;" placeholder="Ketik angka jawaban...">';
            }

            document.getElementById('soalModal').showModal();
            setTimeout(function() { document.getElementById('jawabanInput').focus(); }, 100);
        }

        function cekJawabanTim() {
            let userAns = document.getElementById('jawabanInput').value.trim().toLowerCase();
            if (userAns === '') return;
            document.getElementById('soalModal').close();
            
            let tName = teams[activeTeamIdx];
            let pos = teamData[tName].pos;

            let kunciClean = currentActiveCard.jawaban.trim().toLowerCase();
            let isBenar = false;

            if (currentActiveCard.tipe_soal === 'angka') {
                if (userAns === kunciClean) {
                    isBenar = true;
                }
            } else {
                let keywords = [kunciClean];
                if (currentActiveCard.keyword_jawaban) {
                    let parts = currentActiveCard.keyword_jawaban.split(',');
                    parts.forEach(function(p) {
                        let kw = p.trim().toLowerCase();
                        if (kw) keywords.push(kw);
                    });
                }

                for (let i = 0; i < keywords.length; i++) {
                    if (userAns.includes(keywords[i])) {
                        isBenar = true;
                        break;
                    }
                }
            }

            if (isBenar) {
                teamData[tName].score += 10;
                let msg = '<span style="color:var(--success);">Jawaban Benar! (+10 Poin)</span><br>Token tetap di petak ' + pos + '.';
                
                if (ladders[pos]) {
                    teamData[tName].pos = ladders[pos];
                    msg += '<br><b style="color:#059669;">Hore! Naik Tangga 🪜 (' + pos + ' ➔ ' + ladders[pos] + ')</b>';
                    updateAllTokens();
                } else if (snakes[pos]) {
                    teamData[tName].pos = snakes[pos];
                    msg += '<br><b style="color:var(--danger);">Waduh! Digigit Ular 🐍 (' + pos + ' ➔ ' + snakes[pos] + ')</b>';
                    updateAllTokens();
                }

                tampilkanPesanCustom("Benar!", msg, "🎉", function() { gantiGiliran(); });
            } else {
                tampilkanPesanCustom("Kurang Tepat", 'Jawaban belum tepat.<br>Kunci/Keyword yang diharapkan: <b>' + currentActiveCard.jawaban + '</b><br>Token harus mundur kembali ke petak asal (' + oldPos + ').', "❌", function() {
                    teamData[tName].pos = oldPos;
                    updateAllTokens();
                    gantiGiliran();
                });
            }
        }

        function gantiGiliran() {
            activeTeamIdx = (activeTeamIdx + 1) % teams.length;
            renderScoreboard();
            document.getElementById('btnRoll').disabled = false;
            document.getElementById('gameMessage').innerText = "";
        }

        document.addEventListener("keypress", function(e) {
          if (e.key === "Enter" && document.getElementById('soalModal').open) {
              let activeElem = document.activeElement;
              if (activeElem && activeElem.id === 'jawabanInput' && activeElem.tagName !== 'TEXTAREA') {
                  e.preventDefault();
                  cekJawabanTim();
              }
          }
        });

        renderBoard();
    </script>
    '''
    content = content.replace('__TEAMS_JSON__', teams_json).replace('__KARTU_JSON__', kartu_json)
    return render_page("Ular Tangga Berkelompok", content)

# ==========================================
# 12. MATH VOCAB
# ==========================================
@app.route('/mathvocab', methods=['GET', 'POST'])
@login_required
def mathvocab():
    if request.method == 'POST' and session.get('role') == 'admin':
        if request.form.get('action') == 'add':
            db.session.add(VocabCategory(name=request.form.get('name')))
            flash('Kategori kamus berhasil ditambahkan!', 'success')
        db.session.commit()
        return redirect(url_for('mathvocab'))

    cats = VocabCategory.query.all()
    cats_html = "".join([f"""
    <div class="card" style="border-top: 6px solid #8b5cf6; display:flex; flex-direction:column; justify-content:space-between; padding:36px 28px;">
        <div>
            <h3 style="margin-bottom:10px; font-size:1.4rem;"><i class="fas fa-book" style="color:#8b5cf6;"></i> {c.name}</h3>
            <p style="color:var(--text-muted); font-size:0.95rem; margin-bottom:24px;">{len(c.vocabs)} Istilah / Kosakata Matematika</p>
        </div>
        <a href="{url_for('mathvocab_detail', cat_id=c.id)}" class="btn" style="background:#8b5cf6; width:100%; padding:14px;">Buka Kamus &rarr;</a>
    </div>
    """ for c in cats])
    
    add_btn = f"""
    <button onclick="document.getElementById('formAddCat').showModal()" class="btn btn-success"><i class="fas fa-plus"></i> Tambah Kategori</button>
    <dialog id="formAddCat" style="border:none; border-radius:24px; padding:36px; max-width:480px; width:90%; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
        <h3 style="margin-bottom:20px; color:var(--success); font-size:1.4rem;"><i class="fas fa-folder-plus"></i> Tambah Kategori Kamus</h3>
        <form method="POST">
            <input type="hidden" name="action" value="add">
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Nama Kategori:</label>
            <input type="text" name="name" class="form-control" placeholder="Contoh: Aljabar & Geometri" required>
            <div style="display:flex; gap:12px; margin-top:12px;">
                <button type="submit" class="btn btn-success" style="flex:1;">Simpan</button>
                <button type="button" class="btn btn-danger" onclick="document.getElementById('formAddCat').close()" style="flex:1;">Batal</button>
            </div>
        </form>
    </dialog>
    """ if session.get('role') == 'admin' else ""

    content = f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:32px;">
        <div>
            <h1 style="font-size:2rem; font-weight:800; margin-bottom:6px;">MathVocab (Kamus Matematika)</h1>
            <p style="color:var(--text-muted); font-size:1.05rem;">Daftar istilah matematika dwibahasa (Inggris - Indonesia) beserta definisinya.</p>
        </div>
        {add_btn}
    </div>
    <div class="grid-3">{cats_html}</div>
    """
    return render_page("MathVocab", content)

@app.route('/mathvocab/<int:cat_id>', methods=['GET', 'POST'])
@login_required
def mathvocab_detail(cat_id):
    cat = VocabCategory.query.get_or_404(cat_id)
    if request.method == 'POST' and session.get('role') == 'admin':
        if request.form.get('action') == 'add':
            db.session.add(Vocab(category_id=cat.id, term_en=request.form.get('term_en'), term_id=request.form.get('term_id'), definition=request.form.get('def')))
            db.session.commit()
            flash('Kosakata berhasil ditambahkan!', 'success')
        return redirect(url_for('mathvocab_detail', cat_id=cat.id))

    voc_html = "".join([f"""
    <div class="card" style="border-left: 6px solid #8b5cf6; padding:28px;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
            <h3 style="font-size:1.3rem; color:var(--text-main);">{v.term_en}</h3>
            <span style="background:#f3e8ff; color:#7c3aed; padding:6px 14px; border-radius:20px; font-weight:700; font-size:0.9rem;">{v.term_id}</span>
        </div>
        <p style="color:var(--text-muted); font-size:1.05rem; line-height:1.6;">{v.definition}</p>
    </div>
    """ for v in cat.vocabs])

    add_v = f"""
    <button onclick="document.getElementById('formAddVoc').showModal()" class="btn btn-success"><i class="fas fa-plus"></i> Tambah Kosakata</button>
    <dialog id="formAddVoc" style="border:none; border-radius:24px; padding:36px; max-width:520px; width:90%; box-shadow:0 25px 50px rgba(0,0,0,0.3);">
        <h3 style="margin-bottom:20px; color:var(--success); font-size:1.4rem;"><i class="fas fa-spell-check"></i> Tambah Kosakata Baru</h3>
        <form method="POST">
            <input type="hidden" name="action" value="add">
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Istilah (Bahasa Inggris):</label>
            <input type="text" name="term_en" class="form-control" placeholder="Contoh: Addition" required>
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Terjemahan (Bahasa Indonesia):</label>
            <input type="text" name="term_id" class="form-control" placeholder="Contoh: Penjumlahan" required>
            <label style="font-size:0.85rem; font-weight:bold; display:block; margin-bottom:6px;">Definisi / Penjelasan:</label>
            <textarea name="def" class="form-control" rows="3" placeholder="Penjelasan arti istilah..." required></textarea>
            <div style="display:flex; gap:12px; margin-top:12px;">
                <button type="submit" class="btn btn-success" style="flex:1;">Simpan</button>
                <button type="button" class="btn btn-danger" onclick="document.getElementById('formAddVoc').close()" style="flex:1;">Batal</button>
            </div>
        </form>
    </dialog>
    """ if session.get('role') == 'admin' else ""

    content = f"""
    <a href="{url_for('mathvocab')}" class="btn" style="background:#64748b; margin-bottom:28px;"><i class="fas fa-arrow-left"></i> Kembali ke Daftar Kategori</a>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:32px;">
        <div>
            <h2 style="font-size:1.8rem; font-weight:800; margin-bottom:4px;">Kategori: {cat.name}</h2>
            <p style="color:var(--text-muted); font-size:1.05rem;">Daftar istilah dan definisi lengkap.</p>
        </div>
        {add_v}
    </div>
    <div style="display:flex; flex-direction:column; gap:20px;">{voc_html}</div>
    """
    return render_page(f"MathVocab - {cat.name}", content)

# ==========================================
# 13. PENCAPAIAN SISWA
# ==========================================
@app.route('/pencapaian')
@login_required
def pencapaian():
    riwayat = RiwayatPengerjaan.query.filter_by(user_id=session['user_id']).all()
    rows = "".join([f"""
    <tr>
        <td><b>{MateriSoal.query.get(r.materi_id).judul}</b></td>
        <td><span style="font-size:1.2rem; font-weight:800; color:#4f46e5;">{r.skor_tertinggi}</span></td>
        <td><span style="background:#e0e7ff; color:#4f46e5; padding:6px 14px; border-radius:20px; font-weight:700; font-size:0.85rem;">{r.status_ujian}</span></td>
        <td><span style="color:var(--text-muted); font-size:0.95rem;">{r.terakhir_dikerjakan.strftime('%d %b %Y, %H:%M') if r.terakhir_dikerjakan else '-'}</span></td>
    </tr>
    """ for r in riwayat])
    if not rows: rows = '<tr><td colspan="4" style="text-align:center; color:var(--text-muted); padding:40px; font-size:1.05rem;">Belum ada riwayat pengerjaan ujian.</td></tr>'

    content = f"""
    <div style="margin-bottom:32px;">
        <h1 style="font-size:2.2rem; font-weight:800; margin-bottom:8px;"><i class="fas fa-trophy" style="color:var(--warning);"></i> Pencapaian & Statistik Belajar</h1>
        <p style="color:var(--text-muted); font-size:1.1rem;">Rekapitulasi nilai dan status koreksi ujian yang telah Anda kerjakan.</p>
    </div>
    <div class="card">
        <table>
            <thead><tr><th>Judul Ujian / Materi</th><th>Total Nilai</th><th>Status Koreksi</th><th>Waktu Pengerjaan</th></tr></thead>
            <tbody>{rows}</tbody>
        </table>
    </div>
    """
    return render_page("Pencapaian", content)

@app.route('/logout')
def logout():
    session.clear()
    flash('Anda berhasil keluar dari sistem.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)