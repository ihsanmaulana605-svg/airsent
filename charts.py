from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import config
from analitik import rata_bergerak

CYAN, ORANYE, BIRU = "#0891b2", "#ea580c", "#2563eb"
WARNA_STATUS = {"AMAN": "#16a34a", "WASPADA": "#d97706", "BAHAYA": "#dc2626"}
GRID = "rgba(128,128,128,0.22)"


def _estilo(fig: go.Figure) -> go.Figure:
    try:
        terang = st.context.theme.type == "light"
    except Exception:  # noqa: BLE001
        terang = False
    fig.update_layout(template="plotly_white" if terang else "plotly_dark",
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(color="#31333f" if terang else "#fafafa"),
                      modebar=dict(bgcolor="rgba(0,0,0,0)"))
    return fig


def _siap(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["waktu"] = out["waktu"].dt.tz_convert(config.WIB).dt.tz_localize(None)
    return out


def _layout(fig: go.Figure, judul: str, y_judul: str, y_range=None, tinggi: int = 320) -> go.Figure:
    fig.update_layout(
        title=dict(text=judul, x=0.01),
        height=tinggi,
        margin=dict(l=10, r=10, t=50, b=10),
        xaxis=dict(title="Waktu (WIB)", gridcolor=GRID),
        yaxis=dict(title=y_judul, gridcolor=GRID, range=y_range),
        hovermode="x unified",
        showlegend=False,
        uirevision="tetap",
    )
    return _estilo(fig)


def _kosong(judul: str, y_judul: str, y_range=None, tinggi: int = 320) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text="Belum ada data", showarrow=False, font=dict(size=16),
                       xref="paper", yref="paper", x=0.5, y=0.5, opacity=0.6)
    return _layout(fig, judul, y_judul, y_range, tinggi)


def _seri(df: pd.DataFrame, kolom: str, warna: str, satuan: str, ma: int) -> list:
    d = _siap(df)
    ht = "%{y:.1f} " + satuan + "<extra></extra>"
    if ma <= 1:
        return [go.Scatter(x=d["waktu"], y=d[kolom], mode="lines+markers", connectgaps=False,
                           line=dict(color=warna, width=2), marker=dict(size=4), hovertemplate=ht)]
    halus = rata_bergerak(d[kolom], ma)
    return [
        go.Scatter(x=d["waktu"], y=d[kolom], mode="lines", connectgaps=False, opacity=0.3,
                   line=dict(color=warna, width=1), hoverinfo="skip"),
        go.Scatter(x=d["waktu"], y=halus, mode="lines", connectgaps=False,
                   line=dict(color=warna, width=3), hovertemplate=ht.replace("<extra>", f" (rata-rata {ma})<extra>")),
    ]


def grafik_asap(df: pd.DataFrame, ma: int = 1, ambang: bool = True, tinggi: int = 340) -> go.Figure:
    judul, yj = "Kadar Asap (simulasi MQ-2)", "Asap (%)"
    if df.empty:
        return _kosong(judul, yj, [0, 100], tinggi)
    fig = go.Figure(_seri(df, "asap", CYAN, "%", ma))
    if ambang:
        fig.add_hline(y=config.BATAS_WASPADA, line_dash="dash", line_color=WARNA_STATUS["WASPADA"],
                      annotation_text=f"Waspada {config.BATAS_WASPADA:g}%", annotation_position="top left")
        fig.add_hline(y=config.BATAS_BAHAYA, line_dash="dash", line_color=WARNA_STATUS["BAHAYA"],
                      annotation_text=f"Bahaya {config.BATAS_BAHAYA:g}%", annotation_position="top left")
    return _layout(fig, judul, yj, [0, 100], tinggi)


def grafik_suhu(df: pd.DataFrame, ma: int = 1, tinggi: int = 300) -> go.Figure:
    judul, yj = "Suhu", "Suhu (°C)"
    if df.empty:
        return _kosong(judul, yj, None, tinggi)
    return _layout(go.Figure(_seri(df, "suhu", ORANYE, "°C", ma)), judul, yj, None, tinggi)


def grafik_lembab(df: pd.DataFrame, ma: int = 1, tinggi: int = 300) -> go.Figure:
    judul, yj = "Kelembapan", "Kelembapan (% RH)"
    if df.empty:
        return _kosong(judul, yj, [0, 100], tinggi)
    return _layout(go.Figure(_seri(df, "lembab", BIRU, "% RH", ma)), judul, yj, [0, 100], tinggi)


def gauge_asap(nilai: float | None) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=0 if nilai is None else nilai,
        number=dict(suffix="%", valueformat=".0f") if nilai is not None else dict(suffix="", valueformat=""),
        title=dict(text="Kadar Asap"),
        gauge=dict(
            axis=dict(range=[0, 100]),
            bar=dict(color="rgba(8,145,178,0.9)", thickness=0.28),
            steps=[
                dict(range=[0, config.BATAS_WASPADA], color="rgba(22,163,74,0.35)"),
                dict(range=[config.BATAS_WASPADA, config.BATAS_BAHAYA], color="rgba(217,119,6,0.35)"),
                dict(range=[config.BATAS_BAHAYA, 100], color="rgba(220,38,38,0.35)"),
            ],
        ),
    ))
    if nilai is None:
        fig.add_annotation(text="Menunggu data", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.25, opacity=0.6)
    fig.update_layout(height=270, margin=dict(l=40, r=40, t=50, b=10))
    return _estilo(fig)


def donat_status(data: dict, judul: str) -> go.Figure:
    fig = go.Figure()
    if data:
        fig.add_trace(go.Pie(labels=list(data), values=list(data.values()), hole=0.6, sort=False,
                             marker=dict(colors=[WARNA_STATUS[k] for k in data]),
                             textinfo="percent", hovertemplate="%{label}: %{value:.0f}<extra></extra>"))
    else:
        fig.add_annotation(text="Belum ada data", showarrow=False, xref="paper", yref="paper", x=0.5, y=0.5, opacity=0.6)
    fig.update_layout(title=dict(text=judul, x=0.01), height=300, margin=dict(l=10, r=10, t=50, b=10),
                      legend=dict(orientation="h", y=-0.05))
    return _estilo(fig)


def sebar_suhu_lembab(df: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    d = df.dropna(subset=["suhu", "lembab"]) if not df.empty else df
    if d.empty:
        fig.add_annotation(text="Belum ada data suhu & kelembapan valid", showarrow=False,
                           xref="paper", yref="paper", x=0.5, y=0.5, opacity=0.6)
    else:
        for st_, warna in WARNA_STATUS.items():
            x = d[d["status"] == st_]
            if not x.empty:
                fig.add_trace(go.Scatter(x=x["suhu"], y=x["lembab"], mode="markers", name=st_,
                                         marker=dict(color=warna, size=7, opacity=0.8),
                                         hovertemplate="Suhu %{x:.1f} °C<br>Lembab %{y:.0f}%<extra>" + st_ + "</extra>"))
    fig.update_layout(title=dict(text="Suhu vs Kelembapan (warna = status)", x=0.01), height=300,
                      margin=dict(l=10, r=10, t=50, b=10), xaxis=dict(title="Suhu (°C)", gridcolor=GRID),
                      yaxis=dict(title="Kelembapan (% RH)", gridcolor=GRID), legend=dict(orientation="h", y=-0.2))
    return _estilo(fig)
