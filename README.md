# ThirdProject-IoT — Objeto inteligente con MQTT y MCP

**Grupo 1 — SIS-234**

- Ricardo Andres Andrade Vargas
- Dabner Eliezer Orozco Veizaga

Un ESP32 con un sensor HC-SR04 y tres LEDs publica la distancia en el broker público de HiveMQ. La app IoT MQTT Panel la grafica y controla los LEDs. Un servidor MCP en Python permite hacer lo mismo desde Claude Desktop en lenguaje natural. Todos los componentes se comunican solo a través del broker.

## Protocolo MQTT

Broker: `broker.hivemq.com:1883`. Las constantes están en `include/MqttConfig.h` y `mcp_server/config.py`.

| Tópico | Publica | Se suscribe | QoS | Retenido | Payload |
|---|---|---|---|---|---|
| `sis234/grupo1/distance` | OI | App, MCP | 0 | No | `{"seq":12,"cm":23.5}`; `{"seq":13,"cm":null}` si la lectura es inválida |
| `sis234/grupo1/leds/cmd` | App, MCP | OI | 1 | No | `{"led":"red","state":"on"}`; `led` ∈ red, yellow, white, all; `state` ∈ on, off; máx. 64 caracteres |
| `sis234/grupo1/leds/state` | OI | App, MCP | 0 | Sí | `{"red":1,"yellow":0,"white":0}` tras aplicar cada comando |
| `sis234/grupo1/status` | OI (LWT) | App, MCP | 1 | Sí | `online` / `offline` |

*(Pendiente: herramientas MCP, valores medidos de los RNF e instrucciones de ejecución.)*
