# RNF1 — Estabilidad

- **Qué se mide:** que el ESP32 funcione de forma continua al menos 10 minutos sin reiniciarse (`BOOT`), sin perder la conexión (`WIFI_LOST`, `MQTT_LOST`) y sin bloquearse (pausas largas entre publicaciones de `distance`).
- **Cómo:** monitor serie de PlatformIO con `log2file`, ESP32 real conectado al broker público, período de 1 s (`SensorConfig::SAMPLE_PERIOD_MS = 1000`), firmware final con DNS no bloqueante. El log se copió a `serial_log.txt` ocultando el nombre de la red y se analizó solo hasta la primera caída (las caídas posteriores son las provocadas para RNF5, con el mismo log):
  `uv run --project mcp_server python tools\analyze_stability.py docs\evidencias\RNF1\serial_log.txt --stop-at-first-drop --output docs\evidencias\RNF1\stability.txt`
- **Fecha:** 03/11/2026.

## Resultado

788.1 s (13.1 min) sin reinicios ni caídas de WiFi o MQTT → **PASS** (`stability.txt`).

## Observación sobre `seq_gaps=2` y la pausa de 2003 ms

En algunas líneas el puerto serie USB entregó bytes dañados en lugar del inicio `[t_m` de la línea; el resto de la línea, con su `seq` y su distancia, sí está en el log. El script no reconoce esas líneas, por eso informa 2 huecos de `seq` y una pausa de unos 2 s (dos períodos) en el tramo analizado. No son lecturas perdidas ni bloqueos del firmware: la secuencia `seq` del archivo está completa, sin saltos.
