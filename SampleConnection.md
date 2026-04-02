# Contoh koneksi VirtualBox Web Service (SOAP)

Langkah-langkah di bawah ini mengasumsikan `vboxwebsrv` berjalan di `127.0.0.1:18083` dan otentikasi webservice dimatikan.

---

## 1. Matikan otentikasi webservice

```bash
VBoxManage setproperty websrvauthlibrary null
```

## 2. Verifikasi properti sistem

```bash
VBoxManage list systemproperties
```

Cari baris **Webservice auth. library**. Jika bernilai `null`, otentikasi webservice sudah dimatikan.

## 3. Jalankan vboxwebsrv

```bash
vboxwebsrv --host 127.0.0.1 --port 18083
```

Biarkan proses ini berjalan di terminal terpisah.

## 4. Uji koneksi (logon)

Kirim permintaan SOAP `IWebsessionManager_logon` ke root URL webservice. Respons yang berisi `returnval` berarti koneksi berhasil; nilai itu dipakai sebagai **token sesi VirtualBox** untuk langkah berikutnya.

### macOS / Linux

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

### Windows (PowerShell)

```powershell
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

### Contoh respons sukses

```xml
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

Isi elemen `returnval` (contoh: `634f0d8fd6ef0e49-0000000000000001`) adalah token yang dipakai sebagai `_this` pada `IVirtualBox_*` dan sebagai `refIVirtualBox` pada `getSessionObject`. Di dokumen ini token itu disebut **`VB_TOKEN`**.

---

## 5. Daftar VM (`IVirtualBox_getMachines`)

Ganti `VB_TOKEN` dengan nilai `returnval` dari logon. Body XML dikirim dengan cara yang sama seperti langkah 4 (`POST`, `Content-Type: text/xml`).

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IVirtualBox_getMachines>
      <_this>VB_TOKEN</_this>
    </vbox:IVirtualBox_getMachines>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

---

## 6. Detail sebuah VM

Ganti `MACHINE_HANDLE` dengan ID mesin dari hasil `getMachines` (contoh di bawah memakai placeholder `70e7c3891a68e934-0000000000000002`).

### Nama VM

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IMachine_getName>
      <_this>MACHINE_HANDLE</_this>
    </vbox:IMachine_getName>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

### Status (PoweredOn, PoweredOff, …)

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IMachine_getState>
      <_this>MACHINE_HANDLE</_this>
    </vbox:IMachine_getState>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

### Jumlah CPU

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IMachine_getCPUCount>
      <_this>MACHINE_HANDLE</_this>
    </vbox:IMachine_getCPUCount>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

### Ukuran RAM (MB)

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IMachine_getMemorySize>
      <_this>MACHINE_HANDLE</_this>
    </vbox:IMachine_getMemorySize>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

### Tipe OS

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IMachine_getOSTypeId>
      <_this>MACHINE_HANDLE</_this>
    </vbox:IMachine_getOSTypeId>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

### ID VM

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IMachine_getId>
      <_this>MACHINE_HANDLE</_this>
    </vbox:IMachine_getId>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

---

## 7. Menjalankan VM (PoweredOn)

### 7.1 Ambil objek sesi (`IWebsessionManager_getSessionObject`)

Isi `refIVirtualBox` dengan **`VB_TOKEN`** (sama dengan `returnval` dari `IWebsessionManager_logon`).

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IWebsessionManager_getSessionObject>
      <refIVirtualBox>VB_TOKEN</refIVirtualBox>
    </vbox:IWebsessionManager_getSessionObject>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

Dari respons, ambil handle sesi sebagai **`SESSION_HANDLE`**.

### 7.2 Launch (`IMachine_launchVMProcess`)

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IMachine_launchVMProcess>
      <_this>MACHINE_HANDLE</_this>
      <session>SESSION_HANDLE</session>
      <type>headless</type>
    </vbox:IMachine_launchVMProcess>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

| Placeholder        | Sumber |
|--------------------|--------|
| `MACHINE_HANDLE`   | Salah satu mesin dari `IVirtualBox_getMachines` |
| `SESSION_HANDLE`   | Respons `IWebsessionManager_getSessionObject` |
| `type`             | `headless` (tanpa GUI, cocok untuk server) atau `gui` (jendela VM) |
