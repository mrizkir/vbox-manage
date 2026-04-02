"""
Controller: Menghubungkan route (view layer) dengan model (VBoxService).
Tidak berisi logika SOAP; hanya memanggil model dan merender template / redirect.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, current_app, request
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


def _redirect_after_vm_action(machine_id):
    """Dari halaman detail (`next=detail` di URL form), kembali ke detail; selain itu ke daftar."""
    if request.args.get("next") == "detail":
        return redirect(url_for("vm.vm_detail", machine_id=machine_id))
    return redirect(url_for("vm.index"))


@vm_bp.route("/vm/<machine_id>/start", methods=["POST"])
def start_vm(machine_id):
    """Jalankan VM lalu redirect ke halaman detail dengan flash message."""
    vbox = _get_vbox()
    ok, msg = vbox.start_vm(machine_id)
    if ok:
        flash("VM berhasil dijalankan.", "success")
    else:
        flash(f"Gagal menjalankan VM: {msg}", "error")
    return _redirect_after_vm_action(machine_id)


@vm_bp.route("/vm/<machine_id>/stop", methods=["POST"])
def stop_vm(machine_id):
    """Matikan VM paksa (IConsole_powerDown), alur langkah 8 di vboxwebsrv-SOAP-reference.md."""
    vbox = _get_vbox()
    ok, msg = vbox.stop_vm(machine_id, graceful=False)
    if ok:
        flash("VM dihentikan (paksa, setara powerDown).", "success")
    else:
        flash(f"Gagal menghentikan VM: {msg}", "error")
    return _redirect_after_vm_action(machine_id)


@vm_bp.route("/vm/<machine_id>/stop-graceful", methods=["POST"])
def stop_vm_graceful(machine_id):
    """Kirim sinyal mati halus (IConsole_powerButton); OS di dalam VM yang mendukung bisa shutdown rapi."""
    vbox = _get_vbox()
    ok, msg = vbox.stop_vm(machine_id, graceful=True)
    if ok:
        flash(
            "Sinyal matikan halus dikirim. Jika OS di dalam VM mendukung, VM akan mati setelah shutdown normal.",
            "success",
        )
    else:
        flash(f"Gagal mengirim matikan halus: {msg}", "error")
    return _redirect_after_vm_action(machine_id)


@vm_bp.route("/vm/<machine_id>")
def vm_detail(machine_id):
    """Detail satu VM: SOAP IMachine_* (nama, status, UUID, CPU, RAM, OS), lalu vm_detail.html."""
    vbox = _get_vbox()
    vm, error = vbox.get_machine_detail(machine_id)
    if error:
        flash(error, "error")
        return redirect(url_for("vm.index"))
    return render_template("vm_detail.html", vm=vm)
