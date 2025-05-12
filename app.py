from flask import Flask, request, redirect, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import shortuuid
import qrcode
import qrcode.image.svg
from qrcode.constants import ERROR_CORRECT_H
from io import BytesIO
import base64
import os
from PIL import Image, ImageDraw # type: ignore

app = Flask(__name__)

CORS(app, origins=["https://kodeqr.pkgwagir.or.id", "http://localhost:5173"])

if not os.path.exists('instance/urls.db'):
    file_db = open("instance/urls.db", "w")
    file_db.close()

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///urls.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class URL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    long_url = db.Column(db.String(255), nullable=False)
    short_code = db.Column(db.String(10), unique=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())

    def __repr__(self):
        return f'<URL {self.short_code}>'

@app.route('/api/shorten', methods=['POST'])
def shorten_url():
    data = request.json

    if data is None:
        return jsonify({'error': 'Invalid JSON or missing Content-Type: application/json'}), 415
    long_url = data.get('long_url')
    if not long_url:
        return jsonify({'error': 'URL Panjang diperlukan'}), 400

    short_code = shortuuid.uuid()[:6]

    while URL.query.filter_by(short_code=short_code).first():
        short_code = shortuuid.uuid()[:6]

    new_url = URL(long_url=long_url, short_code=short_code) # type: ignore
    db.session.add(new_url)
    db.session.commit()

    short_url = f"{request.url_root}{short_code}"

    return jsonify({'short_url': short_url, 'short_code': short_code}), 201

@app.route('/<short_code>')
def redirect_to_long_url(short_code):
    # url_entry = URL.query.filter_by(short_code=short_code).first()
    # if url_entry:
    #     return redirect('https://google.com')
    # else:
    #     return "URL not found", 404
    # Log 1: Masuk ke route
    app.logger.info(f"[[DEBUG]] เข้าถึง route redirect untuk: {short_code}") # Menggunakan penanda unik dan bahasa berbeda untuk memastikan terlihat jelas

    try:
        # Log 2: Sebelum memanggil redirect
        app.logger.info("[[DEBUG]] ก่อนเรียก fungsi redirect ke Google.")

        response = redirect("https://www.google.com")

        # Log 3: Setelah memanggil redirect (ini mungkin tidak tercapai jika redirect() segera mengembalikan respons)
        app.logger.info("[[DEBUG]] Setelah panggilan redirect berhasil.")

        return response

    except Exception as e:
        # Log Error jika terjadi Exception
        app.logger.error(f"[[DEBUG]] Terjadi Error saat redirect: {e}", exc_info=True)
        # Kembalikan status code yang berbeda untuk melihat apakah error logging berhasil
        return "Internal Server Error under construction", 500

@app.route('/api/generate-qr', methods=['POST'])
def generate_qr_code():
    data = request.json
    if data is None:
            return jsonify({'error': 'Invalid JSON or missing Content-Type: application/json'}), 415

    content = data.get('content') # Bisa URL atau teks
    if not content:
        return jsonify({'error': 'Parameter content diperlukan'}), 400

    # --- Tambahkan Nama File Logo Anda Di Sini ---
    # Pastikan file logo.png ada di lokasi yang sama dengan app.py
    logo_path = 'logo_pkg.png' # Ganti jika lokasi file logo berbeda

    # Periksa apakah file logo ada
    if not os.path.exists(logo_path):
        # Jika logo tidak ditemukan, generate QR code tanpa logo
        print(f"Warning: Logo file not found at {logo_path}. Generating QR code without logo.")
        # Lanjutkan dengan generate QR code biasa (dengan error correction H tetap disarankan)

        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_H, # Tetap gunakan H agar ada ruang di tengah
            box_size=10,
            border=4,
        )
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

            # Simpan gambar ke buffer dan encode ke base64 seperti sebelumnya
        buffer = BytesIO()
        img.save(buffer, format="PNG") # type: ignore
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        data_url = f"data:image/png;base64,{img_base64}"

        return jsonify({'qr_code_image': data_url, 'warning': 'Logo file not found'}), 200

    # --- Jika file logo ditemukan, proses dengan logo ---
    try:
        logo = Image.open(logo_path)
    except Exception as e:
        print(f"Error opening logo file: {e}")
        # Jika logo tidak bisa dibuka, generate QR code tanpa logo
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_H, # Tetap gunakan H
            box_size=10,
            border=4,
        )
        qr.add_data(content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = BytesIO()
        img.save(buffer, format="PNG") # type: ignore
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        data_url = f"data:image/png;base64,{img_base64}"

        return jsonify({'qr_code_image': data_url, 'warning': 'Error processing logo file'}), 200


    # Generate QR Code dengan error correction level H (High)
    qr = qrcode.QRCode(
        version=None, # Letakkan version=None agar qrcode otomatis memilih ukuran
        error_correction=ERROR_CORRECT_H, # Gunakan level HIGH
        box_size=10,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white").convert('RGB') # type: ignore # Pastikan mode RGB untuk paste

    # Hitung ukuran logo
    # Ukuran logo sebaiknya sekitar 20-30% dari ukuran QR Code
    base_width = img.size[0] # Ukuran QR Code
    logo_size = int(base_width / 4) # Misal, 1/4 dari ukuran QR Code

    # Resize logo
    # Pastikan logo dikonversi ke RGBA jika ada transparansi
    logo = logo.resize((logo_size, logo_size), Image.Resampling.LANCZOS) # Gunakan LANCZOS untuk kualitas lebih baik
    if logo.mode != 'RGBA':
            logo = logo.convert('RGBA')

    # Hitung posisi tengah untuk menempel logo
    pos = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)

    # Tempel logo ke QR Code
    # Gunakan logo itu sendiri sebagai mask jika mode RGBA
    img.paste(logo, pos, logo if logo.mode == 'RGBA' else None)


    # Simpan gambar hasil ke buffer dalam format PNG
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    # Encode buffer ke base64
    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    data_url = f"data:image/png;base64,{img_base64}"

    return jsonify({'qr_code_image': data_url}), 200
@app.route('/')
def index():
    return "Backend berjalan. Silahkan akses menggunakan frontend"

if __name__ == '__main__':
    #Buat tabel database bila belum ada
    with app.app_context():
        db.create_all()

    app.run(debug=True, host='0.0.0.0', port=5001)
