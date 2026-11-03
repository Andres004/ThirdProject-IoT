# RNF3 — Tiempo de respuesta

- **Qué se mide:** el tiempo desde que un cliente publica un comando en `leds/cmd` hasta que el ESP32 lo aplica.
- **Cómo:** `uv run --project mcp_server python tools\measure_response_time.py --output docs\evidencias\RNF3\response_time.txt`. El script publica 20 comandos al LED rojo (encender/apagar, QoS 1, 1 s de pausa) y mide hasta recibir el `leds/state` que confirma cada uno. Es un tiempo de **ida y vuelta** (PC → broker → ESP32 → broker → PC), más exigente que el requisito (solo la ida, app → broker → ESP32), que no se puede medir por separado sin relojes sincronizados.
- **Fecha:** 03/11/2026, firmware final, ESP32 conectado a un hotspot de celular (datos móviles) y PC en otra red.

## Resultados (ida y vuelta)

| Corrida | Red del ESP32 | Media | p95 | Máximo | Comandos > 1 s | Perdidos |
|---|---|---|---|---|---|---|
| 1 | hotspot A | 727.5 ms | 1215.0 ms | 1557.4 ms | 3/20 | 0 |
| 2 | hotspot A | 631.1 ms | 970.2 ms | 1120.8 ms | 1/20 | 0 |
| 3 | hotspot B | 747.4 ms | 1513.8 ms | 1597.3 ms | 3/20 | 0 |

`response_time.txt` contiene la corrida 3 y `serial_log.txt` el log serie del ESP32 durante esa misma corrida (con el nombre de la red oculto). [`app_led_response.mp4`](app_led_response.mp4) muestra el camino completo del requisito con la app real: los switches de IoT MQTT Panel encienden y apagan los LEDs del ESP32. Las corridas 1 y 2 se ejecutaron con el mismo comando y su resumen se copió de la salida de la terminal.

Con el criterio estricto del script (máximo de ida y vuelta ≤ 1000 ms) el resultado es **FAIL**: 53 de los 60 comandos se confirmaron en menos de 1 s y 7 tardaron entre 1.0 y 1.6 s.

## Análisis: la demora está en la red, no en el ESP32

- En el log serie, el tiempo entre `CMD_RX` (comando recibido) y la publicación de `leds/state` es de **1 a 5 ms** en todos los comandos: el firmware aplica el comando de inmediato.
- Comparando cuándo publicó el script cada comando con cuándo lo recibió el ESP32 (`CMD_RX`), los comandos lentos llegaron al ESP32 hasta ~600 ms más tarde que el resto: el atraso se produce en el tramo de ida (cliente → broker → ESP32), por la latencia variable de la red celular del hotspot.
- Cambiar de hotspot (corrida 3) no eliminó los picos. Una red WiFi fija con buen acceso a internet reduciría esa variación.
