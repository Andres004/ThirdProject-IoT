# RNF4 — Frecuencia de publicación

- **Qué se mide:** lecturas por segundo que llegan del tópico `sis234/grupo1/distance`, en ventanas de 10 s durante 60 s, más los huecos de `seq` y las lecturas `null` (que también son publicaciones).
- **Cómo:** `uv run --project mcp_server python tools\measure_publish_rate.py --output docs\evidencias\RNF4\publish_rate.txt`, con el ESP32 real conectado al broker público.
- **Valor declarado:** 1 lectura/s (`SensorConfig::SAMPLE_PERIOD_MS = 1000`).

## Estado

`publish_rate.txt` contiene la medición del 29/10/2026, hecha con el período anterior de 400 ms (2.50 lecturas/s). Esa medición no corresponde al período actual y se reemplaza con una nueva corrida a 1 lectura/s.
