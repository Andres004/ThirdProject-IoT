# RNF4 — Frecuencia de publicación

- **Qué se mide:** lecturas por segundo que llegan del tópico `sis234/grupo1/distance`, en ventanas de 10 s durante 60 s, más los huecos de `seq` y las lecturas `null` (que también son publicaciones).
- **Cómo:** `uv run --project mcp_server python tools\measure_publish_rate.py --output docs\evidencias\RNF4\publish_rate.txt`, con el ESP32 real conectado al broker público.
- **Valor declarado:** 1 lectura/s (`SensorConfig::SAMPLE_PERIOD_MS = 1000`).

- **Fecha:** 03/11/2026.

## Resultado

61 lecturas en 60 s: media **1.018 lecturas/s**, mínimo por ventana 0.900/s, 0 huecos de `seq` y 0 reinicios de `seq` → **PASS** (`publish_rate.txt`). Las ventanas varían entre 0.9 y 1.2 lecturas/s porque la red agrupa algunos mensajes: uno que llega tarde cae en la ventana siguiente, pero no se pierde ninguno.
