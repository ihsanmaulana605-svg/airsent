from __future__ import annotations

import streamlit as st

from halaman import analisis, bantuan, pengaturan, riwayat, ringkasan, sistem
from ui import CSS, css_tema, get_store, init_state, render_navbar

st.set_page_config(page_title="Smart Air Sentinel", page_icon="🛰️", layout="wide",
                   initial_sidebar_state="collapsed")
init_state()
st.markdown(CSS, unsafe_allow_html=True)
st.markdown(css_tema(), unsafe_allow_html=True)
store = get_store()

# Navigasi bawaan disembunyikan; bar navigasi kustom dibuat di render_navbar()
halaman = [
    st.Page(ringkasan, title="Ringkasan", icon=":material/dashboard:", url_path="ringkasan", default=True),
    st.Page(analisis, title="Analisis", icon=":material/monitoring:", url_path="analisis"),
    st.Page(riwayat, title="Riwayat", icon=":material/history:", url_path="riwayat"),
    st.Page(sistem, title="Sistem", icon=":material/memory:", url_path="sistem"),
    st.Page(pengaturan, title="Pengaturan", icon=":material/settings:", url_path="pengaturan"),
    st.Page(bantuan, title="Bantuan", icon=":material/help:", url_path="bantuan"),
]
nav = st.navigation(halaman, position="hidden")
aktif = next((i for i, p in enumerate(halaman) if p is nav), 0)
render_navbar(halaman, store, aktif)


def _notifier() -> None:
    s = store.snapshot()
    ss = st.session_state
    if "seen_seq" not in ss:         
        ss["seen_seq"] = s["seq"]
        return
    batas = ss["seen_seq"]
    ss["seen_seq"] = s["seq"]
    if not ss.get("pref_notif", True):
        return
    kejadian = [("status", x) for x in s["status_log"] if x["seq"] > batas] + \
               [("device", x) for x in s["device_log"] if x["seq"] > batas]
    for jenis, x in sorted(kejadian, key=lambda k: k[1]["seq"]):
        if jenis == "status":
            ikon = {"AMAN": "🟢", "WASPADA": "🟡", "BAHAYA": "🚨"}[x["ke"]]
            st.toast(f"Status udara: {x['dari']} → {x['ke']} (asap {x['asap']:g}%)", icon=ikon)
        else:
            st.toast(f"ESP32 {x['status'].upper()}", icon="🟢" if x["status"] == "online" else "🔌")


st.fragment(run_every=2)(_notifier)()

nav.run()

st.markdown('<div class="footer">Smart Air Sentinel · Kelompok Liminal · SMAN 1 Kota Bogor</div>', unsafe_allow_html=True)
