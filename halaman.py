"""Halaman-halaman dashboard (dipakai oleh st.navigation di app.py)."""
from __future__ import annotations

import pandas as pd
import streamlit as st

import analitik
import charts
import config
from data_manager import (STATUS_VALID, filter_df, format_wib, ke_csv, now_wib,
                          teks_durasi, teks_usia, to_dataframe)
from ui import (RENTANG, WARNA_STATUS, angka, esc, get_store, grid, judul_halaman,
                kartu, live, render_hero, render_indikator, render_metrik, render_waktu, reset_pref)

CFG = {"displaylogo": False}


def _data(s: dict, menit=None) -> pd.DataFrame:
    """DataFrame riwayat, dibatasi rentang waktu dan jumlah titik pilihan pengguna."""
    df = to_dataframe(s["history"])
    df = filter_df(df, [], menit)
    return df.tail(int(st.session_state.get("pref_titik", 300)))


def _tabel_riwayat(f: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "Waktu (WIB)": f["waktu"].dt.tz_convert(config.WIB).dt.strftime("%d-%m-%Y %H:%M:%S"),
        "Asap (%)": f["asap"].map(lambda v: f"{v:g}"),
        "Suhu (°C)": f["suhu"].map(lambda v: "Tidak valid" if pd.isna(v) else f"{v:.1f}"),
        "Kelembapan (% RH)": f["lembab"].map(lambda v: "Tidak valid" if pd.isna(v) else f"{v:.0f}"),
        "Status": f["status"],
        "Relay": f["relay"].map({True: "AKTIF", False: "NONAKTIF"}).fillna("Tidak diketahui"),
    })


# =============================================================== 1. RINGKASAN
def ringkasan() -> None:
    store = get_store()
    judul_halaman("Ringkasan", "Kondisi udara terkini dari ESP32 — Real-Time Air Quality Monitoring System")

    def _isi() -> None:
        s = store.snapshot()
        df_all = to_dataframe(s["history"])
        render_waktu(s)
        render_hero(s)
        render_metrik(s)
        st.write("")
        kiri, kanan = st.columns([1, 2])
        r = s["last_record"]
        kiri.plotly_chart(charts.gauge_asap(r["asap"] if r else None), key="r_gauge", config=CFG, theme=None)
        with kanan:
            render_indikator(s, 2)

        st.subheader("Tren 5 menit terakhir")
        d5 = filter_df(df_all, [], 5)
        st.plotly_chart(charts.grafik_asap(d5, 1, st.session_state.get("pref_ambang", True), 280),
                        key="r_tren", config=CFG, theme=None)

        d15 = filter_df(df_all, [], 15)
        st1 = analitik.statistik(d15, "asap")
        grid([kartu("Puncak asap (15 menit)", f"{st1['maks']:g}%" if st1 else "Tidak tersedia", aksen="#dc2626"),
              kartu("Rata-rata asap (15 menit)", angka(st1["rata"], 1, "%") if st1 else "Tidak tersedia", aksen="#0891b2"),
              kartu("Pesan data diterima", f"{s['total_data']}", "sejak dashboard berjalan", aksen="#8b5cf6")], 3)

        st.subheader("Perubahan status terbaru")
        log = s["status_log"][::-1][:5]
        if not log:
            st.caption("Belum ada perubahan status sejak dashboard berjalan.")
        for x in log:
            w = WARNA_STATUS[x["ke"]]
            st.markdown(f"<span style='color:{w};font-weight:700'>●</span> **{x['dari']} → {x['ke']}** "
                        f"(asap {x['asap']:g}%) · {format_wib(x['waktu'])}", unsafe_allow_html=True)

    live(_isi)


# =============================================================== 2. ANALISIS
def analisis() -> None:
    store = get_store()
    judul_halaman("Analisis", "Grafik interaktif, statistik, dan distribusi status")

    k1, k2, k3 = st.columns([3, 2, 2])
    with k1:
        st.segmented_control("Rentang waktu", list(RENTANG), key="a_rentang")
    with k2:
        st.select_slider("Rata-rata bergerak", [1, 3, 5, 10], key="pref_ma",
                         help="Menghaluskan garis grafik; 1 = data mentah.")
    with k3:
        st.toggle("Tampilkan garis ambang", key="pref_ambang")

    def _isi() -> None:
        s = store.snapshot()
        menit = RENTANG.get(st.session_state.get("a_rentang") or "Semua")
        df = _data(s, menit)
        ma = int(st.session_state.get("pref_ma", 1))
        render_waktu(s)

        kartu_stat = []
        for nama, kol, satuan, des, ak in [("Asap", "asap", "%", 0, "#0891b2"), ("Suhu", "suhu", " °C", 1, "#ea580c"),
                                           ("Kelembapan", "lembab", "% RH", 0, "#2563eb")]:
            stt = analitik.statistik(df, kol)
            if stt:
                sub = f"Min {angka(stt['min'], des)} · Rata-rata {angka(stt['rata'], des)} · {stt['n']} data"
                kartu_stat.append(kartu(f"{nama} — maks", angka(stt["maks"], des, satuan), sub, aksen=ak))
            else:
                kartu_stat.append(kartu(f"{nama} — maks", "Tidak tersedia", "Belum ada data valid", aksen=ak))
        grid(kartu_stat, 3)
        st.write("")
        st.plotly_chart(charts.grafik_asap(df, ma, st.session_state.get("pref_ambang", True)),
                        key="a_asap", config=CFG, theme=None)
        a, b = st.columns(2)
        a.plotly_chart(charts.grafik_suhu(df, ma), key="a_suhu", config=CFG, theme=None)
        b.plotly_chart(charts.grafik_lembab(df, ma), key="a_lembab", config=CFG, theme=None)

        st.subheader("Distribusi status")
        dur = analitik.durasi_per_status(df)
        c1, c2 = st.columns(2)
        if dur:
            c1.plotly_chart(charts.donat_status(dur, "Porsi waktu per status"), key="a_donat", config=CFG, theme=None)
            c1.caption("Perkiraan waktu: " + " · ".join(f"{k} {teks_durasi(v)}" for k, v in dur.items()))
        else:
            jml = analitik.jumlah_per_status(df)
            c1.plotly_chart(charts.donat_status(jml, "Jumlah pengukuran per status"), key="a_donat", config=CFG, theme=None)
        c2.plotly_chart(charts.sebar_suhu_lembab(df), key="a_sebar", config=CFG, theme=None)
        st.caption("Zoom/geser grafik dipertahankan saat data baru masuk. Klik dua kali grafik untuk reset. "
                   "Matikan tombol Live di bar atas untuk menahan tampilan saat memeriksa grafik.")

    live(_isi)


# =============================================================== 3. RIWAYAT
def riwayat() -> None:
    store = get_store()
    judul_halaman("Riwayat & Log", "Tabel pengukuran, perubahan status, dan log teknis")

    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    c1.multiselect("Filter status udara", STATUS_VALID, key="f_status")
    c2.selectbox("Rentang waktu", list(RENTANG), key="f_rentang")
    c3.slider("Jumlah baris", 10, config.MAX_HISTORY, step=10, key="f_baris")
    c4.toggle("Hanya data tidak valid", key="f_invalid", help="Baris dengan suhu atau kelembapan kosong.")

    statuses = list(st.session_state["f_status"])
    menit = RENTANG.get(st.session_state["f_rentang"])
    hanya_invalid = bool(st.session_state["f_invalid"])

    def _terfilter(snap: dict) -> pd.DataFrame:
        df = filter_df(to_dataframe(snap["history"]), statuses, menit)
        if hanya_invalid and not df.empty:
            df = df[df["suhu"].isna() | df["lembab"].isna()]
        return df

    def _csv() -> bytes:  # dibuat saat tombol diklik -> selalu data terbaru
        return ke_csv(_terfilter(store.snapshot()))

    st.download_button("Unduh CSV (sesuai filter)", data=_csv, icon=":material/download:",
                       file_name=f"riwayat_sentinel_{now_wib().strftime('%Y%m%d_%H%M%S')}.csv",
                       mime="text/csv", on_click="ignore")

    def _isi() -> None:
        s = store.snapshot()
        f = _terfilter(s)
        if not f.empty:
            f = f.sort_values("waktu", ascending=False)
        tab1, tab2, tab3 = st.tabs([":material/table_rows: Data pengukuran", ":material/swap_horiz: Perubahan status", ":material/terminal: Log teknis"])
        with tab1:
            st.caption(f"Menampilkan {min(len(f), st.session_state['f_baris'])} dari {len(f)} baris yang cocok "
                       f"({len(s['history'])} baris di memori).")
            if f.empty:
                st.info("Belum ada data yang cocok dengan filter.")
            else:
                st.dataframe(_tabel_riwayat(f.head(st.session_state["f_baris"])), hide_index=True)
            st.caption("Waktu adalah waktu pesan DITERIMA dashboard (WIB), bukan waktu pengukuran sensor.")
        with tab2:
            log = s["status_log"][::-1]
            if not log:
                st.caption("Belum ada perubahan status sejak dashboard berjalan.")
            else:
                st.dataframe(pd.DataFrame({
                    "Waktu (WIB)": [format_wib(x["waktu"]) for x in log],
                    "Perubahan": [f"{x['dari']} → {x['ke']}" for x in log],
                    "Asap (%)": [f"{x['asap']:g}" for x in log],
                }), hide_index=True)
        with tab3:
            ev = s["event_log"][::-1][:100]
            if not ev:
                st.caption("Belum ada kejadian.")
            for waktu, pesan in ev:
                st.text(f"[{format_wib(waktu, False)}] {pesan}")

    live(_isi)


# =============================================================== 4. SISTEM
def _diagnosis(s: dict) -> tuple[list[tuple[str, str]], str]:
    ok = lambda b: ":green[**OK**]" if b else ":red[**GAGAL**]"  # noqa: E731
    total = s["total_data"] + s["invalid_count"]
    cek = [
        (ok(s["mqtt_connected"]), f"Terhubung ke broker {config.MQTT_HOST}:{config.MQTT_PORT}"),
        (ok(s["device_status"] == "online"), f"ESP32 melapor online (status: {s['device_status'] or 'belum ada'})"),
        (ok(s["kesegaran"] == "DATA TERKINI"), f"Data terkini (≤ {config.FRESH_SECONDS:g} detik) — {s['kesegaran']}"),
        (ok(s["invalid_count"] == 0), f"Pesan data valid ({s['invalid_count']} ditolak dari {total})"),
    ]
    if not s["mqtt_connected"]:
        saran = ("Dashboard belum terhubung ke broker. Cek koneksi internet, dan pastikan port 1883 tidak diblokir "
                 "firewall/jaringan sekolah (coba hotspot HP).")
    elif s["total_data"] == 0:
        saran = ("Terhubung ke broker tetapi belum ada data. Pastikan simulasi Wokwi berjalan sampai Serial Monitor "
                 "menampilkan `MQTT: OK`, dan topic di kode ESP32 sama persis dengan topic dashboard.")
    elif s["device_status"] == "offline":
        saran = "ESP32 melaporkan offline. Jalankan ulang simulasi Wokwi atau nyalakan perangkat."
    elif s["kesegaran"] == "DATA TERLAMBAT":
        saran = "Data berhenti masuk. Cek apakah simulasi masih berjalan dan koneksi Wi-Fi ESP32 aktif."
    elif s["invalid_count"]:
        saran = "Ada pesan yang ditolak. Lihat Riwayat & Log → Log teknis untuk alasannya."
    else:
        saran = "Semua normal."
    return cek, saran


def sistem() -> None:
    store = get_store()
    judul_halaman("Sistem", "Diagnostik koneksi, perangkat, dan konfigurasi")

    def _isi() -> None:
        s = store.snapshot()
        df = to_dataframe(s["history"])
        render_waktu(s)
        render_indikator(s)
        st.write("")
        up = (s["now"] - s["started"]).total_seconds()
        laju = analitik.laju_pesan_per_menit(df)
        grid([kartu("Dashboard aktif", teks_durasi(up), f"sejak {format_wib(s['started'])}", aksen="#0891b2"),
              kartu("Pesan data", f"{s['total_data']}", f"{s['invalid_count']} ditolak", aksen="#16a34a"),
              kartu("Pesan status", f"{s['total_status']}", f"Terakhir: {esc(format_wib(s['device_status_time'], False))}",
                    aksen="#8b5cf6"),
              kartu("Laju pesan", angka(laju, 1, "/menit") if laju else "Tidak tersedia", "dari 60 pesan terakhir",
                    aksen="#ea580c")])

        st.subheader("Diagnosis")
        cek, saran = _diagnosis(s)
        for ikon, teks in cek:
            st.markdown(f"{ikon} {teks}")
        (st.success if saran == "Semua normal." else st.info)(f"**Saran:** {saran}")

        st.subheader("Konfigurasi aktif")
        st.dataframe(pd.DataFrame({
            "Parameter": ["Broker MQTT", "Port", "Topic data", "Topic status", "Client ID dashboard",
                          "Ambang WASPADA", "Ambang BAHAYA", "Batas data terkini", "Batas riwayat memori"],
            "Nilai": [config.MQTT_HOST, str(config.MQTT_PORT), config.TOPIC_DATA, config.TOPIC_STATUS,
                      s["client_id"] or "-", f"≥ {config.BATAS_WASPADA:g}%", f"> {config.BATAS_BAHAYA:g}%",
                      f"{config.FRESH_SECONDS:g} detik", f"{config.MAX_HISTORY} titik"],
        }), hide_index=True)
        st.caption("Ubah lewat environment variable (lihat README), lalu jalankan ulang aplikasi.")

    live(_isi)


# =============================================================== 5. PENGATURAN
def pengaturan() -> None:
    store = get_store()
    judul_halaman("Pengaturan", "Preferensi tampilan (berlaku untuk sesi browser ini)")

    st.subheader("Tampilan & tema")
    st.info("Tema **Terang / Sistem / Gelap** dipilih lewat tombol di bar atas (kanan). Pilihan ini berlaku untuk aplikasi "
            "ini saja dan tidak bergantung pada menu Settings Streamlit. **Sistem** mengikuti tema perangkat/browser kamu.")

    st.subheader("Pembaruan data")
    st.caption("Tombol **Live** (jeda/lanjut) ada di bar atas.")
    st.select_slider("Interval penyegaran tampilan", [1, 2, 3, 5], key="pref_refresh",
                     format_func=lambda x: f"{x} detik")
    st.slider("Jumlah titik maksimum di grafik", 50, config.MAX_HISTORY, step=50, key="pref_titik",
              help="Lebih sedikit titik = grafik lebih ringan.")
    c, d = st.columns(2)
    c.select_slider("Rata-rata bergerak grafik", [1, 3, 5, 10], key="pref_ma")
    d.toggle("Tampilkan garis ambang di grafik", key="pref_ambang")

    st.subheader("Notifikasi")
    st.toggle("Tampilkan notifikasi saat status udara berubah atau ESP32 online/offline", key="pref_notif")

    st.subheader("Ambang status (dari konfigurasi)")
    st.markdown(f"- 🟢 **AMAN**: asap < {config.BATAS_WASPADA:g}%\n"
                f"- 🟡 **WASPADA**: {config.BATAS_WASPADA:g}% sampai {config.BATAS_BAHAYA:g}% (inklusif)\n"
                f"- 🔴 **BAHAYA**: asap > {config.BATAS_BAHAYA:g}%")
    st.caption("Ambang harus sama dengan kode ESP32. Ubah via environment variable `SENTINEL_BATAS_WASPADA` / `SENTINEL_BATAS_BAHAYA`.")

    st.subheader("Data")
    st.button("Kembalikan pengaturan bawaan", on_click=reset_pref, icon=":material/restart_alt:")
    with st.expander("Hapus riwayat di memori"):
        st.warning("Menghapus semua data pengukuran dan log perubahan status di memori dashboard "
                   "(berlaku untuk semua pengunjung). Tidak bisa dibatalkan.")
        yakin = st.checkbox("Saya yakin ingin menghapus riwayat", key="yakin_hapus")
        if st.button("Hapus riwayat", disabled=not yakin, icon=":material/delete:"):
            store.hapus_riwayat()
            st.toast("Riwayat dihapus.", icon=":material/delete:")


# =============================================================== 6. BANTUAN
def bantuan() -> None:
    judul_halaman("Bantuan", "Cara membaca dashboard dan mengatasi masalah umum")
    with st.expander("Bagaimana sistem ini bekerja?", expanded=True):
        st.markdown(
            "1. **ESP32** membaca potensiometer (simulasi sensor asap MQ-2) dan DHT22 (suhu & kelembapan).\n"
            "2. ESP32 mengirim data JSON ke **broker MQTT publik HiveMQ** tiap ±8 detik, dan langsung saat status berubah.\n"
            "3. **Dashboard** ini berlangganan (subscribe) ke topic yang sama dan menampilkan datanya secara real-time.\n\n"
            "Alat tetap bekerja mandiri (LCD, LED, relay, buzzer) walaupun internet mati.")
    with st.expander("Arti status udara"):
        st.markdown(f"- 🟢 **AMAN** — asap < {config.BATAS_WASPADA:g}%\n"
                    f"- 🟡 **WASPADA** — {config.BATAS_WASPADA:g}–{config.BATAS_BAHAYA:g}% (relay belum aktif)\n"
                    f"- 🔴 **BAHAYA** — asap > {config.BATAS_BAHAYA:g}% (relay/purifier aktif, buzzer berbunyi)")
        st.caption("Kadar asap adalah persentase simulasi potensiometer, bukan konsentrasi polutan terkalibrasi "
                   "(bukan PM2.5, AQI resmi, atau ppm).")
    with st.expander("Arti indikator & label"):
        st.markdown("- **MQTT TERHUBUNG** = dashboard tersambung ke broker. Ini *tidak* berarti ESP32 menyala.\n"
                    "- **ESP32 ONLINE/OFFLINE** = dari topic status (retained + Last Will).\n"
                    "- **DATA TERKINI** = pesan terakhir ≤ 5 detik. **DATA TERLAMBAT** = lebih lama dari itu.\n"
                    "- **TERAKHIR: …** = nilai terakhir yang diterima, bukan kondisi saat ini.\n"
                    "- Waktu selalu dalam **WIB** dan merupakan waktu pesan *diterima*.")
    with st.expander("Cara membaca grafik"):
        st.markdown("- Garis putus kuning/merah = ambang WASPADA/BAHAYA.\n"
                    "- Celah pada garis = pembacaan sensor gagal (bukan nol).\n"
                    "- Drag untuk zoom, klik dua kali untuk reset. Rata-rata bergerak menghaluskan garis.")
    with st.expander("Dashboard kosong / tidak terhubung?"):
        st.markdown("- Buka halaman **Sistem** — bagian *Diagnosis* memberi saran sesuai kondisi.\n"
                    "- Pastikan topic di kode ESP32 sama persis dengan di halaman Sistem.\n"
                    "- Pastikan simulasi Wokwi sedang berjalan (`MQTT: OK` di Serial Monitor).\n"
                    "- Port 1883 bisa diblokir jaringan tertentu; coba hotspot HP.")
    with st.expander("Tentang"):
        st.markdown("**Smart Air Sentinel** — Kelompok Liminal, SMAN 1 Kota Bogor.  \n"
                    "Dibangun dengan Python, Streamlit, Plotly, Pandas, dan Paho-MQTT.")
