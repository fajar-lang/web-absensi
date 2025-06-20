from flask import Flask, render_template, request, redirect, session, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import functools

app = Flask(__name__)
app.secret_key = "rahasia_rohis_2024"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///rohis.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = False

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
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(128))
    
    def check_password(self, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password, password)
        
    def set_password(self, password):
        from werkzeug.security import generate_password_hash
        self.password = generate_password_hash(password)

class Absen(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100))
    tanggal = db.Column(db.String(20))
    waktu = db.Column(db.String(20))
    lokasi = db.Column(db.String(200))

class Keuangan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tanggal = db.Column(db.String(20))
    keterangan = db.Column(db.String(200))
    jenis = db.Column(db.String(10))
    jumlah = db.Column(db.Float)
    catatan = db.Column(db.String(200))  # <-- INI letak field catatan

@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.route('/', methods=['GET', 'POST'])
def absen():
    if session.get('admin'):
        return redirect(url_for('admin'))

    if request.method == 'POST':
        nama = request.form.get('nama', '').strip()
        lokasi = request.form.get('lokasi', '').strip()
        if not nama or not lokasi:
            flash("Nama dan lokasi harus diisi!", "danger")
            return render_template('absen.html')

        now = datetime.now()
        baru = Absen(
            nama=nama,
            tanggal=now.strftime("%Y-%m-%d"),
            waktu=now.strftime("%H:%M:%S"),
            lokasi=lokasi
        )
        db.session.add(baru)
        db.session.commit()
        flash("Absen berhasil. Terima kasih!", "success")
        return redirect(url_for('absen'))

    return render_template('absen.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        admin = Admin.query.filter_by(username=request.form.get('username')).first()
        if admin and admin.check_password(request.form.get('password')):
            session['admin'] = True
            return redirect(url_for('admin'))
        flash("Username atau password salah!", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('admin', None)
    session.pop('anggota', None)
    return redirect(url_for('login'))

@app.route('/admin')
@admin_required
def admin():
    data = Absen.query.order_by(Absen.tanggal.desc(), Absen.waktu.desc()).all()
    total_masuk = db.session.query(db.func.sum(Keuangan.jumlah)).filter_by(jenis='masuk').scalar() or 0
    total_keluar = db.session.query(db.func.sum(Keuangan.jumlah)).filter_by(jenis='keluar').scalar() or 0
    return render_template('admin.html', 
                         absensi=data, 
                         saldo=total_masuk - total_keluar, 
                         total_masuk=total_masuk, 
                         total_keluar=total_keluar)

@app.route('/keuangan', methods=['GET', 'POST'])
def keuangan():
    if not session.get('admin'):
        return redirect(url_for('keuangan_view'))

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

    # Tampilkan semua transaksi (termasuk kas)
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

@app.route('/edit_absen/<int:absen_id>', methods=['GET', 'POST'])
@admin_required
def edit_absen(absen_id):
    absen = Absen.query.get_or_404(absen_id)
    if request.method == 'POST':
        absen.nama = request.form.get('nama')
        absen.tanggal = request.form.get('tanggal')
        absen.waktu = request.form.get('waktu')
        absen.lokasi = request.form.get('lokasi')
        db.session.commit()
        flash('Data absen berhasil diupdate!', 'success')
        return redirect(url_for('admin'))
    return render_template('edit_absen.html', absen=absen)

@app.route('/hapus_absen/<int:absen_id>', methods=['POST'])
@admin_required
def hapus_absen(absen_id):
    absen = Absen.query.get_or_404(absen_id)
    db.session.delete(absen)
    db.session.commit()
    flash('Data absen berhasil dihapus!', 'success')
    return redirect(url_for('admin'))

@app.route('/ganti_password', methods=['GET', 'POST'])
@admin_required
def ganti_password():
    admin = Admin.query.filter_by(username='admin').first()
    if request.method == 'POST':
        old = request.form.get('old_password')
        new = request.form.get('new_password')
        confirm = request.form.get('confirm_password')
        
        if not admin.check_password(old):
            flash("Password lama salah!", "danger")
        elif new != confirm:
            flash("Password baru tidak sama!", "danger")
        elif not new:
            flash("Password baru tidak boleh kosong!", "danger")
        else:
            admin.set_password(new)
            db.session.commit()
            flash("Password berhasil diganti!", "success")
            return redirect(url_for('admin'))
    return render_template('ganti_password.html')

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
                keterangan='Uang Kas',  # hanya tampil "Uang Kas" di keuangan
                jenis='kas',
                jumlah=float(jumlah),
                catatan=nama  # tambahkan field catatan di model Keuangan jika belum ada
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

# Route publik untuk keuangan
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

def setup_default_users():
    db.create_all()
    if not Admin.query.filter_by(username='admin').first():
        admin = Admin(username='admin')
        admin.set_password('rohis123')
        db.session.add(admin)
    if not Anggota.query.filter_by(username='anggota').first():
        anggota = Anggota(username='anggota')
        anggota.set_password('anggota123')
        db.session.add(anggota)
    db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        setup_default_users()
    app.run(host='0.0.0.0', port=5000)
