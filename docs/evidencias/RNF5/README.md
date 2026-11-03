# RNF5 — Reconexión automática

- **Qué se mide:** que el ESP32 recupere solo el WiFi y la sesión MQTT después de una caída, sin reiniciarse, y cuánto tarda.
- **Cómo:** el mismo log de RNF1 (monitor serie con `log2file`, firmware final con DNS no bloqueante), con 3 caídas provocadas después de los primeros 13 min:
  1. Hotspot del celular apagado unos 30 s.
  2. Hotspot encendido pero sin datos móviles (broker inalcanzable) unos 60 s.
  3. Hotspot apagado otra vez.

  Analizado con `uv run --project mcp_server python tools\analyze_reconnection.py docs\evidencias\RNF5\serial_log.txt --output docs\evidencias\RNF5\reconnection.txt`.
- **Fecha:** 03/11/2026.

## Resultado

3/3 caídas recuperadas sin reinicio; MQTT vuelve **0.8–1.1 s** después de que vuelve el WiFi → **PASS** (`reconnection.txt`).

- Las interrupciones totales (~131 s) incluyen el tiempo con la red cortada y unos 2 min que el iPhone tarda en desconectar al ESP32 cuando deja de dar servicio: en los tres casos `WIFI_LOST` llega 120 s después de `MQTT_LOST`.
- **Sin bloqueos durante las caídas:** la búsqueda DNS del broker es asíncrona, así que cada reintento MQTT sin internet termina en unos 14 ms (o espera la respuesta del DNS en segundo plano, `dns_ms=7000`) y el `loop()` sigue midiendo. La pausa más larga entre dos lecturas (`PUB` o `PUB_FAILED`) durante las caídas fue de 1395 ms, con un período de 1000 ms; el `seq` no tiene saltos y los LEDs parpadean sin congelarse.
