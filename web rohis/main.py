from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import functools
import math

app = Flask(__name__)
app.secret_key = "rahasia_rohis_2024"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rohis.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

def admin_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin'):
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(128))
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, password)
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(password)

class Anggota(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    kelas = db.Column(db.String(50))

class Absen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    tanggal = db.Column(db.String(20))
    waktu = db.Column(db.String(20))
    lokasi = db.Column(db.String(200))
    kegiatan_id = db.Column(db.Integer, db.ForeignKey('kegiatan.id'))

class Keuangan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.String(20))
    keterangan = db.Column(db.String(200))
    jenis = db.Column(db.String(10))
    jumlah = db.Column(db.Float)
    catatan = db.Column(db.String(200))

class Kegiatan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    lokasi = db.Column(db.String(200))
    status = db.Column(db.String(10), default='aktif')  # 'aktif' atau 'nonaktif'

class Kultum(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(200), nullable=False)
    isi = db.Column(db.Text, nullable=False)
    tanggal = db.Column(db.String(20), nullable=False)

class Pengumuman(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    judul = db.Column(db.String(200), nullable=False)
    isi = db.Column(db.Text, nullable=False)
    tanggal = db.Column(db.String(20), nullable=False)

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

@app.route('/')
def landing():
    return render_template('landing.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form.get('username')).first()
        if admin and admin.check_password(request.form.get('password')):
            session['admin'] = True
            return redirect(url_for('admin'))
        flash("Username atau password salah!", "danger")
    return render_template('login.html')

@app.route('/login_anggota', methods=['GET', 'POST'])
def login_anggota():
    if request.method == 'POST':
        nama = request.form.get('nama')
        session['anggota'] = nama
        flash(f"Selamat datang, {nama}!", "success")
        return redirect(url_for('absen'))
    return render_template('login_anggota.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('anggota', None)
    return redirect(url_for('landing'))

@app.route('/absen', methods=['GET', 'POST'])
def absen():
    if not session.get('anggota'):
        return redirect(url_for('login_anggota'))
    kegiatan_list = Kegiatan.query.all()
    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        lokasi = request.form.get('lokasi', '').strip()
        kegiatan_id = request.form.get('kegiatan_id')
        if not nama or not lokasi or not kegiatan_id:
            flash("Nama, kegiatan, dan lokasi harus diisi!", "danger")
            return render_template('absen.html', kegiatan_list=kegiatan_list)
        kegiatan = Kegiatan.query.get(int(kegiatan_id))
        if not kegiatan or not kegiatan.lokasi:
            flash("Lokasi kegiatan belum ditetapkan admin!", "danger")
            return render_template('absen.html', kegiatan_list=kegiatan_list)
        try:
            lat1, lon1 = map(float, lokasi.split(','))
            lat2, lon2 = map(float, kegiatan.lokasi.split(','))
            jarak = haversine(lat1, lon1, lat2, lon2)
        except Exception:
            flash("Format lokasi tidak valid!", "danger")
            return render_template('absen.html', kegiatan_list=kegiatan_list)
        if jarak > 100:
            flash("Anda berada lebih dari 100 meter dari lokasi kegiatan. Absen dinyatakan TIDAK HADIR.", "danger")
            return render_template('absen.html', kegiatan_list=kegiatan_list)
        now = datetime.now()
        baru = Absen(
            nama=nama,
            tanggal=now.strftime("%Y-%m-%d"),
            waktu=now.strftime("%H:%M:%S"),
            lokasi=lokasi,
            kegiatan_id=kegiatan_id
        )
        db.session.add(baru)
        db.session.commit()
        flash("Absen berhasil. Terima kasih!", "success")
        return redirect(url_for('absen'))
    return render_template('absen.html', kegiatan_list=kegiatan_list)

@app.route('/admin')
@admin_required
def admin():
    absensi = Absen.query.order_by(Absen.tanggal.desc(), Absen.waktu.desc()).all()
    kegiatan_list = Kegiatan.query.all()
    tanggal_list = db.session.query(Absen.tanggal).distinct().order_by(Absen.tanggal.desc()).all()
    anggota_absen = db.session.query(Absen.nama).distinct().all()
    return render_template(
        'admin.html',
        absensi=absensi,
        kegiatan_list=kegiatan_list,
        tanggal_list=[t[0] for t in tanggal_list],
        anggota_absen=[a[0] for a in anggota_absen]
    )

@app.route('/keuangan', methods=['GET', 'POST'])
@admin_required
def keuangan():
    if request.method == 'POST':
        tanggal = request.form.get('tanggal')
        keterangan = request.form.get('keterangan')
        jenis = request.form.get('jenis')
        jumlah = request.form.get('jumlah')
        if tanggal and keterangan and jenis and jumlah:
            db.session.add(Keuangan(
                tanggal=tanggal,
                keterangan=keterangan,
                jenis=jenis,
                jumlah=float(jumlah)
            ))
            db.session.commit()
            flash("Data keuangan berhasil ditambahkan!", "success")
        else:
            flash("Semua field harus diisi!", "danger")
        return redirect(url_for('keuangan'))
    data = Keuangan.query.order_by(Keuangan.tanggal.desc()).all()
    total_masuk = db.session.query(db.func.sum(Keuangan.jumlah)).filter(Keuangan.jenis.in_(['masuk', 'kas'])).scalar() or 0
    total_keluar = db.session.query(db.func.sum(Keuangan.jumlah)).filter_by(jenis='keluar').scalar() or 0
    return render_template('keuangan.html',
                           data=data,
                           saldo=total_masuk - total_keluar,
                           total_masuk=total_masuk,
                           total_keluar=total_keluar)

@app.route('/keuangan/delete/<int:uang_id>', methods=['POST'])
@admin_required
def hapus_keuangan(uang_id):
    item = Keuangan.query.get_or_404(uang_id)
    db.session.delete(item)
    db.session.commit()
    flash('Data keuangan berhasil dihapus!', "success")
    return redirect(url_for('keuangan'))

@app.route('/keuangan_anggota')
def keuangan_anggota():
    data = Keuangan.query.order_by(Keuangan.tanggal.desc()).all()
    total_masuk = db.session.query(db.func.sum(Keuangan.jumlah)).filter_by(jenis='masuk').scalar() or 0
    total_keluar = db.session.query(db.func.sum(Keuangan.jumlah)).filter_by(jenis='keluar').scalar() or 0
    return render_template('keuangan.html',
                         data=data,
                         saldo=total_masuk - total_keluar,
                         total_masuk=total_masuk,
                         total_keluar=total_keluar,
                         is_admin=False)

@app.route('/keuangan_view')
def keuangan_view():
    data = Keuangan.query.order_by(Keuangan.tanggal.desc()).all()
    total_masuk = db.session.query(db.func.sum(Keuangan.jumlah)).filter_by(jenis='masuk').scalar() or 0
    total_keluar = db.session.query(db.func.sum(Keuangan.jumlah)).filter_by(jenis='keluar').scalar() or 0
    return render_template('keuangan_view.html',
                         data=data,
                         saldo=total_masuk - total_keluar,
                         total_masuk=total_masuk,
                         total_keluar=total_keluar)

@app.route('/kas_lunas', methods=['GET', 'POST'])
@admin_required
def kas_lunas():
    if request.method == 'POST':
        nama = request.form.get('nama')
        tanggal = request.form.get('tanggal')
        jumlah = request.form.get('jumlah')
        if nama and tanggal and jumlah:
            db.session.add(Keuangan(
                tanggal=tanggal,
                keterangan='Uang Kas',
                jenis='kas',
                jumlah=float(jumlah),
                catatan=nama
            ))
            db.session.commit()
            flash("Data pembayaran kas berhasil ditambahkan!", "success")
        else:
            flash("Semua field harus diisi!", "danger")
        return redirect(url_for('kas_lunas'))
    kas_data = Keuangan.query.filter_by(jenis='kas').order_by(Keuangan.tanggal.desc()).all()
    return render_template('kas_lunas.html', kas_data=kas_data)

@app.route('/kas_lunas/delete/<int:kas_id>', methods=['POST'])
@admin_required
def hapus_kas(kas_id):
    kas = Keuangan.query.get_or_404(kas_id)
    db.session.delete(kas)
    db.session.commit()
    flash('Data pembayaran kas berhasil dihapus!', "success")
    return redirect(url_for('kas_lunas'))

@app.route('/kas_lunas_anggota')
def kas_lunas_anggota():
    kas_data = Keuangan.query.filter_by(jenis='kas').order_by(Keuangan.tanggal.desc()).all()
    return render_template('kas_lunas.html', kas_data=kas_data)

@app.route('/kultum', methods=['GET', 'POST'])
@admin_required
def kultum():
    if request.method == 'POST':
        judul = request.form.get('judul')
        isi = request.form.get('isi')
        tanggal = datetime.now().strftime("%Y-%m-%d")
        db.session.add(Kultum(judul=judul, isi=isi, tanggal=tanggal))
        db.session.commit()
        flash("Kultum berhasil ditambahkan!", "success")
        return redirect(url_for('kultum'))
    data = Kultum.query.order_by(Kultum.tanggal.desc()).all()
    return render_template('kultum.html', data=data)

@app.route('/kultum_anggota')
def kultum_anggota():
    data = Kultum.query.order_by(Kultum.tanggal.desc()).all()
    return render_template('kultum.html', data=data, is_admin=False)

@app.route('/pengumuman', methods=['GET', 'POST'])
@admin_required
def pengumuman():
    if request.method == 'POST':
        judul = request.form.get('judul')
        isi = request.form.get('isi')
        tanggal = datetime.now().strftime("%Y-%m-%d")
        db.session.add(Pengumuman(judul=judul, isi=isi, tanggal=tanggal))
        db.session.commit()
        flash("Pengumuman berhasil ditambahkan!", "success")
        return redirect(url_for('pengumuman'))
    data = Pengumuman.query.order_by(Pengumuman.tanggal.desc()).all()
    return render_template('pengumuman.html', data=data)

@app.route('/pengumuman_anggota')
def pengumuman_anggota():
    data = Pengumuman.query.order_by(Pengumuman.tanggal.desc()).all()
    return render_template('pengumuman.html', data=data, is_admin=False)

@app.route('/kegiatan', methods=['GET', 'POST'])
@admin_required
def kegiatan():
    if request.method == 'POST':
        nama = request.form.get('nama')
        lokasi = request.form.get('lokasi')
        if not nama or not lokasi:
            flash("Nama dan lokasi kegiatan wajib diisi!", "danger")
        else:
            db.session.add(Kegiatan(nama=nama, lokasi=lokasi))
            db.session.commit()
            flash("Kegiatan berhasil ditambahkan!", "success")
        return redirect(url_for('kegiatan'))
    data = Kegiatan.query.order_by(Kegiatan.id.desc()).all()
    return render_template('kegiatan.html', data=data)

@app.route('/kegiatan/delete/<int:id>', methods=['POST'])
@admin_required
def hapus_kegiatan(id):
    keg = Kegiatan.query.get_or_404(id)
    db.session.delete(keg)
    db.session.commit()
    flash("Kegiatan berhasil dihapus!", "success")
    return redirect(url_for('kegiatan'))

@app.route('/kegiatan/aktifkan/<int:id>', methods=['POST'])
@admin_required
def aktifkan_kegiatan(id):
    keg = Kegiatan.query.get_or_404(id)
    keg.status = 'aktif'
    db.session.commit()
    flash("Kegiatan diaktifkan!", "success")
    return redirect(url_for('kegiatan'))

@app.route('/kegiatan/nonaktifkan/<int:id>', methods=['POST'])
@admin_required
def nonaktifkan_kegiatan(id):
    keg = Kegiatan.query.get_or_404(id)
    keg.status = 'nonaktif'
    db.session.commit()
    flash("Kegiatan dinonaktifkan!", "warning")
    return redirect(url_for('kegiatan'))

@app.route('/anggota')
@admin_required
def anggota():
    data = Anggota.query.order_by(Anggota.nama).all()
    return render_template('anggota.html', data=data)

def setup_default_users():
    db.create_all()
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin')
        admin.set_password('rohis123')
        db.session.add(admin)
    db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        setup_default_users()
    app.run(host='0.0.0.0', port=5000)
