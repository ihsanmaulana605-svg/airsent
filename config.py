import os
from zoneinfo import ZoneInfo


def _env(nama: str, bawaan: str) -> str:
    return os.getenv(nama, bawaan)

MQTT_HOST = _env("SENTINEL_MQTT_HOST", "broker.hivemq.com")
MQTT_PORT = int(_env("SENTINEL_MQTT_PORT", "1883"))
TOPIC_DATA = _env("SENTINEL_TOPIC_DATA", "sentinel/liminal-ammar321/data")
TOPIC_STATUS = _env("SENTINEL_TOPIC_STATUS", "sentinel/liminal-ammar321/status")

BATAS_WASPADA = float(_env("SENTINEL_BATAS_WASPADA", "40"))
BATAS_BAHAYA = float(_env("SENTINEL_BATAS_BAHAYA", "70"))

FRESH_SECONDS = float(_env("SENTINEL_FRESH_SECONDS", "5"))              # <= ini: DATA TERKINI
DEVICE_STALE_SECONDS = float(_env("SENTINEL_DEVICE_STALE_SECONDS", "15"))  # status online tapi data berhenti
REFRESH_SECONDS = float(_env("SENTINEL_REFRESH_SECONDS", "1"))          # interval refresh UI

MAX_HISTORY = 1000
MAX_LOG = 200

WIB = ZoneInfo("Asia/Jakarta")
