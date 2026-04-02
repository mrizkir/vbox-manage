# VirtualBox Web Service (SOAP) — referensi singkat

Dokumen ini menjelaskan cara menyiapkan **vboxwebsrv** di komputer Anda dan contoh **body SOAP** yang dikirim dengan metode **POST** ke **alamat root** webservice, dengan header **`Content-Type: text/xml`**.

**Yang dianggap di contoh:** webservice mendengarkan di `http://127.0.0.1:18083/` (bisa diganti `localhost`) dan **otentikasi webservice dimatikan** (`websrvauthlibrary null`).

---

## Alur singkat (dibaca dulu)

1. Di komputer host, matikan auth webservice → jalankan `vboxwebsrv`.  
2. **Login SOAP** → simpan teks di `returnval` sebagai **`VB_TOKEN`**.  
3. **Daftar mesin** → tiap VM punya **`MACHINE_HANDLE`** (teks di `returnval`, bisa lebih dari satu elemen).  
4. **Detail / nyalakan / matikan** → ikuti urutan langkah di bawah; untuk mematikan VM perlu **sesi**, **kunci mesin**, **konsol**, lalu **buka kunci** sesi.

---

## Istilah (placeholder)

| Nama | Arti |
|------|------|
| **`VB_TOKEN`** | Teks dari `returnval` setelah `IWebsessionManager_logon`. Dipakai sebagai `_this` pada pemanggilan `IVirtualBox_*` dan sebagai isi `<refIVirtualBox>` pada `getSessionObject`. |
| **`MACHINE_HANDLE`** | Teks yang menunjuk ke satu VM, dari hasil `IVirtualBox_getMachines`. |
| **`SESSION_HANDLE`** | Teks dari `returnval` setelah `IWebsessionManager_getSessionObject`. |
| **`CONSOLE_HANDLE`** | Teks dari `returnval` setelah `ISession_getConsole` (untuk mematikan VM lewat konsol). |

**Format XML umum:** nama operasi dibungkus dengan prefix `vbox:` (misalnya `vbox:IMachine_getName`). Isi parameter biasanya elemen **tanpa** prefix `vbox:` (misalnya `<_this>`, `<username>`, `<session>`).

---

## Isi dokumen

**Persiapan di komputer host**

1. Matikan otentikasi webservice  
2. Verifikasi properti sistem  
3. Jalankan `vboxwebsrv`  

**SOAP (urutan penggunaan)**

4. Login (`IWebsessionManager_logon`)  
5. Daftar VM (`IVirtualBox_getMachines`)  
6. Detail sebuah VM  
7. Menjalankan VM  
8. Mematikan VM  

---

## Persiapan di komputer host

### 1. Matikan otentikasi webservice

Jalankan perintah berikut di terminal (di komputer tempat VirtualBox terpasang):

```bash
VBoxManage setproperty websrvauthlibrary null
```

### 2. Verifikasi properti sistem

```bash
VBoxManage list systemproperties
```

Pada keluaran perintah, cari baris **Webservice auth. library**. Jika nilainya **`null`**, otentikasi webservice sudah nonaktif.

### 3. Jalankan vboxwebsrv

```bash
vboxwebsrv --host 127.0.0.1 --port 18083
```

Biarkan proses ini tetap berjalan (misalnya di jendela terminal terpisah). Tanpa ini, klien (curl, Postman, aplikasi) tidak bisa terhubung.

---

## SOAP — contoh permintaan

Semua contoh di bawah mengirim **POST** ke URL root webservice, misalnya `http://127.0.0.1:18083/` atau `http://localhost:18083/`, dengan header **`Content-Type: text/xml`**.

### 4. Login — `IWebsessionManager_logon`

**Tujuan:** memastikan webservice bisa dihubungi dan mendapat **`VB_TOKEN`** untuk langkah berikutnya.

Jika otentikasi `null`, elemen `<username>` dan `<password>` boleh dikosongkan.

#### macOS / Linux (curl)

```bash
curl -X POST http://127.0.0.1:18083/ \
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

#### Windows (PowerShell)

```powershell
Invoke-WebRequest -Uri "http://127.0.0.1:18083/" `
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

#### Contoh respons sukses

Isi teks di dalam `<returnval>` inilah yang disimpan sebagai **`VB_TOKEN`** (contoh di bawah: `634f0d8fd6ef0e49-0000000000000001`).

```xml
<?xml version="1.0" encoding="UTF-8"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/"
  xmlns:SOAP-ENC="http://schemas.xmlsoap.org/soap/encoding/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns:xsd="http://www.w3.org/2001/XMLSchema"
  xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IWebsessionManager_logonResponse>
      <returnval>634f0d8fd6ef0e49-0000000000000001</returnval>
    </vbox:IWebsessionManager_logonResponse>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

---

### 5. Daftar VM — `IVirtualBox_getMachines`

**Tujuan:** mendapat daftar **`MACHINE_HANDLE`** untuk tiap mesin virtual.

Isi `<_this>` dengan **`VB_TOKEN`** yang Anda dapatkan di langkah 4. Cara mengirim permintaan sama seperti langkah 4 (POST + `text/xml`).

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

**Cara membaca respons:** dalam `IVirtualBox_getMachinesResponse`, cari elemen `<returnval>`.

- **Satu VM:** biasanya satu `<returnval>` berisi satu baris teks (handle).  
- **Lebih dari satu VM:** bisa berupa beberapa `<returnval>` yang berurutan (masing-masing satu handle).  
- Pada variasi lain, handle bisa muncul sebagai elemen anak dengan atribut `href`; intinya tiap VM punya satu nilai handle yang dipakai di langkah 6–8.

---

### 6. Detail sebuah VM

Di semua contoh berikut, ganti `MACHINE_HANDLE` dengan salah satu handle dari langkah 5.

#### Nama — `IMachine_getName`

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

#### Status — `IMachine_getState` (misalnya PoweredOn, PoweredOff)

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

#### Jumlah CPU — `IMachine_getCPUCount`

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

#### RAM (MB) — `IMachine_getMemorySize`

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

#### Tipe OS — `IMachine_getOSTypeId`

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

#### ID mesin — `IMachine_getId`

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

### 7. Menjalankan VM (menjadi PoweredOn)

#### 7.1 Ambil objek sesi — `IWebsessionManager_getSessionObject`

Isi `<refIVirtualBox>` dengan **`VB_TOKEN`** (sama seperti teks `returnval` dari login, langkah 4).

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

Dari respons, baca **`SESSION_HANDLE`** (biasanya teks di dalam `returnval`).

#### 7.2 Menjalankan proses VM — `IMachine_launchVMProcess`

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

| Placeholder | Asal nilai |
|-------------|------------|
| `MACHINE_HANDLE` | Salah satu hasil langkah 5 |
| `SESSION_HANDLE` | Respons langkah 7.1 |
| `type` | `headless` (tanpa jendela VM) atau `gui` (tampil jendela) |

---

### 8. Mematikan VM (PoweredOff)

**Urutan yang disarankan:** (1) dapatkan sesi → (2) kunci mesin dengan tipe **Shared** → (3) ambil konsol → (4) pilih **powerDown** atau **powerButton** → (5) **buka kunci** sesi.

#### Membandingkan `powerDown` dan `powerButton`

| Operasi | Arti singkat |
|---------|----------------|
| `IConsole_powerDown` | Menghentikan VM secara paksa (mirip listrik langsung putus). |
| `IConsole_powerButton` | Mengirim sinyal seperti tombol daya; **sistem operasi di dalam VM** bisa mematikan diri dengan rapi jika mengenali sinyal tersebut. |

#### 8.1 Ambil objek sesi — `IWebsessionManager_getSessionObject`

Sama seperti **langkah 7.1:** kirim `refIVirtualBox` = **`VB_TOKEN`**, lalu catat **`SESSION_HANDLE`** dari `returnval`.

#### 8.2 Kunci mesin — `IMachine_lockMachine`

Nilai **`Shared`** pada `lockType` dipakai agar sesi bisa mengakses konsol untuk mematikan VM.

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IMachine_lockMachine>
      <_this>MACHINE_HANDLE</_this>
      <session>SESSION_HANDLE</session>
      <lockType>Shared</lockType>
    </vbox:IMachine_lockMachine>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

#### 8.3 Ambil konsol — `ISession_getConsole`

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:ISession_getConsole>
      <_this>SESSION_HANDLE</_this>
    </vbox:ISession_getConsole>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

Dari respons, ambil **`CONSOLE_HANDLE`** (biasanya teks di `returnval`).

#### 8.4 Matikan VM — `IConsole_powerDown`

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IConsole_powerDown>
      <_this>CONSOLE_HANDLE</_this>
    </vbox:IConsole_powerDown>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

#### 8.5 (Opsional) Tombol daya — `IConsole_powerButton`

Gunakan bila ingin mematikan lewat sinyal tombol daya (lihat tabel perbandingan di atas), bukan cabut-listrik paksa.

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:IConsole_powerButton>
      <_this>CONSOLE_HANDLE</_this>
    </vbox:IConsole_powerButton>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

#### 8.6 Buka kunci sesi — `ISession_unlockMachine`

Setelah **`lockMachine`**, mesin masih “terkunci” oleh sesi tersebut. Panggilan ini **melepaskan kunci** sehingga tidak mengganggu tindakan lain (misalnya membuka VM di VirtualBox Manager atau menjalankan langkah start/stop berikutnya). Lakukan setelah operasi konsol selesai (setelah **powerDown** atau setelah Anda tidak lagi membutuhkan kunci itu).

```xml
<?xml version="1.0"?>
<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/" xmlns:vbox="http://www.virtualbox.org/">
  <SOAP-ENV:Body>
    <vbox:ISession_unlockMachine>
      <_this>SESSION_HANDLE</_this>
    </vbox:ISession_unlockMachine>
  </SOAP-ENV:Body>
</SOAP-ENV:Envelope>
```

#### Ringkasan placeholder untuk langkah 8

| Placeholder | Asal nilai |
|-------------|------------|
| `CONSOLE_HANDLE` | Respons langkah 8.3 (`ISession_getConsole`) |
| `SESSION_HANDLE` | Respons langkah 8.1; dipakai lagi di langkah 8.6 (`unlockMachine`) |
