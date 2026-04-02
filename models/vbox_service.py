"""
Model: Layer akses ke VirtualBox via SOAP (vboxwebsrv).
Format permintaan mengikuti vboxwebsrv-SOAP-reference.md (POST root URL, elemen param tanpa prefix vbox:).
"""
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring
import requests

NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_VBOX = "http://www.virtualbox.org/"


def _register_namespaces():
    ET.register_namespace("soap", NS_SOAP)
    ET.register_namespace("vbox", NS_VBOX)


def _xml_text(val):
    if val is None:
        return ""
    s = str(val)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _soap_call(base_url, method_name, params=None, timeout=10):
    """
    Kirim SOAP ke root URL vboxwebsrv (sama seperti contoh di vboxwebsrv-SOAP-reference.md).
    params: dict nama elemen -> nilai string (elemen anak tanpa prefix vbox:).
    """
    params = params or {}
    parts = [
        f'<?xml version="1.0"?>',
        f'<SOAP-ENV:Envelope xmlns:SOAP-ENV="{NS_SOAP}" xmlns:vbox="{NS_VBOX}">',
        "<SOAP-ENV:Body>",
        f"<vbox:{method_name}>",
    ]
    for key, value in params.items():
        parts.append(f"<{key}>{_xml_text(value)}</{key}>")
    parts.append(f"</vbox:{method_name}></SOAP-ENV:Body></SOAP-ENV:Envelope>")
    payload = "".join(parts)

    headers = {"Content-Type": "text/xml"}
    try:
        r = requests.post(base_url, data=payload.encode("utf-8"), headers=headers, timeout=timeout)
        if not r.ok:
            body_preview = (r.text[:1500] + "…") if len(r.text) > 1500 else r.text
            msg = f"vboxwebsrv HTTP {r.status_code} {r.reason}\n\nResponse body:\n{body_preview}"
            raise RuntimeError(msg)
        root = fromstring(r.text)
        body_el = root.find(f".//{{{NS_SOAP}}}Body")
        if body_el is None:
            body_el = root.find(".//Body")
        if body_el is not None:
            fault = body_el.find(f"{{{NS_SOAP}}}Fault") or body_el.find("Fault")
            if fault is not None:
                faultstring = fault.find("faultstring") or fault.find(f"{{{NS_SOAP}}}faultstring")
                raise RuntimeError(faultstring.text if faultstring is not None and faultstring.text else "SOAP Fault")
            if len(body_el) > 0:
                return body_el[0]
        return None
    except requests.RequestException as e:
        err_detail = str(e)
        if hasattr(e, "response") and e.response is not None:
            body_preview = (e.response.text[:1500] + "…") if len(e.response.text) > 1500 else e.response.text
            err_detail = f"{e}\n\nResponse body:\n{body_preview}"
        raise RuntimeError(f"Koneksi vboxwebsrv gagal: {err_detail}") from e


def _local_tag(elem):
    if elem is None or not hasattr(elem, "tag"):
        return ""
    tag = elem.tag
    return tag.split("}", 1)[-1] if tag.startswith("{") else tag


def _find_returnval(response_el):
    if response_el is None:
        return None
    for child in response_el:
        if _local_tag(child) == "returnval":
            return child
    return None


def _extract_token_or_ref(response_el):
    """
    Nilai dari returnval: teks (token sesi / handle) atau href pada anak (ref objek).
    """
    rv = _find_returnval(response_el)
    if rv is None:
        return None
    text = (rv.text or "").strip()
    if text:
        return text
    href = rv.get("href")
    if href:
        return href
    for sub in rv:
        href = sub.get("href")
        if href:
            return href
        t = (sub.text or "").strip()
        if t:
            return t
    return None


def _extract_ref(response_el):
    """Prioritas href di returnval / subtree (kompatibel dengan getMachines)."""
    tok = _extract_token_or_ref(response_el)
    if tok:
        return tok
    if response_el is None:
        return None
    href = response_el.get("href")
    if href:
        return href
    for child in response_el:
        href = child.get("href")
        if href:
            return href
        for sub in child:
            href = sub.get("href")
            if href:
                return href
    return None


def _machine_refs_from_get_machines(response_el):
    """
    Parse IVirtualBox_getMachinesResponse.

    Satu VM: satu <returnval> berisi teks handle.
    Beberapa VM: beberapa elemen <returnval> bersaudara, masing-masing berisi satu handle
    (bukan satu returnval berisi banyak id).
    Alternatif: satu <returnval> dengan anak ber-atribut href (SOAP-ENC array).
    """
    if response_el is None:
        return []
    refs = []
    seen = set()

    def add_ref(t):
        t = (t or "").strip()
        if not t or t in seen:
            return
        seen.add(t)
        refs.append(t)

    for el in response_el.iter():
        if _local_tag(el) != "returnval":
            continue
        add_ref(el.text)
        h = el.get("href")
        if h:
            add_ref(h)
        for child in el:
            ch = child.get("href")
            if ch:
                add_ref(ch)
            add_ref(child.text)
    return refs


def _extract_text(element):
    if element is None:
        return ""
    rv = _find_returnval(element)
    if rv is not None:
        t = (rv.text or "").strip()
        if t:
            return t
        if len(rv) > 0 and (rv[0].text or "").strip():
            return (rv[0].text or "").strip()
    return (element.text or "").strip() or (next((e.text for e in element), "") or "")


def _uuid_match(a, b):
    """Bandingkan UUID mesin (abaikan case, kurung kurawal opsional)."""
    def key(s):
        t = (s or "").strip().lower()
        if len(t) >= 2 and t[0] == "{" and t[-1] == "}":
            t = t[1:-1]
        return t

    return key(a) == key(b) and bool(key(a))


def _vm_state_is_running(state_val):
    """
    True jika VM dianggap menyala untuk tombol Start/Stop di UI.
    vboxwebsrv bisa mengembalikan nama enum (mis. Running, PoweredOn) atau angka MachineState.
    """
    s = (str(state_val).strip() if state_val is not None else "") or ""
    if not s:
        return False
    n = "".join(c for c in s.upper() if c not in " _")
    if n.startswith("MACHINESTATE"):
        n = n[len("MACHINESTATE") :]
    # Mesin benar-benar mati / tidak jalan (jangan pakai substring "POWEREDON" — bentrok dengan POWEREDOFF)
    if n in (
        "NULL",
        "POWEREDOFF",
        "SAVED",
        "ABORTED",
        "ABORTEDSNAPSHOTTING",
    ):
        return False
    if n in (
        "POWEREDON",
        "RUNNING",
        "PAUSED",
        "STARTING",
        "RESTORING",
        "STOPPING",
        "STUCK",
        "RESETTING",
        "SETTINGUP",
    ):
        return True
    if "RUNNING" in n:
        return True
    if n.startswith(("FIRSTONLINE", "LASTONLINE", "TELEPORTING", "LIVESNAPSHOTTING")):
        return True
    try:
        v = int(s)
    except ValueError:
        return False
    # Umum di SDK VirtualBox: PoweredOff=1, Saved=2, …, Running sering ≥ 5 (variasi versi)
    return v >= 5


class VBoxService:
    """
    Singleton-style service untuk VirtualBox SOAP.
    VB_TOKEN (returnval logon) dipakai sebagai _this untuk IVirtualBox_* dan refIVirtualBox untuk getSessionObject.
    """

    _instance = None

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/") + "/"
        self._vbox_token = None

    @classmethod
    def get_instance(cls, base_url=None):
        if cls._instance is None:
            from config import get_vbox_base_url
            cls._instance = cls(base_url or get_vbox_base_url())
        return cls._instance

    def _logon(self, username="", password=""):
        from config import VBOX_USER, VBOX_PW
        user = username or VBOX_USER
        pw = password or VBOX_PW
        result = _soap_call(
            self.base_url,
            "IWebsessionManager_logon",
            params={"username": user, "password": pw},
        )
        token = _extract_token_or_ref(result)
        if token:
            self._vbox_token = token
        return token

    def _ensure_vbox(self):
        if not self._vbox_token:
            self._logon()
        return self._vbox_token

    def list_machines(self):
        """
        Daftar semua VM: list of dict {id, name, state, running}.
        Mengembalikan ([], None) jika sukses, ([], "pesan error") jika gagal.
        """
        try:
            vbox_token = self._logon()
            if not vbox_token:
                return [], "Tidak dapat logon ke vboxwebsrv (token kosong)."

            result = _soap_call(
                self.base_url,
                "IVirtualBox_getMachines",
                params={"_this": vbox_token},
            )
            if result is None:
                return [], "Response getMachines kosong."

            machine_refs = _machine_refs_from_get_machines(result)

            machines = []
            for ref in machine_refs:
                name_el = _soap_call(self.base_url, "IMachine_getName", params={"_this": ref})
                state_el = _soap_call(self.base_url, "IMachine_getState", params={"_this": ref})
                id_el = _soap_call(self.base_url, "IMachine_getId", params={"_this": ref})
                name = _extract_text(name_el) if name_el is not None else "?"
                state = _extract_text(state_el) if state_el is not None else "Unknown"
                machine_uuid = _extract_text(id_el) if id_el is not None else ""
                machine_uuid = machine_uuid.strip()
                # Handle SOAP tidak stabil antar request; UUID tetap sama untuk URL/detail.
                public_id = machine_uuid if machine_uuid else ref
                machines.append(
                    {
                        "id": public_id,
                        "name": name or ref,
                        "state": state,
                        "running": _vm_state_is_running(state),
                    }
                )

            return machines, None
        except RuntimeError as e:
            return [], str(e)
        except Exception as e:
            return [], str(e)

    def resolve_machine_ref(self, machine_id):
        """
        Ubah id publik (UUID dari IMachine_getId) jadi _this ref saat ini untuk SOAP.
        Jika machine_id sudah ref yang valid dari panggilan terbaru, kembalikan yang cocok.
        """
        try:
            vbox_token = self._ensure_vbox()
            result = _soap_call(
                self.base_url,
                "IVirtualBox_getMachines",
                params={"_this": vbox_token},
            )
            if result is None:
                return None
            for ref in _machine_refs_from_get_machines(result):
                id_el = _soap_call(self.base_url, "IMachine_getId", params={"_this": ref})
                mid = _extract_text(id_el) if id_el is not None else ""
                if mid and _uuid_match(mid, machine_id):
                    return ref
                if ref == machine_id:
                    return ref
            return None
        except Exception:
            return None

    def _imachine_int_property(self, ref, method_name):
        el = _soap_call(self.base_url, method_name, params={"_this": ref})
        raw = _extract_text(el) if el is not None else ""
        raw = (raw or "").strip()
        if not raw:
            return None
        try:
            return int(raw)
        except ValueError:
            return None

    def get_machine_detail(self, machine_id):
        """
        Satu VM lengkap untuk halaman detail: nama, status, UUID, CPU, RAM (MB), tipe OS.
        SOAP: IMachine_getName/State/Id/getCPUCount/getMemorySize/getOSTypeId (lihat vboxwebsrv-SOAP-reference.md §6).
        """
        try:
            ref = self.resolve_machine_ref(machine_id)
            if not ref:
                return None, "VM tidak ditemukan."

            name_el = _soap_call(self.base_url, "IMachine_getName", params={"_this": ref})
            state_el = _soap_call(self.base_url, "IMachine_getState", params={"_this": ref})
            id_el = _soap_call(self.base_url, "IMachine_getId", params={"_this": ref})
            name = _extract_text(name_el) if name_el is not None else "?"
            state = _extract_text(state_el) if state_el is not None else "Unknown"
            machine_uuid = (_extract_text(id_el) if id_el is not None else "").strip()
            public_id = machine_uuid if machine_uuid else ref

            cpu_count = self._imachine_int_property(ref, "IMachine_getCPUCount")
            memory_mb = self._imachine_int_property(ref, "IMachine_getMemorySize")
            os_el = _soap_call(self.base_url, "IMachine_getOSTypeId", params={"_this": ref})
            os_type_id = _extract_text(os_el) if os_el is not None else ""
            os_type_id = os_type_id.strip() or "—"

            vm = {
                "id": public_id,
                "name": name or ref,
                "state": state,
                "running": _vm_state_is_running(state),
                "cpu_count": cpu_count,
                "memory_mb": memory_mb,
                "os_type_id": os_type_id,
            }
            return vm, None
        except RuntimeError as e:
            return None, str(e)
        except Exception as e:
            return None, str(e)

    def start_vm(self, machine_id):
        """Jalankan VM (headless), alur seperti langkah 7 di vboxwebsrv-SOAP-reference.md."""
        try:
            ref = self.resolve_machine_ref(machine_id)
            if not ref:
                return False, "VM tidak ditemukan (UUID tidak dikenali)."
            vbox_token = self._ensure_vbox()
            session_result = _soap_call(
                self.base_url,
                "IWebsessionManager_getSessionObject",
                params={"refIVirtualBox": vbox_token},
            )
            session_ref = _extract_token_or_ref(session_result)
            if not session_ref:
                return False, "Tidak dapat mendapatkan session."

            _soap_call(
                self.base_url,
                "IMachine_launchVMProcess",
                params={"_this": ref, "session": session_ref, "type": "headless"},
            )
            return True, None
        except RuntimeError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def stop_vm(self, machine_id, graceful=False):
        """
        Matikan VM mengikuti langkah 8 di vboxwebsrv-SOAP-reference.md:
        getSessionObject → lockMachine(Shared) → getConsole → powerDown atau powerButton → unlockMachine.
        unlockMachine dipanggil di finally bila lock berhasil, agar kunci tidak tertinggal.
        """
        ref = self.resolve_machine_ref(machine_id)
        if not ref:
            return False, "VM tidak ditemukan (UUID tidak dikenali)."
        vbox_token = self._ensure_vbox()
        session_ref = None
        locked = False
        try:
            session_result = _soap_call(
                self.base_url,
                "IWebsessionManager_getSessionObject",
                params={"refIVirtualBox": vbox_token},
            )
            session_ref = _extract_token_or_ref(session_result)
            if not session_ref:
                return False, "Tidak dapat mendapatkan session."

            _soap_call(
                self.base_url,
                "IMachine_lockMachine",
                params={"_this": ref, "session": session_ref, "lockType": "Shared"},
            )
            locked = True

            console_result = _soap_call(
                self.base_url,
                "ISession_getConsole",
                params={"_this": session_ref},
            )
            console_ref = _extract_ref(console_result)
            if not console_ref:
                return False, "Tidak dapat mengakses konsol (VM mungkin tidak menyala)."

            if graceful:
                _soap_call(
                    self.base_url,
                    "IConsole_powerButton",
                    params={"_this": console_ref},
                )
            else:
                _soap_call(
                    self.base_url,
                    "IConsole_powerDown",
                    params={"_this": console_ref},
                )
            return True, None
        except RuntimeError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
        finally:
            if locked and session_ref:
                try:
                    _soap_call(
                        self.base_url,
                        "ISession_unlockMachine",
                        params={"_this": session_ref},
                    )
                except Exception:
                    pass
