# Scripts de medición

Miden los requisitos no funcionales con el ESP32 real. No simulan datos: si faltan mediciones, el resultado es `NOT ENOUGH DATA`.

| Script | Requisito | Fuente | Qué mide |
|---|---|---|---|
| `analyze_stability.py` | RNF1 | Log del monitor serie | Duración sin reinicios, `WIFI_LOST`/`MQTT_LOST`, huecos de `seq` y la pausa más larga entre dos `PUB` de distancia (una pausa larga indica un bloqueo). |
| `analyze_accuracy.py` | RNF2 | Tópico `distance` | Error frente a una regla en varias distancias de referencia (10 lecturas válidas en cada una) y el rango de trabajo donde se cumple ±3 cm. |
| `measure_response_time.py` | RNF3 | Tópicos `leds/cmd` y `leds/state` | Tiempo desde publicar un comando hasta recibir el `leds/state` que lo confirma (ida y vuelta PC → broker → OI → broker → PC). |
| `measure_publish_rate.py` | RNF4 | Tópico `distance` | Lecturas por segundo en ventanas de 10 s, más los huecos de `seq` y las lecturas `null`. |
| `analyze_reconnection.py` | RNF5 | Log del monitor serie | En cada caída, el tiempo desde `WIFI_LOST`/`MQTT_LOST` hasta `MQTT_CONNECTED` y si hubo un reinicio en medio. |

Módulos compartidos:

- `tools_config.py`: umbrales, tiempos y client IDs. El contrato MQTT (broker, tópicos, QoS y valores de los LEDs) se importa de `mcp_server/config.py`, así no hay dos copias que puedan diferir.
- `report.py`: imprime cada línea y, con `--output`, guarda exactamente lo mismo en un archivo, con la fecha y la hora al inicio.
- `serial_log.py`: lee los logs de `pio device monitor` (formato `[t_ms=...] EVENTO detalles` de `src/EventLog.cpp`) e ignora las líneas del bootloader.

Cada script termina con una línea `PASS`, `FAIL` o `NOT ENOUGH DATA`.

## Ejecución

Los scripts usan el entorno de `mcp_server`, que ya tiene `paho-mqtt`. Desde la raíz del repositorio, en PowerShell:

```powershell
uv run --project mcp_server python tools\measure_publish_rate.py --output docs\evidencias\RNF4\publish_rate.txt
uv run --project mcp_server python tools\measure_response_time.py --output docs\evidencias\RNF3\response_time.txt
uv run --project mcp_server python tools\analyze_accuracy.py --output docs\evidencias\RNF2\accuracy.txt
uv run --project mcp_server python tools\analyze_stability.py docs\evidencias\RNF1\serial_log.txt --stop-at-first-drop --output docs\evidencias\RNF1\stability.txt
uv run --project mcp_server python tools\analyze_reconnection.py docs\evidencias\RNF1\serial_log.txt --output docs\evidencias\RNF5\reconnection.txt
```

- Mientras se mide RNF3 o RNF4, nadie debe usar Claude Desktop ni la app, para que ningún otro comando se mezcle con la prueba.
- `analyze_accuracy.py` es interactivo: en cada distancia pide colocar el objeto y pulsar Enter (`s` + Enter salta esa distancia).
- `--stop-at-first-drop` analiza solo la parte del log anterior a la primera caída, para que las caídas provocadas para RNF5 no cuenten en la estabilidad.
- Los logs del monitor serie se guardan en `logs/` (ignorado por git). Antes de copiar uno como evidencia, se borra el nombre de la red WiFi de la línea `WIFI_CONNECTING`.

## Revisión de estilo

```powershell
uv run --project mcp_server ruff check --config mcp_server\pyproject.toml tools
uv run --project mcp_server flake8 --config mcp_server\.flake8 tools
```
