# Scripts de medición

Miden los requisitos no funcionales que dependen de la red, con el ESP32 real conectado al broker. No simulan datos: si el objeto inteligente no responde, el resultado es `NOT ENOUGH DATA`.

| Script | Requisito | Qué mide |
|---|---|---|
| `measure_response_time.py` | RNF3 | Tiempo desde publicar un comando en `leds/cmd` hasta recibir el `leds/state` que lo confirma (ida y vuelta PC → broker → OI → broker → PC). |
| `measure_publish_rate.py` | RNF4 | Lecturas por segundo en `distance`, en ventanas de 10 s, más los huecos de `seq` y las lecturas `null`. |

`tools_config.py` reúne los umbrales, tiempos y client IDs de las pruebas. El contrato MQTT (broker, tópicos, QoS y valores de los LEDs) se importa de `mcp_server/config.py`, así no hay dos copias que puedan diferir. `report.py` imprime cada línea y, con `--output`, guarda exactamente lo mismo en un archivo.

Cada script termina con una línea `PASS`, `FAIL` o `NOT ENOUGH DATA`.

## Ejecución

Los scripts usan el entorno de `mcp_server`, que ya tiene `paho-mqtt`. Desde la raíz del repositorio, en PowerShell:

```powershell
uv run --project mcp_server python tools\measure_publish_rate.py --output docs\evidencias\RNF4\publish_rate.txt
uv run --project mcp_server python tools\measure_response_time.py --output docs\evidencias\RNF3\response_time.txt
```

`--output` guarda la misma salida de la consola, con la fecha y la hora al inicio. Sin `--output`, solo se imprime.

Mientras se mide, nadie debe usar Claude Desktop ni la app, para que ningún otro comando se mezcle con la prueba.

## Revisión de estilo

```powershell
uv run --project mcp_server ruff check --config mcp_server\pyproject.toml tools
uv run --project mcp_server flake8 --config mcp_server\.flake8 tools
```
