"""
Model: Layer akses ke VirtualBox via SOAP (vboxwebsrv).
Semua komunikasi dengan VirtualBox hanya melalui modul ini.
Menggunakan requests untuk HTTP dan xml.etree untuk parsing response.
"""
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring
import requests

# Namespace VirtualBox SOAP (vboxwebsrv mengharapkan format IInterface_methodName)
NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_VBOX = "http://www.virtualbox.org/"


def _register_namespaces():
    ET.register_namespace("soap", NS_SOAP)
    ET.register_namespace("vbox", NS_VBOX)


def _soap_call(base_url, method_name, params=None, ref=None, param_no_prefix=False, soap_action=None, timeout=10):
    """
    Kirim SOAP request ke vboxwebsrv. method_name harus format IInterface_method (e.g. IWebsessionManager_logon).
    params: dict nama_param -> nilai (string atau ref dict).
    ref: managed object reference untuk method yang memerlukan 'this'.
    param_no_prefix: jika True, elemen param tanpa prefix vbox: (untuk logon dll).
    soap_action: jika diisi (e.g. '"#logon"'), dipakai untuk header SOAPAction; beberapa versi vboxwebsrv memakainya.
    """
    params = params or {}
    # vboxwebsrv mengharapkan SOAP-ENV / envelope standar
    payload = f'<?xml version="1.0" encoding="UTF-8"?><SOAP-ENV:Envelope xmlns:SOAP-ENV="{NS_SOAP}" xmlns:vbox="{NS_VBOX}"><SOAP-ENV:Body><vbox:{method_name}>'
    if ref:
        payload += f'<vbox:ref href="{ref if isinstance(ref, str) else ref.get("href", "")}"/>'
    for key, value in params.items():
        if isinstance(value, dict) and "href" in value:
            payload += f'<vbox:{key} href="{value["href"]}"/>'
        else:
            val = str(value) if value is not None else ""
            if param_no_prefix:
                payload += f"<{key}>{val}</{key}>"
            else:
                payload += f"<vbox:{key}>{val}</vbox:{key}>"
    payload += f"</vbox:{method_name}></SOAP-ENV:Body></SOAP-ENV:Envelope>"

    action = soap_action if soap_action is not None else f'"{NS_VBOX}{method_name}"'
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": action,
    }
    try:
        r = requests.post(base_url, data=payload.encode("utf-8"), headers=headers, timeout=timeout)
        if not r.ok:
            body_preview = (r.text[:1500] + "…") if len(r.text) > 1500 else r.text
            msg = f"vboxwebsrv HTTP {r.status_code} {r.reason}\n\nResponse body:\n{body_preview}"
            raise RuntimeError(msg)
        root = fromstring(r.text)
        # Fault bisa pakai SOAP-ENV atau soap
        body_el = root.find(f".//{{{NS_SOAP}}}Body")
        if body_el is None:
            body_el = root.find(".//Body")
        if body_el is not None:
            fault = body_el.find(f"{{{NS_SOAP}}}Fault") or body_el.find("Fault")
            if fault is not None:
                faultstring = fault.find("faultstring") or fault.find(f"{{{NS_SOAP}}}faultstring")
                raise RuntimeError(faultstring.text if faultstring is not None and faultstring.text else "SOAP Fault")
            # Return: elemen pertama di Body (response method)
            if len(body_el) > 0:
                return body_el[0]
        return None
    except requests.RequestException as e:
        err_detail = str(e)
        if hasattr(e, "response") and e.response is not None:
            body_preview = (e.response.text[:1500] + "…") if len(e.response.text) > 1500 else e.response.text
            err_detail = f"{e}\n\nResponse body:\n{body_preview}"
        raise RuntimeError(f"Koneksi vboxwebsrv gagal: {err_detail}") from e


def _extract_ref(element):
    """Ambil managed object reference (href) dari elemen response."""
    if element is None:
        return None
    href = element.get("href") if hasattr(element, "get") else None
    if href:
        return href
    for child in element:
        href = child.get("href")
        if href:
            return href
    return None


def _extract_text(element):
    """Ambil teks dari elemen."""
    if element is None:
        return ""
    return (element.text or "").strip() or (next((e.text for e in element), "") or "")


class VBoxService:
    """
    Singleton-style service untuk VirtualBox SOAP.
    Gunakan get_instance() atau buat satu instance dan pakai di controller.
    """

    _instance = None

    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")
        self._vbox_ref = None

    @classmethod
    def get_instance(cls, base_url=None):
        """Singleton accessor. base_url hanya dipakai saat pertama kali."""
        if cls._instance is None:
            from config import get_vbox_base_url
            cls._instance = cls(base_url or get_vbox_base_url())
        return cls._instance

    def _logon(self, username="", password=""):
        """Logon ke IWebsessionManager, dapatkan IVirtualBox ref. Pakai config VBOX_USER/VBOX_PW jika kosong."""
        from config import VBOX_USER, VBOX_PW
        user = username or VBOX_USER
        pw = password or VBOX_PW
        result = _soap_call(
            self.base_url,
            "IWebsessionManager_logon",
            params={"user": user, "password": pw},
            param_no_prefix=True,
            soap_action='"#logon"',
        )
        ref = _extract_ref(result)
        if ref:
            self._vbox_ref = ref
        return ref

    def _ensure_vbox(self):
        if not self._vbox_ref:
            self._logon()
        return self._vbox_ref

    def list_machines(self):
        """
        Daftar semua VM: list of dict {id, name, state}.
        Mengembalikan ([], None) jika sukses, ([], "pesan error") jika gagal.
        """
        try:
            vbox_ref = self._logon()
            if not vbox_ref:
                return [], "Tidak dapat logon ke vboxwebsrv (ref kosong)."

            # IVirtualBox::getMachines() -> array of IMachine ref
            result = _soap_call(self.base_url, "IVirtualBox_getMachines", ref=vbox_ref)
            if result is None:
                return [], "Response getMachines kosong."

            machine_refs = []
            def collect_refs(elem):
                if elem.get("href"):
                    machine_refs.append(elem.get("href"))
                for child in elem:
                    collect_refs(child)
            collect_refs(result)

            machines = []
            for ref in machine_refs:
                name_el = _soap_call(self.base_url, "IMachine_getName", ref=ref)
                state_el = _soap_call(self.base_url, "IMachine_getState", ref=ref)
                name = _extract_text(name_el) if name_el is not None else "?"
                state = _extract_text(state_el) if state_el is not None else "Unknown"
                # State bisa enum number; tampilkan sebagai string
                machines.append({"id": ref, "name": name or ref, "state": state})

            return machines, None
        except RuntimeError as e:
            return [], str(e)
        except Exception as e:
            return [], str(e)

    def start_vm(self, machine_id):
        """Jalankan VM (headless). Mengembalikan (True, None) atau (False, pesan error)."""
        try:
            self._ensure_vbox()
            session_result = _soap_call(self.base_url, "IWebsessionManager_getSessionObject")
            session_ref = _extract_ref(session_result)
            if not session_ref:
                return False, "Tidak dapat mendapatkan session."

            # IMachine::lockMachine(session, lockType) — ref = machine
            _soap_call(
                self.base_url,
                "IMachine_lockMachine",
                params={"session": {"href": session_ref}, "lockType": "Write"},
                ref=machine_id,
            )
            # launchVMProcess(session, type, environment)
            launch_result = _soap_call(
                self.base_url,
                "IMachine_launchVMProcess",
                params={"session": {"href": session_ref}, "type": "headless", "environment": ""},
                ref=machine_id,
            )
            if launch_result is not None or True:
                return True, None
            return False, "Launch VM tidak mengembalikan response."
        except RuntimeError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def stop_vm(self, machine_id):
        """Matikan VM (powerDown). Mengembalikan (True, None) atau (False, pesan error)."""
        try:
            session_result = _soap_call(self.base_url, "IWebsessionManager_getSessionObject")
            session_ref = _extract_ref(session_result)
            if not session_ref:
                return False, "Tidak dapat mendapatkan session."

            # lockMachine lalu getConsole -> powerDown -> unlockMachine
            _soap_call(
                self.base_url,
                "IMachine_lockMachine",
                params={"session": {"href": session_ref}, "lockType": "Shared"},
                ref=machine_id,
            )
            console_result = _soap_call(self.base_url, "ISession_getConsole", ref=session_ref)
            console_ref = _extract_ref(console_result)
            if console_ref:
                _soap_call(self.base_url, "IConsole_powerDown", ref=console_ref)
            _soap_call(self.base_url, "ISession_unlockMachine", ref=session_ref)
            return True, None
        except RuntimeError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
