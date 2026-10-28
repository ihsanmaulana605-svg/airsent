
from __future__ import annotations

import json
import math
import threading
from collections import deque
from datetime import datetime
from typing import Any, Optional

import pandas as pd

import config

STATUS_VALID = ("AMAN", "WASPADA", "BAHAYA")
BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
         "Agustus", "September", "Oktober", "November", "Desember"]
KOLOM = ["waktu", "asap", "suhu", "lembab", "status", "status_hitung", "relay"]


def now_wib() -> datetime:
    return datetime.now(config.WIB)


def format_wib(dt: Optional[datetime], dengan_tanggal: bool = True) -> str:
    if dt is None:
        return "-"
    dt = dt.astimezone(config.WIB)
    jam = dt.strftime("%H:%M:%S")
    if not dengan_tanggal:
        return f"{jam} WIB"
    return f"{dt.day} {BULAN[dt.month - 1]} {dt.year}, {jam} WIB"


def teks_usia(detik: Optional[float]) -> str:
    if detik is None:
        return "Belum ada data diterima"
    d = int(detik)
    if d < 60:
        return f"{d} detik yang lalu"
    m, s = divmod(d, 60)
    if m < 60:
        return f"{m} menit {s} detik yang lalu"
    j, m = divmod(m, 60)
    return f"{j} jam {m} menit yang lalu"


def teks_durasi(detik: float) -> str:
    d = int(detik)
    h, sisa = divmod(d, 3600)
    m, sc = divmod(sisa, 60)
    if h:
        return f"{h} j {m} m"
    if m:
        return f"{m} m {sc} d"
    return f"{sc} d"


def hitung_status(asap: float) -> str:
    if asap < config.BATAS_WASPADA:
        return "AMAN"
    if asap <= config.BATAS_BAHAYA:
        return "WASPADA"
    return "BAHAYA"


def _angka(nilai: Any) -> Optional[float]:
    """Angka valid -> float; None/bool/string/NaN/inf -> None."""
    if nilai is None or isinstance(nilai, bool):
        return None
    if isinstance(nilai, (int, float)):
        f = float(nilai)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    return None


def parse_payload(raw: bytes) -> tuple[Optional[dict], Optional[str]]:
    """Mengembalikan (record, None) bila valid, atau (None, pesan_error)."""
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return None, f"JSON tidak valid: {e}"
    if not isinstance(data, dict):
        return None, "Payload bukan objek JSON"

    asap = _angka(data.get("asap"))
    if asap is None or not 0 <= asap <= 100:
        return None, f"Nilai 'asap' tidak valid: {data.get('asap')!r}"

    status = data.get("status")
    if not isinstance(status, str) or status.strip().upper() not in STATUS_VALID:
        return None, f"Nilai 'status' tidak valid: {status!r}"

    suhu = _angka(data.get("suhu"))
    if suhu is not None and not -40 <= suhu <= 80:
        suhu = None
    lembab = _angka(data.get("lembab"))
    if lembab is not None and not 0 <= lembab <= 100:
        lembab = None
    relay = data.get("relay")
    relay = relay if isinstance(relay, bool) else None
    adc = _angka(data.get("adc"))                    
    adc = int(adc) if adc is not None and 0 <= adc <= 4095 else None

    return {
        "asap": asap,
        "suhu": suhu,
        "lembab": lembab,
        "status": status.strip().upper(),
        "status_hitung": hitung_status(asap),
        "relay": relay,
        "adc": adc,
    }, None


class DataStore:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._history: deque = deque(maxlen=config.MAX_HISTORY)
        self._status_log: deque = deque(maxlen=config.MAX_LOG)
        self._event_log: deque = deque(maxlen=config.MAX_LOG)
        self.mqtt_connected = False
        self.mqtt_error: Optional[str] = None
        self.device_status: Optional[str] = None     
        self.device_status_time: Optional[datetime] = None
        self.last_data_time: Optional[datetime] = None
        self.last_record: Optional[dict] = None
        self.invalid_count = 0
        self._last_status: Optional[str] = None
        self._device_log: deque = deque(maxlen=config.MAX_LOG)
        self._seq = 0
        self.total_data = 0
        self.total_status = 0
        self.started = now_wib()
        self.client_id: Optional[str] = None

    
    def log_event(self, pesan: str) -> None:
        with self._lock:
            self._event_log.append((now_wib(), pesan))

    def set_mqtt_state(self, terhubung: bool, error: Optional[str] = None) -> None:
        with self._lock:
            self.mqtt_connected = terhubung
            self.mqtt_error = None if terhubung else error
            self._event_log.append(
                (now_wib(), "MQTT terhubung" if terhubung else f"MQTT terputus: {error}"))

    def handle_message(self, topic: str, payload: bytes, retain: bool = False) -> None:
        waktu = now_wib()  # waktu terima di sisi Python (bukan waktu ukur sensor)
        with self._lock:
            if topic == config.TOPIC_DATA:
                self._proses_data(waktu, payload)
            elif topic == config.TOPIC_STATUS:
                self._proses_status(waktu, payload, retain)
            else:
                self._event_log.append((waktu, f"Topik tidak dikenal diabaikan: {topic}"))

    def _proses_data(self, waktu: datetime, payload: bytes) -> None:
        rec, err = parse_payload(payload)
        if rec is None:
            self.invalid_count += 1
            self._event_log.append((waktu, f"Pesan data ditolak: {err}"))
            return
        rec["waktu"] = waktu
        self._history.append(rec)
        self.total_data += 1
        self.last_record = rec
        self.last_data_time = waktu
        # Log hanya saat status benar-benar berubah antar pesan yang diterima
        if self._last_status is not None and rec["status"] != self._last_status:
            self._seq += 1
            self._status_log.append({"seq": self._seq, "waktu": waktu, "dari": self._last_status,
                                     "ke": rec["status"], "asap": rec["asap"]})
        self._last_status = rec["status"]

    def _proses_status(self, waktu: datetime, payload: bytes, retain: bool) -> None:
        teks = payload.decode("utf-8", errors="replace").strip().lower()
        if teks not in ("online", "offline"):
            self._event_log.append((waktu, f"Pesan status tidak dikenal: {teks[:40]!r}"))
            return
        self.device_status = teks
        self.device_status_time = waktu
        self.total_status += 1
        self._seq += 1
        self._device_log.append({"seq": self._seq, "waktu": waktu, "status": teks})
        asal = " (retained)" if retain else ""
        self._event_log.append((waktu, f"Status perangkat: {teks}{asal}"))

    # ---- dipanggil dari UI Streamlit
    def snapshot(self) -> dict:
        with self._lock:
            now = now_wib()
            usia = None
            if self.last_data_time is not None:
                usia = max(0.0, (now - self.last_data_time).total_seconds())
            if usia is None:
                kesegaran = "TIDAK ADA DATA"
            elif usia <= config.FRESH_SECONDS:
                kesegaran = "DATA TERKINI"
            else:
                kesegaran = "DATA TERLAMBAT"
            return {
                "now": now,
                "mqtt_connected": self.mqtt_connected,
                "mqtt_error": self.mqtt_error,
                "device_status": self.device_status,
                "device_status_time": self.device_status_time,
                "last_data_time": self.last_data_time,
                "usia": usia,
                "kesegaran": kesegaran,
                "last_record": dict(self.last_record) if self.last_record else None,
                "invalid_count": self.invalid_count,
                "history": [dict(r) for r in self._history],
                "status_log": [dict(r) for r in self._status_log],
                "event_log": list(self._event_log),
                "device_log": [dict(r) for r in self._device_log],
                "total_data": self.total_data,
                "total_status": self.total_status,
                "started": self.started,
                "client_id": self.client_id,
                "seq": self._seq,
            }

    def hapus_riwayat(self) -> None:
        """Mengosongkan riwayat data & log perubahan status (counter tetap)."""
        with self._lock:
            self._history.clear()
            self._status_log.clear()
            self._last_status = None
            self.last_record = None
            self.last_data_time = None
            self._event_log.append((now_wib(), "Riwayat dihapus oleh pengguna"))



def to_dataframe(history: list[dict]) -> pd.DataFrame:
    if not history:
        return pd.DataFrame(columns=KOLOM)
    df = pd.DataFrame(history, columns=KOLOM)
    df["waktu"] = pd.to_datetime(df["waktu"])
    for k in ("asap", "suhu", "lembab"):
        df[k] = pd.to_numeric(df[k], errors="coerce")  
    return df


def filter_df(df: pd.DataFrame, statuses: list[str], menit: Optional[int]) -> pd.DataFrame:
    if df.empty:
        return df
    out = df
    if menit:
        batas = now_wib() - pd.Timedelta(minutes=menit)
        out = out[out["waktu"] >= batas]
    if statuses:
        out = out[out["status"].isin(statuses)]
    return out


def ke_csv(df: pd.DataFrame) -> bytes:
    kolom = ["Waktu (WIB)", "Asap (%)", "Suhu (°C)", "Kelembapan (% RH)",
             "Status ESP32", "Status Hitung Python", "Relay"]
    if df.empty:
        return pd.DataFrame(columns=kolom).to_csv(index=False).encode("utf-8-sig")
    out = df.copy()
    out["waktu"] = out["waktu"].dt.strftime("%Y-%m-%d %H:%M:%S")
    out["relay"] = out["relay"].map({True: "AKTIF", False: "NONAKTIF"}).fillna("TIDAK DIKETAHUI")
    out.columns = kolom
    return out.to_csv(index=False).encode("utf-8-sig")  # BOM agar terbaca di Excel
