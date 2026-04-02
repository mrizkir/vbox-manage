# VBox-Manage

A Flask-based web dashboard for managing VirtualBox virtual machines — start, stop, monitor, and control VMs with ease via VBoxWebSrv API.

## 📋 Deskripsi

VBox-Manage adalah aplikasi web ringan yang dibangun menggunakan Flask untuk mengelola Virtual Machine (VM) di VirtualBox melalui antarmuka browser. Aplikasi ini berkomunikasi dengan VirtualBox melalui VBoxWebSrv menggunakan protokol SOAP, sehingga memudahkan pengelolaan VM tanpa harus menggunakan command line.

Proyek ini cocok digunakan sebagai alat pembelajaran untuk memahami bagaimana cloud management console bekerja dalam mengelola infrastruktur virtual.

## ✨ Fitur

- Daftar Virtual Machine (nama, status) dengan tautan ke halaman detail
- Halaman detail per VM: UUID, jumlah vCPU, RAM (MB), tipe OS (`IMachine_getOSTypeId`), status
- Menjalankan VM (headless), menghentikan paksa, dan matikan halus (ACPI / tombol daya)
- Identitas VM di URL memakai **UUID** mesin (bukan handle SOAP yang berubah tiap request)
- Pesan sukses/error lewat flash message; dari halaman detail, aksi Start/Stop mengarah kembali ke detail (`?next=detail`)

Untuk contoh body SOAP mentah (curl, urutan langkah), lihat **[vboxwebsrv-SOAP-reference.md](vboxwebsrv-SOAP-reference.md)**.

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

### 4. Konfigurasi
File `config.py` tidak di-commit (ada di `.gitignore`). Setelah clone, salin template konfigurasi:
```bash
cp config.example.py config.py
```
Atau set variabel lingkungan: `VBOX_HOST`, `VBOX_PORT`, `VBOX_USER`, `VBOX_PW` (logon vboxwebsrv), `SECRET_KEY`.

### 5. Jalankan VBoxWebSrv
```bash
# macOS/Linux
vboxwebsrv --host 127.0.0.1 --port 18083

# Windows
VBoxWebSrv.exe --host 127.0.0.1 --port 18083
```

### 6. Jalankan aplikasi Flask
```bash
python app.py
```

### 7. Akses di browser
```
http://localhost:5000
```

## 📁 Struktur Project (MVC)

- **Model**: `models/vbox_service.py` — klien SOAP (requests + `xml.etree`): `list_machines`, `get_machine_detail`, `resolve_machine_ref`, `start_vm`, `stop_vm`. Ubah di sini jika format SOAP/endpoint berubah.
- **Referensi SOAP**: [vboxwebsrv-SOAP-reference.md](vboxwebsrv-SOAP-reference.md) — contoh permintaan ke vboxwebsrv (login, daftar VM, properti mesin, start/stop).
- **View**: `templates/` — Jinja2. Ubah tampilan hanya di sini; bisa pakai partial (`templates/partials/`) dan filter Jinja.
- **Controller**: `controllers/vm_controller.py` — route Flask yang memanggil model dan me-render view.

```
vbox-manage/
├── app.py                  # Entry point, create_app(), register blueprint
├── config.py               # Konfigurasi (dipakai saat jalan; bisa di .gitignore)
├── config.example.py      # Template config untuk di-commit; setelah clone: cp config.example.py config.py
├── requirements.txt
├── models/
│   └── vbox_service.py     # SOAP client (list_machines, get_machine_detail, start_vm, stop_vm, …)
├── controllers/
│   └── vm_controller.py    # Blueprint vm_bp
├── templates/
│   ├── base.html           # Layout + flash messages
│   ├── index.html          # Daftar VM
│   ├── vm_detail.html      # Detail satu VM
│   └── partials/           # Partial template (contoh: _vm_row.html)
├── static/
│   └── style.css           # CSS tambahan (opsional)
├── .gitignore
├── LICENSE
├── README.md
└── vboxwebsrv-SOAP-reference.md   # Referensi SOAP vboxwebsrv (bahasa Indonesia)
```

## 🛣️ Route

`machine_id` di path adalah **UUID** mesin (dari `IMachine_getId`), URL-encoded jika mengandung `{` `}`.

Pemetaan ke dokumentasi SOAP lokal: **[vboxwebsrv-SOAP-reference.md](vboxwebsrv-SOAP-reference.md)** — bagian utama ada di **langkah 4–langkah 8** pada [SOAP — contoh permintaan](vboxwebsrv-SOAP-reference.md#soap-contoh-permintaan) (login langkah 4, daftar langkah 5, detail langkah 6, start langkah 7, stop langkah 8).

| Method | Path | Keterangan | SOAP (lihat referensi) |
|--------|------|------------|-------------------------|
| GET | `/` | Daftar VM | [langkah 5 — Daftar VM — `IVirtualBox_getMachines`](vboxwebsrv-SOAP-reference.md#5-daftar-vm-ivirtualbox_getmachines) |
| GET | `/vm/<machine_id>` | Detail VM (nama, status, UUID, vCPU, RAM, tipe OS) | [langkah 6 — Detail sebuah VM](vboxwebsrv-SOAP-reference.md#6-detail-sebuah-vm) (`IMachine_getName`, `getState`, `getId`, `getCPUCount`, `getMemorySize`, `getOSTypeId`) |
| POST | `/vm/<machine_id>/start` | Jalankan VM (headless), lalu redirect ke `/` atau kembali ke detail jika form memakai `?next=detail` | [langkah 7 — Menjalankan VM](vboxwebsrv-SOAP-reference.md#7-menjalankan-vm-menjadi-poweredon) (`getSessionObject`, `IMachine_launchVMProcess`) |
| POST | `/vm/<machine_id>/stop` | Hentikan paksa (`IConsole_powerDown`) | [langkah 8 — Mematikan VM](vboxwebsrv-SOAP-reference.md#8-mematikan-vm-poweredoff) |
| POST | `/vm/<machine_id>/stop-graceful` | Sinyal mati halus (`IConsole_powerButton`) | [langkah 8.5 — Tombol daya — `IConsole_powerButton`](vboxwebsrv-SOAP-reference.md#85-opsional-tombol-daya-iconsole_powerbutton) |

Alur persiapan host (auth webservice, menjalankan `vboxwebsrv`) dijelaskan di awal [vboxwebsrv-SOAP-reference.md](vboxwebsrv-SOAP-reference.md#persiapan-di-komputer-host).

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