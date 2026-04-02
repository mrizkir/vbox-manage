"""
Model: Layer akses ke VirtualBox via SOAP (vboxwebsrv).
Format permintaan mengikuti SampleConnection.md (POST root URL, elemen param tanpa prefix vbox:).
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
    Kirim SOAP ke root URL vboxwebsrv (sama seperti contoh curl di SampleConnection.md).
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
        Daftar semua VM: list of dict {id, name, state}.
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
                name = _extract_text(name_el) if name_el is not None else "?"
                state = _extract_text(state_el) if state_el is not None else "Unknown"
                machines.append({"id": ref, "name": name or ref, "state": state})

            return machines, None
        except RuntimeError as e:
            return [], str(e)
        except Exception as e:
            return [], str(e)

    def start_vm(self, machine_id):
        """Jalankan VM (headless), alur seperti SampleConnection.md §7."""
        try:
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
                params={"_this": machine_id, "session": session_ref, "type": "headless"},
            )
            return True, None
        except RuntimeError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)

    def stop_vm(self, machine_id):
        """Matikan VM (powerDown). Parameter SOAP sama pola dengan contoh (_this + isi teks)."""
        try:
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
                "IMachine_lockMachine",
                params={"_this": machine_id, "session": session_ref, "lockType": "Shared"},
            )
            console_result = _soap_call(
                self.base_url,
                "ISession_getConsole",
                params={"_this": session_ref},
            )
            console_ref = _extract_ref(console_result)
            if console_ref:
                _soap_call(
                    self.base_url,
                    "IConsole_powerDown",
                    params={"_this": console_ref},
                )
            _soap_call(
                self.base_url,
                "ISession_unlockMachine",
                params={"_this": session_ref},
            )
            return True, None
        except RuntimeError as e:
            return False, str(e)
        except Exception as e:
            return False, str(e)
