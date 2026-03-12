"""
Konfigurasi aplikasi VBox-Manage (template).
Salin ke config.py setelah clone: cp config.example.py config.py
Nilai dapat di-override dengan variabel lingkungan.
"""
import os

# VirtualBox Web Service (vboxwebsrv)
VBOX_HOST = os.environ.get("VBOX_HOST", "127.0.0.1")
VBOX_PORT = os.environ.get("VBOX_PORT", "18083")

def get_vbox_base_url():
    """URL dasar vboxwebsrv (tanpa path)."""
    return f"http://{VBOX_HOST}:{VBOX_PORT}"

# Flask
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-ganti-di-production")
