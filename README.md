# VBox-Manage

A Flask-based web dashboard for managing VirtualBox virtual machines — start, stop, monitor, and control VMs with ease via VBoxWebSrv API.

## 📋 Deskripsi

VBox-Manage adalah aplikasi web ringan yang dibangun menggunakan Flask untuk mengelola Virtual Machine (VM) di VirtualBox melalui antarmuka browser. Aplikasi ini berkomunikasi dengan VirtualBox melalui VBoxWebSrv menggunakan protokol SOAP, sehingga memudahkan pengelolaan VM tanpa harus menggunakan command line.

Proyek ini cocok digunakan sebagai alat pembelajaran untuk memahami bagaimana cloud management console bekerja dalam mengelola infrastruktur virtual.

## ✨ Fitur

- Melihat daftar Virtual Machine yang tersedia
- Menjalankan (start) dan menghentikan (stop) VM
- Monitoring status VM secara real-time
- Antarmuka web yang sederhana dan mudah digunakan

## 🛠️ Teknologi

- **Python 3.11**
- **Flask** — Web framework
- **VBoxWebSrv** — VirtualBox Web Service (SOAP API)
- **requests** — HTTP library untuk komunikasi SOAP

## ⚙️ Prasyarat

Pastikan sudah terinstall:

- Python 3.11 atau lebih baru
- VirtualBox (dengan VBoxWebSrv aktif)
- pip

## 🚀 Instalasi

### 1. Clone repositori
```bash
git clone https://github.com/mrizkir/vbox-manage.git
cd vbox-manage
```

### 2. Buat virtual environment
```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependensi
```bash
pip install -r requirements.txt
```

### 4. Jalankan VBoxWebSrv
```bash
# macOS/Linux
vboxwebsrv --authentication null --host 127.0.0.1 --port 18083

# Windows
VBoxWebSrv.exe --authentication null --host 127.0.0.1 --port 18083
```

### 5. Jalankan aplikasi Flask
```bash
python app.py
```

### 6. Akses di browser
```
http://localhost:5000
```

## 📁 Struktur Project
```
vbox-manage/
├── app.py              # File utama aplikasi Flask
├── requirements.txt    # Daftar dependensi Python
├── .gitignore          # File yang diabaikan git
├── LICENSE             # Lisensi MIT
└── README.md           # Dokumentasi project
```

## 📦 Requirements

Generate file requirements.txt dengan perintah:
```bash
pip freeze > requirements.txt
```

## 🤝 Kontribusi

Kontribusi sangat terbuka! Silakan fork repositori ini dan buat pull request untuk perbaikan atau penambahan fitur.

1. Fork project ini
2. Buat branch fitur (`git checkout -b feature/NamaFitur`)
3. Commit perubahan (`git commit -m 'add: tambah fitur baru'`)
4. Push ke branch (`git push origin feature/NamaFitur`)
5. Buat Pull Request

## 📄 Lisensi

Proyek ini menggunakan lisensi [MIT](LICENSE).

## 👤 Author

**Mochammad Rizki Romdoni**  
GitHub: [@mrizkir](https://github.com/mrizkir)