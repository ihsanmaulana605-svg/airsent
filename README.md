# Smart Air Sentinel — Python Dashboard (v3)

Dashboard Streamlit real-time untuk ESP32 Smart Air Sentinel (sensor MQ2 + DHT22, MQTT broker publik HiveMQ).

## Yang baru di v3
- **Tombol tema di dalam aplikasi** (Terang / Sistem / Gelap, kanan atas). Tidak bergantung pada menu Settings Streamlit,
  jadi berfungsi juga saat diakses lewat tunnel (Colab/cloudflared).
- **Bar navigasi kustom**: merek, status udara/MQTT/ESP32 langsung (berdenyut saat online), pemilih tema, tombol Live,
  dan menu halaman dengan penanda halaman aktif. Responsif di ponsel.
- Banner status besar (berdenyut saat BAHAYA), kartu seragam, gauge, dan tampilan ADC mentah di kartu asap.

## Halaman
Ringkasan · Analisis · Riwayat · Sistem · Pengaturan · Bantuan (lihat isi di tiap halaman; Sistem memuat diagnosis otomatis).

## Struktur file
`app.py` (entry, navbar, notifikasi) · `halaman.py` · `ui.py` (CSS, tema, navbar, kartu) · `charts.py` · `analitik.py` ·
`data_manager.py` · `mqtt_client.py` · `config.py` · `.streamlit/config.toml`

## Instalasi (Windows)
```powershell
cd smart-air-sentinel
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```
Buka http://localhost:8501. Dites dengan Streamlit 1.66 (minimal 1.50).

## Konfigurasi MQTT
Bawaan: `broker.hivemq.com:1883`, topic `sentinel/liminal-ammar321/data` dan `.../status` (sama dengan kode ESP32 `smart_air_sentinel_mqtt.ino`).
Ganti tanpa edit kode (PowerShell):
```powershell
$env:SENTINEL_TOPIC_DATA = "sentinel/liminal-kodemu/data"
$env:SENTINEL_TOPIC_STATUS = "sentinel/liminal-kodemu/status"
streamlit run app.py
```
Variabel lain: `SENTINEL_MQTT_HOST`, `SENTINEL_MQTT_PORT`, `SENTINEL_BATAS_WASPADA`, `SENTINEL_BATAS_BAHAYA`,
`SENTINEL_FRESH_SECONDS`, `SENTINEL_DEVICE_STALE_SECONDS`. Topic dan ambang harus sama dengan kode ESP32.

## Format payload dari ESP32
```json
{"asap":45,"suhu":29.5,"lembab":72,"status":"WASPADA","relay":false,"adc":1843}
```
`suhu`/`lembab` boleh `null`. Field `adc` (opsional) menampilkan nilai ADC mentah untuk kalibrasi `ADC_PEKAT`.

## Pengujian singkat
1. Jalankan Wokwi sampai Serial Monitor menampilkan `MQTT: OK`, lalu `streamlit run app.py`.
2. Halaman **Sistem → Diagnosis** menampilkan OK untuk semua poin bila normal.
3. Geser slider gas melewati 40% dan 70%: banner, chip di bar atas, dan toast (pojok kanan bawah) berubah.
4. Hentikan simulasi: ESP32 OFFLINE, relay "TERAKHIR: …", muncul keterangan data bukan kondisi saat ini.
5. Coba tombol tema Terang/Gelap/Sistem di bar atas.

## Catatan
- Waktu = waktu pesan **diterima** (WIB), bukan waktu ukur sensor. Riwayat hanya di memori (maks. 1000 titik).
- Kadar asap = persentase hasil kalibrasi ADC sensor simulasi, bukan PM2.5/AQI/ppm.
- Tema Terang/Gelap dibuat dengan membalik warna seluruh aplikasi (filter CSS) bila pilihan berbeda dari tema dasar
  browser/Streamlit, sehingga warna hijau/kuning/merah mungkin sedikit bergeser dibanding mode Sistem.
- Hentikan (Ctrl+C) dan jalankan ulang aplikasi setelah mengedit kode agar tidak ada koneksi MQTT ganda.
- Di Colab: jalankan Streamlit di latar belakang lalu buka lewat tunnel (cloudflared); hentikan proses lama dengan
  `!pkill -f streamlit` bila masih berjalan, agar yang tampil adalah versi terbaru.
