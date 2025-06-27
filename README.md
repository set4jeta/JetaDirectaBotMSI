# 🧠 MSI Tracker Bot

Bot de Discord para **trackear en tiempo real las partidas de jugadores profesionales** de League of Legends (MSI, Worlds, LEC, LCS, etc.). Muestra información detallada de cada partida y permite espectarlas fácilmente desde el cliente.

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
   Usa comandos como `!g2`, `!mkoi`, etc., para ver los jugadores y rangos de cada equipo.

---

## 📦 Estructura del proyecto

```
msi_tracker_bot/
├── bot.py                          # Inicio y comandos del bot
├── main.py                         # Script principal
├── config.py                       # Variables de entorno (.env)
├── .gitignore                      # Archivos a ignorar por Git
├── requirements.txt                # Dependencias del proyecto
├── .env.example                    # Ejemplo de archivo de configuración
├── spectate_lol.bat                # Archivo generador para espectar partidas
├── riot/
│   ├── __init__.py
│   ├── riot_api.py                 # Funciones para consultar la API de Riot
│   ├── champion_cache.py           # Diccionario de campeones por ID
│   ├── champion_data_raw.json
│   └── res/
│       └── champion_data_raw_res.json
├── tracking/
│   ├── __init__.py
│   ├── tracker.py                  # Lógica de trackeo de partidas
│   ├── accounts.py                 # Manejo de jugadores MSI
│   ├── accounts.json               # Datos de jugadores
│   ├── update_accounts_from_leaderboard.py
│   └── update_puuids.py
├── ui/
│   ├── __init__.py
│   └── embeds.py                   # Generación de embeds
├── utils/
│   ├── logger.py
│   └── spectate_bat.py             # Generación del archivo .bat
└── README.md
```

---

## ⚙️ Instalación y configuración

1. **Clona el repositorio:**

```sh
git clone https://github.com/tu_usuario/msi-tracker-bot.git
cd msi-tracker-bot
```

2. **Instala las dependencias:**

```sh
pip install -r requirements.txt
```

3. **Configura las variables de entorno:**

Copia el archivo `.env.example` a `.env` y edítalo con tus claves:

```
RIOT_API_KEY=tu_api_key_de_riot
DISCORD_TOKEN=tu_token_de_discord
```

4. **Ejecuta el bot:**

```sh
python main.py
```

---

## 💬 Comandos útiles

| Comando         | Descripción                                         |
|-----------------|-----------------------------------------------------|
| `!setchannel`   | Define el canal actual como canal de notificaciones |
| `!<equipo>`     | Muestra los jugadores y rangos de un equipo (ej: `!g2`, `!mkoi`) |

---

## 🛡️ Seguridad

- El bot **nunca expone tus claves** ni sube datos sensibles.
- El archivo `.bat` solo automatiza la ejecución del cliente de LoL en modo espectador.

---

## 📄 Licencia

Este proyecto está bajo la licencia **MIT**.

---

## ✨ Créditos

Desarrollado por **set4**.  
Inspirado por la comunidad de esports y los bots de seguimiento de partidas profesionales.

> ¡Pull requests y sugerencias son bienvenidas!
