### 1. Matikan otentikasi
```bash
VBoxManage setproperty websrvauthlibrary null
```

### 2. Cek apakah sudah dimatikan otentikasi-nya
```
VBoxManage list systemproperties
```
Kemudian cari bagian Webservice auth. library

Bila bernilai null, maka proses otentikasi di dalam vboxmanage berhasil dimatikan.

### 3. Jalankan vboxsrv
```bash
vboxwebsrv --host 127.0.0.1 --port 18083
```
### 4. Uji coba koneksi
MAcos/Linux
```bash
curl -X POST http://localhost:18083/ \
  -H "Content-Type: text/xml" \
  -d '<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IWebsessionManager_logon>
      <username></username>
      <password></password>
    </vbox:IWebsessionManager_logon>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>'
```

Windows 10/11, di PowerShelll

```bash
Invoke-WebRequest -Uri "http://localhost:18083/" `
  -Method POST `
  -ContentType "text/xml" `
  -Body '<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IWebsessionManager_logon>
      <username></username>
      <password></password>
    </vbox:IWebsessionManager_logon>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>'
```

outputnya:

```
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:vbox="http://www.virtualbox.org/">
    <SOAP-ENV:Body>
        <vbox:IWebsessionManager_logonResponse>
            <returnval>
                634f0d8fd6ef0e49-0000000000000001
            </returnval>
        </vbox:IWebsessionManager_logonResponse>
    </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

Lihat bagian, returnval, terdapat nilai

634f0d8fd6ef0e49-0000000000000001

berarti koneksi berhasil.

Selanjutya koneksi, ke vbox api menggunakan: 634f0d8fd6ef0e49-0000000000000001

### 5. Mendapatkan daftar vms
```bash
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IVirtualBox_getMachines>
      <_this>634f0d8fd6ef0e49-0000000000000001</_this>
    </vbox:IVirtualBox_getMachines>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>'
```