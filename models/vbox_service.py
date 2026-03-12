"""
Model: Layer akses ke VirtualBox via SOAP (vboxwebsrv).
Semua komunikasi dengan VirtualBox hanya melalui modul ini.
Menggunakan requests untuk HTTP dan xml.etree untuk parsing response.
"""
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import fromstring
import requests

# Namespace VirtualBox SOAP (sesuaikan dengan versi VirtualBox jika perlu)
NS_SOAP = "http://schemas.xmlsoap.org/soap/envelope/"
NS_VBOX = "http://www.virtualbox.org/"


def _register_namespaces():
    ET.register_namespace("soap", NS_SOAP)
    ET.register_namespace("vbox", NS_VBOX)


def _soap_call(base_url, method_name, params=None, ref=None, timeout=10):
    """
    Kirim SOAP request ke vboxwebsrv dan kembalikan response body sebagai ElementTree.
    params: dict nama_param -> nilai (string atau ref dict)
    ref: managed object reference untuk method yang memerlukan 'this'
    """
    params = params or {}
    envelope = ET.Element(f"{{{NS_SOAP}}}Envelope")
    envelope.set("xmlns:soap", NS_SOAP)
    envelope.set("xmlns:vbox", NS_VBOX)
    body = ET.SubElement(envelope, f"{{{NS_SOAP}}}Body")
    method_elem = ET.SubElement(body, f"{{{NS_VBOX}}}{method_name}")

    if ref:
        ref_elem = ET.SubElement(method_elem, f"{{{NS_VBOX}}}ref")
        ref_elem.set("href", ref if isinstance(ref, str) else ref.get("href", ""))

    for key, value in params.items():
        child = ET.SubElement(method_elem, f"{{{NS_VBOX}}}{key}")
        if isinstance(value, dict) and "href" in value:
            child.set("href", value["href"])
        else:
            child.text = str(value) if value is not None else ""

    xml_bytes = ET.tostring(envelope, encoding="unicode", default_namespace="")
    # Pastikan namespace prefix dipakai di root
    xml_str = f'<?xml version="1.0"?><soap:Envelope xmlns:soap="{NS_SOAP}" xmlns:vbox="{NS_VBOX}">{ET.tostring(envelope.find(f".//{{{NS_SOAP}}}Body"), encoding="unicode", method="xml").replace("<Body>", f"<soap:Body>").replace("</Body>", "</soap:Body>")}'
    # Build ulang agar konsisten
    body_inner = envelope.find(f".//{{{NS_SOAP}}}Body")[0]
    inner = ET.tostring(body_inner, encoding="unicode", default_namespace="")
    payload = f'<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="{NS_SOAP}" xmlns:vbox="{NS_VBOX}"><soap:Body><vbox:{method_name}>'
    if ref:
        payload += f'<vbox:ref href="{ref if isinstance(ref, str) else ref.get("href", "")}"/>'
    for key, value in params.items():
        if isinstance(value, dict) and "href" in value:
            payload += f'<vbox:{key} href="{value["href"]}"/>'
        else:
            payload += f"<vbox:{key}>{str(value) if value is not None else ''}</vbox:{key}>"
    payload += f"</vbox:{method_name}></soap:Body></soap:Envelope>"

    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": f'"{NS_VBOX}{method_name}"',
    }
    try:
        r = requests.post(base_url, data=payload.encode("utf-8"), headers=headers, timeout=timeout)
        r.raise_for_status()
        root = fromstring(r.text)
        # Ekstrak return atau fault
        for ns in ["", NS_SOAP]:
            body_el = root.find(f".//{{{NS_SOAP}}}Body") if NS_SOAP else root.find(".//Body")
            if body_el is None:
                body_el = root.find(".//Body")
            if body_el is not None:
                fault = body_el.find(f"{{{NS_SOAP}}}Fault")
                if fault is not None:
                    faultstring = fault.find("faultstring")
                    raise RuntimeError(faultstring.text if faultstring is not None else "SOAP Fault")
                # Cari elemen return / result (bisa di dalam response method)
                for child in body_el.iter():
                    if child.tag and ("return" in child.tag or "result" in child.tag):
                        return child
                return body_el[0] if len(body_el) else None
        return None
    except requests.RequestException as e:
        raise RuntimeError(f"Koneksi vboxwebsrv gagal: {e}") from e


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
        """Logon ke IWebsessionManager, dapatkan IVirtualBox ref."""
        result = _soap_call(
            self.base_url,
            "logon",
            params={"username": username, "password": password},
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
            result = _soap_call(self.base_url, "getMachines", ref=vbox_ref)
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
                name_el = _soap_call(self.base_url, "getName", ref=ref)
                state_el = _soap_call(self.base_url, "getState", ref=ref)
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
            session_result = _soap_call(self.base_url, "getSessionObject")
            session_ref = _extract_ref(session_result)
            if not session_ref:
                return False, "Tidak dapat mendapatkan session."

            # IMachine::lockMachine(session, lockType) — ref = machine
            _soap_call(
                self.base_url,
                "lockMachine",
                params={"session": {"href": session_ref}, "lockType": "Write"},
                ref=machine_id,
            )
            # launchVMProcess(session, type, environment)
            launch_result = _soap_call(
                self.base_url,
                "launchVMProcess",
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
            session_result = _soap_call(self.base_url, "getSessionObject")
            session_ref = _extract_ref(session_result)
            if not session_ref:
                return False, "Tidak dapat mendapatkan session."

            # lockMachine lalu getConsole -> powerDown -> unlockMachine
            _soap_call(
                self.base_url,
                "lockMachine",
                params={"session": {"href": session_ref}, "lockType": "Shared"},
                ref=machine_id,
            )
            console_result = _soap_call(self.base_url, "getConsole", ref=session_ref)
            console_ref = _extract_ref(console_result)
            if console_ref:
                _soap_call(self.base_url, "powerDown", ref=console_ref)
            _soap_call(self.base_url, "unlockMachine", ref=session_ref)
            return True, None
        except RuntimeError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
