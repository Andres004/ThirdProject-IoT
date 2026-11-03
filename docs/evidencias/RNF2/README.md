# RNF2 — Exactitud de la medición

- **Qué se mide:** el error de cada lectura publicada en `sis234/grupo1/distance` frente a una distancia de referencia medida con cinta métrica, y el rango de trabajo donde todas las lecturas quedan dentro de ±3 cm.
- **Cómo:** ESP32 real conectado al broker público, sensor elevado en el borde de la mesa y apuntando de frente a una pared lisa; se movió el sensor (no el objetivo) a 5, 10, 20, 50, 100, 150 y 200 cm, medidos desde la cara frontal del sensor. En cada distancia se tomaron 10 lecturas válidas con:
  `uv run --project mcp_server python tools\analyze_accuracy.py --output docs\evidencias\RNF2\accuracy.txt`
- **Fecha:** 03/11/2026.

## Resultado

Rango de trabajo **20–200 cm**, error máximo **1.40 cm** → **PASS** (`accuracy.txt`). Entre 50 y 200 cm el error máximo fue de 1.2 cm.

## Observación sobre 10 cm

A 10 cm las 10 lecturas dieron 14.8 cm con una dispersión de solo 0.03 cm: el sensor quedó a unos 15 cm de la pared al pulsar Enter, un error de colocación y no del sensor (a 5 cm el error fue de 0.30 cm). No se corrigió el valor; como el rango de trabajo se calcula con distancias seguidas, se declara el que salió de la medición, 20–200 cm.
