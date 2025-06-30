# 🧠 MSI Tracker Bot

Bot de Discord para **trackear en tiempo real las partidas de jugadores profesionales** de League of Legends (MSI Verison). Muestra información detallada de cada partida, permite espectarlas fácilmente desde el cliente y ofrece comandos útiles para la comunidad.

---

## 🚀 Funcionalidades principales

- **Detección automática de partidas activas** de jugadores configurados (`MSI_PLAYERS`).
- **Anuncios automáticos en Discord** con embed detallado:
  - Nombres de los jugadores MSI en partida.
  - Tipo de cola y modo de juego.
  - Tabla con campeón, cuenta y rango de cada jugador MSI.
  - Equipos completos ordenados por rol, con jugadores MSI destacados.
  - Opción para espectar la partida.
- **Archivo `spectate_lol.bat` personalizado** adjunto para espectar la partida con un solo clic (cliente de LoL cerrado).
- **Comandos personalizados por equipo** (`!g2`, `!mkoi`, etc.) para consultar cuentas y rangos.
- **Actualización automática** de la base de datos de jugadores desde un endpoint externo.
- **Soporte multi-servidor** y configuración por canal.
- **Historial de partidas** por jugador, incluso si tiene varias cuentas.
- **Soporte para cuentas múltiples por jugador** (muestra historial de todas las cuentas asociadas al nombre).
- **Gestión de rate limits** de Riot, con reintentos automáticos y mensajes claros.
- **Actualización automática de PUUIDs** y fusión de cuentas manuales/automáticas.

---

## 🛠️ ¿Cómo funciona?

1. **Actualización de jugadores:**  
   Al iniciar, el bot actualiza la lista de jugadores MSI desde un endpoint externo y corrige los PUUIDs.

2. **Trackeo de partidas:**  
   Cada minuto, revisa si algún jugador está en partida relevante (SoloQ, Flex, etc.).

3. **Anuncio en Discord:**  
   Si detecta una partida, genera un embed y adjunta el archivo `.bat` para espectar.

4. **Espectar partida:**  
   Solo debes ejecutar el `.bat` adjunto con el cliente de LoL cerrado, y entrarás en modo espectador directo.

5. **Comandos por equipo:**  
   Usa comandos como `!g2`, `!fly`, etc. para ver los jugadores y sus rangos.

6. **Historial de partidas:**  
   Usa `!historial <jugador>` para ver las últimas partidas de un jugador (soporta varias cuentas con el mismo nombre).

7. **Soporte multi-servidor:**  
   Puedes configurar el canal de anuncios en cada servidor con `!setchannel`.

---

## 📦 Requisitos y dependencias

- Python 3.10+
- Discord bot token (añádelo en un archivo `.env` como `DISCORD_TOKEN`)
- Riot API Key (añádelo en `.env` como `RIOT_API_KEY`)
- [requirements.txt](./requirements.txt):
  - nextcord
  - aiohttp
  - python-dotenv
  - cloudscraper
  - flask

Instala dependencias con:
```bash
pip install -r requirements.txt
```

---

## ⚙️ Instalación y despliegue

1. **Clona el repositorio:**
   ```bash
   git clone https://github.com/tuusuario/msi-tracker-bot.git
   cd msi-tracker-bot
   ```
2. **Crea un archivo `.env`** con tu token de Discord y tu Riot API Key:
   ```env
   DISCORD_TOKEN=tu_token_de_discord
   RIOT_API_KEY=tu_api_key_de_riot
   ```
3. **Instala las dependencias:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Ejecuta el bot:**
   ```bash
   python main.py
   ```

---

## 📝 Uso de comandos

- `!help` — Muestra la ayuda y comandos disponibles.
- `!setchannel` — Configura el canal actual para anuncios automáticos.
- `!<equipo>` — Muestra los jugadores de un equipo (ej: `!g2`, `!fly`).
- `!<nombrejugador>` — Muestra la partida activa de un jugador (ej: `!elk`).
- `!historial <jugador>` — Muestra las últimas partidas de un jugador MSI (si tiene varias cuentas, muestra todas).
- `!ranking` — Muestra la tabla de clasificación actual de los jugadores MSI.
- `!live` — Muestra los jugadores MSI actualmente en partida (según el caché).

---

## 👤 Uso para usuarios

- **Ver partidas activas:**  
  Simplemente escribe el nombre del jugador o el comando de equipo.
- **Ver historial:**  
  Usa `!historial <nombre>` para ver las últimas partidas de todas las cuentas asociadas a ese nombre.
- **Espectar partidas:**  
  Descarga y ejecuta el `.bat` adjunto al anuncio de partida (cierra el cliente de LoL antes).
- **Ver equipos y rangos:**  
  Usa los comandos de equipo para ver la plantilla y el rango de cada jugador.

---

## 🛡️ Seguridad y buenas prácticas

- **No compartas tu token de Discord ni tu Riot API Key.**
- El archivo `.env` **no debe subirse a GitHub** (está en `.gitignore`).
- El bot maneja rate limits de Riot automáticamente, pero si ves mensajes de rate limit, espera unos minutos.

---

## 🧩 Estructura del proyecto

```
msi_tracker_bot/
├── bot.py                # Lógica principal del bot y comandos
├── main.py               # Arranque y actualización de cuentas
├── config.py             # Carga de variables de entorno
├── requirements.txt      # Dependencias
├── README.md             # Este archivo
├── riot/                 # Lógica de integración con Riot API
├── tracking/             # Gestión de cuentas, cachés y ciclo de chequeo
├── ui/                   # Embeds y helpers visuales
├── utils/                # Utilidades varias (ej: generación de .bat)
└── ...
```

---

## 🧑‍💻 Desarrollo y contribución

- Puedes añadir nuevos comandos, equipos o mejorar la lógica de trackeo.
- Si quieres añadir más endpoints o modos de juego, revisa la carpeta `riot/`.
- Para añadir jugadores manualmente, edita `tracking/accounts.json`.
- Si encuentras bugs o tienes sugerencias, abre un issue o un pull request.

---

## ❓ Preguntas frecuentes

- **¿Por qué no aparecen partidas nuevas?**  
  Puede que el jugador no haya jugado en las últimas horas, o que Riot esté limitando las peticiones.
- **¿Por qué el .bat no funciona?**  
  Asegúrate de tener el cliente de LoL cerrado y la ruta correcta en el archivo.
- **¿Puedo usar el bot en varios servidores?**  
  Sí, cada servidor puede configurar su canal de anuncios.
- **¿Puedo añadir más equipos o jugadores?**  
  Sí, edita el archivo `accounts.json` y reinicia el bot.

---

## 📄 Licencia

Este proyecto es open source bajo licencia MIT. Puedes usarlo, modificarlo y compartirlo libremente.

---

## 💡 Créditos y agradecimientos

- Inspirado por la comunidad de LoL y los fans de los torneos internacionales.
- Gracias a Riot Games por la API y a todos los contribuidores del proyecto.

---

¡Disfruta trackeando partidas y espectando a los mejores jugadores del mundo!
