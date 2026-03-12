"""
Controller: Menghubungkan route (view layer) dengan model (VBoxService).
Tidak berisi logika SOAP; hanya memanggil model dan merender template / redirect.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, current_app
from models.vbox_service import VBoxService

vm_bp = Blueprint("vm", __name__)


def _get_vbox():
    """Singleton VBoxService (pakai config dari app)."""
    base_url = current_app.config.get("VBOX_BASE_URL", "http://127.0.0.1:18083")
    return VBoxService.get_instance(base_url)


@vm_bp.route("/")
def index():
    """Daftar VM: panggil model, render template dengan machines dan error."""
    vbox = _get_vbox()
    machines, error = vbox.list_machines()
    return render_template("index.html", machines=machines, error=error)


@vm_bp.route("/vm/<machine_id>/start", methods=["POST"])
def start_vm(machine_id):
    """Jalankan VM lalu redirect ke index dengan flash message."""
    vbox = _get_vbox()
    ok, msg = vbox.start_vm(machine_id)
    if ok:
        flash("VM berhasil dijalankan.", "success")
    else:
        flash(f"Gagal menjalankan VM: {msg}", "error")
    return redirect(url_for("vm.index"))


@vm_bp.route("/vm/<machine_id>/stop", methods=["POST"])
def stop_vm(machine_id):
    """Matikan VM lalu redirect ke index dengan flash message."""
    vbox = _get_vbox()
    ok, msg = vbox.stop_vm(machine_id)
    if ok:
        flash("VM berhasil dihentikan.", "success")
    else:
        flash(f"Gagal menghentikan VM: {msg}", "error")
    return redirect(url_for("vm.index"))


@vm_bp.route("/vm/<machine_id>")
def vm_detail(machine_id):
    """Detail satu VM: ambil dari list, render vm_detail.html."""
    vbox = _get_vbox()
    machines, error = vbox.list_machines()
    if error:
        flash(error, "error")
        return redirect(url_for("vm.index"))
    vm = next((m for m in machines if m["id"] == machine_id), None)
    if not vm:
        flash("VM tidak ditemukan.", "error")
        return redirect(url_for("vm.index"))
    return render_template("vm_detail.html", vm=vm)
