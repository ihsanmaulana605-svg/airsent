from __future__ import annotations

from typing import Optional

import pandas as pd

from data_manager import STATUS_VALID


def statistik(df: pd.DataFrame, kolom: str) -> Optional[dict]:
    if df.empty:
        return None
    v = df[kolom].dropna()
    if v.empty:
        return None
    return {"min": float(v.min()), "rata": float(v.mean()), "maks": float(v.max()), "n": int(v.size)}


def durasi_per_status(df: pd.DataFrame, batas_celah: float = 10.0) -> dict:
    """Perkiraan waktu (detik) di tiap status. Celah antar-pesan > batas_celah dipotong
    agar waktu saat ESP32 mati tidak dihitung."""
    if len(df) < 2:
        return {}
    d = df.sort_values("waktu")
    selisih = d["waktu"].shift(-1) - d["waktu"]
    detik = selisih.dt.total_seconds().clip(upper=batas_celah)
    hasil = detik.groupby(d["status"]).sum()
    return {k: float(hasil.get(k, 0.0)) for k in STATUS_VALID if hasil.get(k, 0.0) > 0}


def jumlah_per_status(df: pd.DataFrame) -> dict:
    if df.empty:
        return {}
    h = df["status"].value_counts()
    return {k: int(h.get(k, 0)) for k in STATUS_VALID if h.get(k, 0) > 0}


def laju_pesan_per_menit(df: pd.DataFrame, maks: int = 60) -> Optional[float]:
    if len(df) < 2:
        return None
    d = df.sort_values("waktu").tail(maks)
    rentang = (d["waktu"].iloc[-1] - d["waktu"].iloc[0]).total_seconds()
    if rentang <= 0:
        return None
    return (len(d) - 1) / rentang * 60.0


def rata_bergerak(seri: pd.Series, jendela: int) -> pd.Series:
    if jendela <= 1:
        return seri
    return seri.rolling(jendela, min_periods=1).mean()
