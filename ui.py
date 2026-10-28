from __future__ import annotations

import html

import pandas as pd
import streamlit as st

import config
from data_manager import STATUS_VALID, DataStore, format_wib, teks_usia
from mqtt_client import get_service

WARNA_STATUS = {"AMAN": "#16a34a", "WASPADA": "#d97706", "BAHAYA": "#dc2626"}
WARNA_TONE = {"ok": "#16a34a", "warn": "#d97706", "bad": "#dc2626", "idle": "#64748b", "info": "#0891b2"}
RENTANG = {"5 menit": 5, "15 menit": 15, "1 jam": 60, "Semua": None}
TEMA_OPSI = [":material/light_mode: Terang", ":material/computer: Sistem", ":material/dark_mode: Gelap"]

PREF_BAWAAN = {
    "live": True, "pref_tema": ":material/computer: Sistem", "pref_refresh": 1, "pref_titik": 300, "pref_ma": 1,
    "pref_notif": True, "pref_ambang": True,
    "f_status": list(STATUS_VALID), "f_rentang": "Semua", "f_baris": 100, "f_invalid": False,
    "a_rentang": "15 menit",
}

CSS = """
<style>
header[data-testid="stHeader"] {background: transparent !important; pointer-events: none;}
header[data-testid="stHeader"] [data-testid="stToolbar"], header[data-testid="stHeader"] [data-testid="stStatusWidget"] {pointer-events: auto;}
[data-testid="stAppDeployButton"] {display: none !important;}
.block-container {padding-top: 1rem !important; padding-bottom: 3rem; max-width: 1320px;}
[data-testid="stToastContainer"] {top: auto !important; bottom: 1.2rem !important; right: 1.2rem !important;}
@keyframes pulse {0% {box-shadow: 0 0 0 0 var(--pc, rgba(220,38,38,.55));} 70% {box-shadow: 0 0 0 12px rgba(0,0,0,0);}
                  100% {box-shadow: 0 0 0 0 rgba(0,0,0,0);}}

.st-key-navbar {position: sticky; top: .5rem; z-index: 100; margin: 0 0 1.1rem 0; padding: 12px 18px 10px 18px;
  border-radius: 20px; border: 1px solid rgba(128,128,128,.30);
  background: linear-gradient(135deg, rgba(8,145,178,.16), rgba(37,99,235,.10) 55%, rgba(128,128,128,.10));
  backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px); box-shadow: 0 10px 34px rgba(0,0,0,.16);
  padding-right: 18px;}
.brand {display: flex; align-items: center; gap: 12px;}
.brand-logo {width: 42px; height: 42px; border-radius: 13px; display: grid; place-items: center; font-size: 1.35rem;
  background: linear-gradient(135deg, #06b6d4, #2563eb); box-shadow: 0 6px 18px rgba(8,145,178,.45);}
.brand-t {font-weight: 800; letter-spacing: .07em; font-size: 1.05rem; line-height: 1.1;
  background: linear-gradient(90deg, #06b6d4, #3b82f6); -webkit-background-clip: text; background-clip: text; color: transparent;}
.brand-s {opacity: .65; font-size: .72rem; letter-spacing: .04em;}
.chips {display: flex; gap: 8px; flex-wrap: wrap; align-items: center; justify-content: center;}
.chip {display: inline-flex; align-items: center; gap: 7px; padding: 5px 12px; border-radius: 999px; font-size: .78rem;
  font-weight: 700; background: rgba(128,128,128,.13); border: 1px solid rgba(128,128,128,.28); white-space: nowrap;}
.dot {width: 9px; height: 9px; border-radius: 50%; display: inline-block; --pc: rgba(22,163,74,.5);}
.dot.pulse {animation: pulse 1.8s infinite;}
.st-key-navlinks {margin-top: 4px; padding-top: 10px; border-top: 1px solid rgba(128,128,128,.22);}
.st-key-navlinks a {border-radius: 12px !important; padding: 7px 16px !important; font-weight: 600 !important;
  transition: transform .15s ease, background .15s ease, box-shadow .15s ease;}
.st-key-navlinks a:hover {background: rgba(8,145,178,.16) !important; transform: translateY(-1px);}

.st-key-pref_tema button[role="radio"] {border-radius: 10px !important; font-weight: 600; transition: background .15s ease;
  background: rgba(128,128,128,.14) !important; border-color: rgba(128,128,128,.25) !important;}
.st-key-pref_tema button[aria-checked="true"] {background: linear-gradient(135deg, #0891b2, #2563eb) !important;
  box-shadow: 0 4px 14px rgba(37,99,235,.40); border-color: transparent !important;}
.st-key-pref_tema button[aria-checked="true"], .st-key-pref_tema button[aria-checked="true"] * {color: #ffffff !important;}

.judul {font-size: 2.1rem !important; font-weight: 800; letter-spacing: .02em; margin: .2rem 0 0 0; line-height: 1.25;
  background: linear-gradient(90deg, #06b6d4, #3b82f6 60%, #8b5cf6); -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent; color: transparent;}
.sub {opacity: .7; margin: .15rem 0 .9rem 0;}

.grid {display: grid; gap: 14px; align-items: stretch;}
.grid4 {grid-template-columns: repeat(4, minmax(0, 1fr));}
.grid3 {grid-template-columns: repeat(3, minmax(0, 1fr));}
.grid2 {grid-template-columns: repeat(2, minmax(0, 1fr));}
@media (max-width: 1000px) {.grid4 {grid-template-columns: repeat(2, minmax(0, 1fr));}}
@media (max-width: 640px) {.grid4, .grid3, .grid2 {grid-template-columns: 1fr;} .brand-s {display: none;}}
.kartu {background: rgba(128,128,128,.10); border: 1px solid rgba(128,128,128,.26); border-top: 3px solid var(--ak, rgba(128,128,128,.4));
  border-radius: 16px; padding: 16px 18px; transition: transform .15s ease, box-shadow .15s ease;}
.kartu:hover {transform: translateY(-2px); box-shadow: 0 10px 26px rgba(0,0,0,.14);}
.k-judul {opacity: .7; font-size: .78rem; text-transform: uppercase; letter-spacing: .07em;}
.k-nilai {font-size: 2.1rem; font-weight: 800; line-height: 1.15; margin: 4px 0;}
.k-sub {opacity: .7; font-size: .84rem;}
.bar {background: rgba(128,128,128,.25); border-radius: 8px; height: 10px; margin: 8px 0 4px 0; overflow: hidden;}
.bar > div {height: 100%; border-radius: 8px;}
.badge {display: inline-block; padding: 3px 12px; border-radius: 999px; font-weight: 700; font-size: .78rem; border: 1px solid;}
.ind {background: rgba(128,128,128,.10); border: 1px solid rgba(128,128,128,.26); border-radius: 14px; padding: 13px 15px;}
.ind-l {opacity: .7; font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; margin-bottom: 7px;}
.hero {border-radius: 20px; padding: 20px 26px; border: 1px solid; margin-bottom: 14px; --pc: rgba(220,38,38,.5);}
.hero.alarm {animation: pulse 1.6s infinite;}
.hdot {display: inline-block; width: .8em; height: .8em; border-radius: 50%; margin-right: .45em; vertical-align: -.02em;}
.hero-t {font-size: 2rem; font-weight: 800; letter-spacing: .03em; line-height: 1.2;}
.hero-s {opacity: .85; margin-top: 3px;}
.footer {opacity: .55; text-align: center; font-size: .8rem; margin-top: 2rem;}
</style>
"""


def _tema_dasar() -> str | None:
    """Tema yang sedang dipakai Streamlit (light/dark), atau None bila belum diketahui."""
    try:
        t = st.context.theme.type
        return t if t in ("light", "dark") else None
    except Exception:  # noqa: BLE001
        return None


def css_tema() -> str:
    """Tema Terang/Gelap/Sistem milik aplikasi, tidak bergantung pada menu Settings Streamlit.

    Bila pilihan berbeda dari tema dasar Streamlit, seluruh aplikasi (termasuk grafik, tabel, dan popup)
    dibalik dengan filter invert + hue-rotate (popup/tooltip/toast yang berada di luar .stApp ikut difilter). Latar dasar dipilih agar hasilnya tidak hitam/putih murni.
    """
    pilihan = st.session_state.get("pref_tema", PREF_BAWAAN["pref_tema"])
    target = {TEMA_OPSI[0]: "light", TEMA_OPSI[2]: "dark"}.get(pilihan)
    dasar = _tema_dasar()
    if target is None or dasar is None or target == dasar:
        return ""
    filt = "invert(1) hue-rotate(180deg)"
    if dasar == "light":   # -> gelap: #e7eefc dibalik+diputar warna menjadi navy #0b1220
        latar_app, latar_body = "#e7eefc", "#0b1220"
    else:                  # -> terang: #080a0e menjadi #f3f5f9
        latar_app, latar_body = "#080a0e", "#f3f5f9"
    return (f"<style>html, body {{background: {latar_body} !important;}}"
            f".stApp {{filter: {filt}; background: {latar_app} !important;}}"
            f"div[role='tooltip'], [data-testid='stSelectboxVirtualDropdown'], [data-testid='stToast'] {{filter: {filt};}}</style>")


@st.cache_resource(show_spinner=False)
def get_store() -> DataStore:
    store, _ = get_service()  # satu koneksi MQTT untuk seluruh sesi/rerun
    return store


def init_state() -> None:
    """Isi default dan jaga agar nilai widget tidak hilang saat pindah halaman."""
    for k, v in PREF_BAWAAN.items():
        st.session_state.setdefault(k, v)
        st.session_state[k] = st.session_state[k]


def reset_pref() -> None:
    for k, v in PREF_BAWAAN.items():
        st.session_state[k] = v


def live(func) -> None:
    """Jalankan `func` sebagai fragment yang menyegarkan diri (atau statis saat dijeda)."""
    aktif = st.session_state.get("live", True)
    interval = float(st.session_state.get("pref_refresh", config.REFRESH_SECONDS))
    st.fragment(run_every=interval if aktif else None)(func)()


def esc(x) -> str:
    return html.escape(str(x))


def angka(x, desimal=1, satuan="") -> str:
    if x is None or pd.isna(x):
        return "Tidak tersedia"
    return f"{x:.{desimal}f}".replace(".", ",") + satuan


def badge(teks: str, tone: str) -> str:
    w = WARNA_TONE[tone]
    return f'<span class="badge" style="color:{w};border-color:{w};background:{w}22">{esc(teks)}</span>'


def kartu(judul, nilai, sub="", warna="inherit", bar=None, aksen=None) -> str:
    b = ""
    if bar is not None:
        b = f'<div class="bar"><div style="width:{max(0, min(100, bar))}%;background:{warna}"></div></div>'
    ak = aksen or (warna if warna != "inherit" else "rgba(128,128,128,.4)")
    return (f'<div class="kartu" style="--ak:{ak}"><div class="k-judul">{esc(judul)}</div>'
            f'<div class="k-nilai" style="color:{warna}">{esc(nilai)}</div>{b}<div class="k-sub">{sub}</div></div>')


def indikator(label, teks, tone, catatan="") -> str:
    return (f'<div class="ind"><div class="ind-l">{esc(label)}</div>{badge(teks, tone)}'
            f'<div class="k-sub" style="margin-top:6px">{catatan}</div></div>')


def grid(items: list[str], kolom: int = 4) -> None:
    """Tampilkan kartu dalam grid CSS (tinggi sama, otomatis 2 kolom di layar sedang, 1 di ponsel)."""
    st.markdown(f'<div class="grid grid{kolom}">{"".join(items)}</div>', unsafe_allow_html=True)


def judul_halaman(judul: str, sub: str) -> None:
    st.markdown(f'<div class="judul">{esc(judul)}</div><div class="sub">{esc(sub)}</div>', unsafe_allow_html=True)


def data_basi(s: dict) -> bool:
    """True bila nilai terakhir tidak bisa dianggap kondisi saat ini."""
    return (s["kesegaran"] != "DATA TERKINI") or s["device_status"] == "offline" or not s["mqtt_connected"]


def status_esp(s: dict) -> tuple[str, str, str]:
    """(teks, tone, catatan) status perangkat ESP32 — terpisah dari status broker."""
    ds, dt = s["device_status"], s["device_status_time"]
    cat = f"Status diterima: {esc(format_wib(dt))}" if dt else "Belum ada pesan status"
    if not s["mqtt_connected"]:
        return "TIDAK DIKETAHUI", "idle", "Dashboard tidak terhubung ke broker"
    if ds is None:
        return "BELUM ADA STATUS", "idle", cat
    if ds == "offline":
        return "OFFLINE", "bad", cat
    if s["usia"] is None or s["usia"] > config.DEVICE_STALE_SECONDS:
        return "ONLINE (DATA TIDAK MASUK)", "warn", cat + "<br>Status retained bisa kedaluwarsa atau dari perangkat lain."
    return "ONLINE", "ok", cat


def _chip(teks: str, tone: str, pulse: bool = False) -> str:
    w = WARNA_TONE[tone]
    return (f'<span class="chip"><i class="dot{" pulse" if pulse else ""}" style="background:{w};--pc:{w}88"></i>'
            f'{esc(teks)}</span>')


def render_navbar(halaman: list, store: DataStore, aktif: int = 0) -> None:
    """Bar navigasi atas: merek, status ringkas langsung, pemilih tema, tombol live, dan menu halaman."""
    with st.container(key="navbar"):
        c1, c2, c3, c4 = st.columns([3.1, 4.2, 3.3, 1.1], vertical_alignment="center", gap="small")
        c1.markdown('<div class="brand"><div class="brand-logo">🛰️</div><div>'
                    '<div class="brand-t">SMART AIR SENTINEL</div>'
                    '<div class="brand-s">Real-Time Air Quality Monitoring</div></div></div>', unsafe_allow_html=True)

        def _chips() -> None:
            s = store.snapshot()
            r = s["last_record"]
            teks_esp, tone_esp, _ = status_esp(s)
            chips = []
            if r is not None:
                tone = {"AMAN": "ok", "WASPADA": "warn", "BAHAYA": "bad"}[r["status"]]
                chips.append(_chip(f"{r['status']} · {r['asap']:g}%", tone, pulse=r["status"] == "BAHAYA"))
            else:
                chips.append(_chip("MENUNGGU DATA", "idle"))
            chips.append(_chip("MQTT", "ok" if s["mqtt_connected"] else "bad", pulse=s["mqtt_connected"]))
            chips.append(_chip("ESP32 " + teks_esp.split(" ")[0], tone_esp, pulse=tone_esp == "ok"))
            st.markdown(f'<div class="chips">{"".join(chips)}</div>', unsafe_allow_html=True)

        with c2:
            live(_chips)
        with c3:
            st.segmented_control("Tema", TEMA_OPSI, key="pref_tema", required=True, label_visibility="collapsed")
        with c4:
            st.toggle("Live", key="live", help="Matikan untuk menjeda semua tampilan.")
        st.markdown(f'<style>.st-key-navlinks > div:nth-child({aktif + 1}) a {{background: linear-gradient(135deg,#0891b2,#2563eb) '
                    '!important; box-shadow: 0 6px 18px rgba(37,99,235,.40);}'
                    f'.st-key-navlinks > div:nth-child({aktif + 1}) a, .st-key-navlinks > div:nth-child({aktif + 1}) a * '
                    '{color: #ffffff !important;}</style>', unsafe_allow_html=True)
        with st.container(key="navlinks", horizontal=True, gap="small"):
            for p in halaman:
                st.page_link(p)


def render_waktu(s: dict) -> None:
    mqtt_b = badge("MQTT TERHUBUNG", "ok") if s["mqtt_connected"] else badge("MQTT TERPUTUS", "bad")
    kes = {"DATA TERKINI": "ok", "DATA TERLAMBAT": "warn", "TIDAK ADA DATA": "idle"}[s["kesegaran"]]
    jeda = badge("DIJEDA", "warn") if not st.session_state.get("live", True) else ""
    if s["last_data_time"] is None:
        info = "<b>Terakhir diperbarui:</b> belum ada data sensor yang diterima"
    else:
        info = (f"<b>Terakhir diperbarui:</b> {esc(format_wib(s['last_data_time']))} "
                f"<span style='opacity:.7'>· data diterima {esc(teks_usia(s['usia']))}</span>")
    st.markdown(f"{mqtt_b} &nbsp;{badge(s['kesegaran'], kes)} &nbsp;{jeda}<div style='margin:8px 0 2px 0'>{info}</div>",
                unsafe_allow_html=True)
    if not s["mqtt_connected"] and s["mqtt_error"]:
        st.error(f"Tidak terhubung ke broker: {s['mqtt_error']}. Mencoba menyambung ulang otomatis…")


def render_hero(s: dict) -> None:
    r = s["last_record"]
    alarm = False
    if r is None:
        w, judul, sub = WARNA_TONE["idle"], "MENUNGGU DATA", "Belum ada data sensor dari ESP32."
    else:
        w = WARNA_STATUS[r["status"]]
        judul = {"AMAN": "UDARA AMAN", "WASPADA": "WASPADA", "BAHAYA": "BAHAYA — ASAP PEKAT"}[r["status"]]
        sub = {"AMAN": "Kadar asap rendah, tidak ada tindakan diperlukan.",
               "WASPADA": "Kadar asap meningkat. Periksa sumber asap dan siapkan ventilasi.",
               "BAHAYA": "Kadar asap tinggi. Periksa ruangan segera dan pastikan ventilasi/purifier aktif."}[r["status"]]
        if data_basi(s):
            sub = "(Data terakhir, bukan kondisi saat ini) " + sub
        else:
            alarm = r["status"] == "BAHAYA"
    st.markdown(f'<div class="hero{" alarm" if alarm else ""}" style="background:linear-gradient(135deg,{w}33,{w}0d);'
                f'border-color:{w}88"><div class="hero-t" style="color:{w}"><span class="hdot" style="background:{w}"></span>{esc(judul)}</div>'
                f'<div class="hero-s">{esc(sub)}</div></div>', unsafe_allow_html=True)


def render_metrik(s: dict) -> None:
    r = s["last_record"]
    if r is None:
        grid([kartu("Kadar Asap", "Tidak tersedia", "Menunggu data dari ESP32"),
              kartu("Suhu", "Tidak tersedia"), kartu("Kelembapan", "Tidak tersedia"),
              kartu("Status Udara", "Menunggu data")])
        return
    kategori = {"AMAN": f"AMAN (< {config.BATAS_WASPADA:g}%)",
                "WASPADA": f"WASPADA ({config.BATAS_WASPADA:g}–{config.BATAS_BAHAYA:g}%)",
                "BAHAYA": f"BAHAYA (> {config.BATAS_BAHAYA:g}%)"}[r["status_hitung"]]
    adc = f" · ADC {r['adc']}" if r.get("adc") is not None else ""
    grid([
        kartu("Kadar Asap", f"{r['asap']:g}%", f"Kategori: {kategori}{adc}", WARNA_STATUS[r["status_hitung"]], bar=r["asap"]),
        kartu("Suhu", angka(r["suhu"], 1, " °C"), "" if r["suhu"] is not None else "Pembacaan DHT22 gagal / tidak valid",
              aksen="#ea580c"),
        kartu("Kelembapan", angka(r["lembab"], 0, "% RH"), "" if r["lembab"] is not None else "Pembacaan DHT22 gagal / tidak valid",
              aksen="#2563eb"),
        kartu("Status Udara", r["status"], "Status dari ESP32", WARNA_STATUS[r["status"]]),
    ])
    if r["status"] != r["status_hitung"]:
        st.warning(f"Ketidaksesuaian status: ESP32 mengirim **{r['status']}**, tetapi perhitungan dari "
                   f"kadar asap {r['asap']:g}% menghasilkan **{r['status_hitung']}**. "
                   "Dashboard tetap menampilkan status asli dari ESP32.")


def render_indikator(s: dict, kolom: int = 4) -> None:
    r = s["last_record"]
    t, tone, cat = status_esp(s)
    item = [
        indikator("Koneksi broker MQTT", "TERHUBUNG" if s["mqtt_connected"] else "TERPUTUS",
                  "ok" if s["mqtt_connected"] else "bad", esc(config.MQTT_HOST)),
        indikator("Perangkat ESP32", t, tone, cat),
    ]
    if r is None or r["relay"] is None:
        item.append(indikator("Relay (purifier/kipas)", "TIDAK DIKETAHUI" if r else "-", "idle"))
    elif data_basi(s):
        item.append(indikator("Relay (purifier/kipas)", f"TERAKHIR: {'AKTIF' if r['relay'] else 'NONAKTIF'}", "idle",
                              "Kondisi sekarang tidak diketahui (data tidak terkini)"))
    elif r["relay"]:
        item.append(indikator("Relay (purifier/kipas)", "AKTIF", "info", "Purifier/kipas menyala"))
    else:
        item.append(indikator("Relay (purifier/kipas)", "NONAKTIF", "ok"))
    if r is None:
        item.append(indikator("Kondisi sensor", "BELUM ADA DATA", "idle"))
    else:
        buruk = [n for n, k in (("suhu", "suhu"), ("kelembapan", "lembab")) if r[k] is None]
        item.append(indikator("Kondisi sensor", "SEBAGIAN TIDAK VALID" if buruk else "VALID",
                              "warn" if buruk else "ok", ("Tidak valid: " + ", ".join(buruk)) if buruk else ""))
    grid(item, kolom)
    if s["invalid_count"]:
        st.caption(f"{s['invalid_count']} pesan data ditolak karena format tidak valid (lihat log teknis).")
