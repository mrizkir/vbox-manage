from flask import Flask, jsonify
import requests

app = Flask(__name__)

# Konfigurasi VirtualBox Web Server
VBOX_WEB_SERVER_URL = "http://127.0.0.1:18083"
VBOX_USER = ""  # Ganti dengan user OS Anda
VBOX_PW = ""    # Ganti dengan password OS Anda

@app.route("/")
def hello_world():
    return "<h3>VirtualBox API Gateway</h3><p>Status: Online</p>"

@app.route("/connect")
def connect():
    # Body SOAP untuk login (vboxwebsrv menggunakan SOAP API)
    soap_body = f"""
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
       <soapenv:Header/>
       <soapenv:Body>
          <vbox:IWebsessionManager_logon>
             <user>{VBOX_USER}</user>
             <password>{VBOX_PW}</password>
          </vbox:IWebsessionManager_logon>
       </soapenv:Body>
    </soapenv:Envelope>
    """
    
    headers = {
        "Content-Type": "text/xml; charset=utf-8",
        "SOAPAction": '"#logon"' # Beberapa versi butuh SOAPAction
    }

    try:
        response = requests.post(VBOX_WEB_SERVER_URL, data=soap_body, headers=headers, timeout=5)
        
        if response.status_code == 200:
            # Jika berhasil, VirtualBox akan mengembalikan Session ID dalam XML
            return jsonify({
                "status": "success",
                "message": "Koneksi ke VBoxWebServer berhasil!",
                "raw_response": response.text[:200] # Menampilkan potongan XML response
            })
        else:
            return jsonify({
                "status": "error",
                "message": f"Server merespon dengan kode {response.status_code}"
            }), response.status_code

    except requests.exceptions.ConnectionError:
        return jsonify({
            "status": "fail",
            "message": "Gagal terhubung. Pastikan 'vboxwebsrv' sudah berjalan."
        }), 500

if __name__ == "__main__":
    app.run(debug=True)