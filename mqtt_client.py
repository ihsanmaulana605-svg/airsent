"""Koneksi MQTT (paho-mqtt 2.x, callback API VERSION2).

Satu koneksi untuk seluruh aplikasi. Callback hanya menulis ke DataStore
(thread-safe) dan tidak menyentuh Streamlit.
"""
from __future__ import annotations

import atexit
import logging
import threading
import uuid

import paho.mqtt.client as mqtt

import config
from data_manager import DataStore

log = logging.getLogger("sentinel.mqtt")


class MqttService:
    def __init__(self, store: DataStore) -> None:
        self.store = store
        self._lock = threading.Lock()
        self._started = False
        self.client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"sentinel-dashboard-{uuid.uuid4().hex[:10]}",
            protocol=mqtt.MQTTv311,
        )
        cid = self.client._client_id
        store.client_id = cid.decode() if isinstance(cid, bytes) else str(cid)
        self.client.on_connect = self._on_connect
        self.client.on_connect_fail = self._on_connect_fail
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.reconnect_delay_set(min_delay=1, max_delay=30)

    def start(self) -> None:
        with self._lock:
            if self._started:          # jangan pernah loop_start() dua kali
                return
            self._started = True
        try:
            # connect_async + loop_start: tidak memblokir, dan otomatis mencoba ulang
            self.client.connect_async(config.MQTT_HOST, config.MQTT_PORT, keepalive=60)
            self.client.loop_start()
        except Exception as e:  # noqa: BLE001
            log.exception("Gagal memulai MQTT")
            self.store.set_mqtt_state(False, f"Gagal memulai: {e}")

    def stop(self) -> None:
        try:
            self.client.disconnect()
            self.client.loop_stop()
        except Exception:  # noqa: BLE001
            pass

    # ---- callback (thread jaringan paho)
    def _on_connect(self, client, userdata, flags, reason_code, properties):
        if reason_code.is_failure:
            self.store.set_mqtt_state(False, f"Ditolak broker: {reason_code}")
            return
        # Subscribe di sini agar otomatis diulang setelah reconnect
        client.subscribe([(config.TOPIC_DATA, 1), (config.TOPIC_STATUS, 1)])
        self.store.set_mqtt_state(True)

    def _on_connect_fail(self, client, userdata):
        self.store.set_mqtt_state(False, f"Tidak dapat menjangkau {config.MQTT_HOST}:{config.MQTT_PORT}")

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties):
        self.store.set_mqtt_state(False, f"Koneksi ke broker terputus ({reason_code})")

    def _on_message(self, client, userdata, msg):
        try:
            self.store.handle_message(msg.topic, msg.payload, bool(msg.retain))
        except Exception:  # noqa: BLE001
            log.exception("Error saat memproses pesan MQTT")


_singleton: tuple[DataStore, MqttService] | None = None
_singleton_lock = threading.Lock()


def get_service() -> tuple[DataStore, MqttService]:
    """Mengembalikan (store, service) tunggal; membuat dan menjalankannya sekali saja."""
    global _singleton
    with _singleton_lock:
        if _singleton is None:
            store = DataStore()
            service = MqttService(store)
            service.start()
            atexit.register(service.stop)
            _singleton = (store, service)
        return _singleton
