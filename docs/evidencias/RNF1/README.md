# RNF1 — Estabilidad

- **Qué se mide:** que el ESP32 funcione de forma continua al menos 10 minutos sin reiniciarse (`BOOT`), sin perder la conexión (`WIFI_LOST`, `MQTT_LOST`) y sin bloquearse (pausas largas entre publicaciones de `distance`).
- **Cómo:** monitor serie de PlatformIO con `log2file`, ESP32 real conectado al broker público, período de 1 s (`SensorConfig::SAMPLE_PERIOD_MS = 1000`). El log se copió a `serial_log.txt` ocultando el nombre de la red y se analizó con:
  `uv run --project mcp_server python tools\analyze_stability.py docs\evidencias\RNF1\serial_log.txt --stop-at-first-drop --output docs\evidencias\RNF1\stability.txt`
- **Fecha:** 03/11/2026.

## Resultado

775.0 s (12.9 min) sin reinicios ni caídas de WiFi o MQTT → **PASS** (`stability.txt`).

## Observación sobre `seq_gaps=3` y la pausa de 2001 ms

En 3 de las 775 líneas de `distance` (las de `seq` 115, 310 y 771) el puerto serie entregó bytes dañados en lugar del inicio `[t_m` de la línea. El resto de cada línea, con su `seq` y su distancia, sí está en el log. El script no reconoce esas 3 líneas, por eso informa 3 huecos de `seq` y una pausa de 2001 ms (dos períodos). No son lecturas perdidas ni bloqueos del firmware: la secuencia `seq` de 1 a 775 está completa en el archivo.
