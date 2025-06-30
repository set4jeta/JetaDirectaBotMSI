# bot.py
import nextcord
from datetime import datetime, timezone
from nextcord.ext import commands, tasks
from config import DISCORD_TOKEN
from tracking.tracker import check_active_games, save_channel_id
from tracking.active_game_cache import get_active_game_cache, ACTIVE_GAME_CACHE
from tracking.accounts import MSI_PLAYERS, reload_msi_players
from tracking.update_accounts_from_leaderboard import fetch_leaderboard
from riot.riot_api import get_ranked_data, get_active_game, get_puuid_from_riot_id, get_is_live_and_updated_from_dpmlol, get_puuid_from_dpmlol, get_match_history_from_dpmlol, get_dpmlol_puuid
from ui.embeds import create_match_embed, get_player_display, get_champion_name_by_id
import time
import asyncio
import subprocess
import json
import os

def limpiar_cache_partidas_viejas():
    now = time.time()
    MAX_CACHE_AGE = 90 * 60  # 90 minutos en segundos
    to_delete = []
    for puuid, entry in list(ACTIVE_GAME_CACHE.items()):
        timestamp_guardado = entry["timestamp"]
        game_length = entry.get("game_length", 0) or 0
        tiempo_transcurrido = int(game_length + (now - timestamp_guardado))
        if tiempo_transcurrido > MAX_CACHE_AGE:
            to_delete.append(puuid)
    for puuid in to_delete:
        del ACTIVE_GAME_CACHE[puuid]






ACCOUNTS_PATH = os.path.join(os.path.dirname(__file__), "tracking", "accounts.json")

RANKING_CACHE_PATH = os.path.join("tracking", "ranking_cache.json")
RANKING_CACHE_TTL = 1800  # 30 minutos

def load_ranking_cache():
    if os.path.exists(RANKING_CACHE_PATH):
        with open(RANKING_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if time.time() - data.get("timestamp", 0) < RANKING_CACHE_TTL:
                return data["ranking"]
    return None

def save_ranking_cache(ranking):
    with open(RANKING_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"timestamp": time.time(), "ranking": ranking}, f, ensure_ascii=False, indent=2)






HISTORIAL_CACHE_PATH = os.path.join("tracking", "historial_cache.json")

def load_historial_cache():
    if os.path.exists(HISTORIAL_CACHE_PATH):
        with open(HISTORIAL_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_historial_cache(cache):
    with open(HISTORIAL_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


RETRY_PUUIDS = []
RETRY_WORKER_RUNNING = False

def add_to_retry_queue(puuid):
    if puuid not in RETRY_PUUIDS:
        RETRY_PUUIDS.append(puuid)
        # Si el worker no está corriendo, lánzalo
        if not RETRY_WORKER_RUNNING:
            asyncio.create_task(retry_worker())

async def retry_worker():
    global RETRY_WORKER_RUNNING
    RETRY_WORKER_RUNNING = True
    while RETRY_PUUIDS:
        puuid = RETRY_PUUIDS[0]
        while True:
            active_game, status = await get_active_game(puuid)
            if status == 200 and active_game:
                from tracking.active_game_cache import set_active_game
                set_active_game(puuid, active_game)
                break  # Sale del bucle interno, pasa al siguiente puuid
            elif status == 404:
                from tracking.active_game_cache import ACTIVE_GAME_CACHE
                if puuid in ACTIVE_GAME_CACHE:
                    del ACTIVE_GAME_CACHE[puuid]
                break  # Sale del bucle interno, pasa al siguiente puuid
            elif status != 429:
                break  # Sale del bucle interno, pasa al siguiente puuid
            await asyncio.sleep(2)  # Espera 2 segundos antes de reintentar si sigue en 429
        RETRY_PUUIDS.pop(0)
    RETRY_WORKER_RUNNING = False







RANKED_CACHE = {}  # clave: puuid, valor: (timestamp, ranked_data)
CACHE_TTL = 120    # segundos que dura el caché (ajusta a gusto)




intents = nextcord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)



def get_teams():
    return sorted(set(p["team"].lower() for p in MSI_PLAYERS if p["team"]))

async def get_rank_str(puuid: str, retries: int = 5, delay: float = 1.0) -> str:
    """
    Intenta obtener el ranked hasta 'retries' veces, esperando 'delay' segundos entre cada intento.
    Usa caché si está disponible y es válido.
    """
    for intento in range(retries):
        now = time.time()
        # Usa caché si es válido
        if puuid in RANKED_CACHE:
            ts, ranked_data = RANKED_CACHE[puuid]
            if now - ts < CACHE_TTL:
                result = parse_ranked_data(ranked_data)
                if result != "Sin datos de ranked":
                    return result
        # Si no hay caché válido, consulta la API
        ranked_data = await get_ranked_data(puuid)
        RANKED_CACHE[puuid] = (now, ranked_data)
        result = parse_ranked_data(ranked_data)
        if result != "Sin datos de ranked":
            return result
        if intento < retries - 1:
            await asyncio.sleep(delay)
    return "Sin datos de ranked"

def parse_ranked_data(ranked_data):
    if ranked_data is not None:
        if isinstance(ranked_data, list) and ranked_data:
            soloq = next((q for q in ranked_data if q["queueType"] == "RANKED_SOLO_5x5"), None)
            if soloq:
                tier = soloq["tier"].capitalize()
                rank = soloq["rank"]
                lp = soloq["leaguePoints"]
                return f"{tier} {rank} ({lp} LP)"
            else:
                return "Unranked"
        else:
            return "Unranked"
    else:
        return "Sin datos de ranked"

def add_team_commands(bot):
    teams = get_teams()
    for team in teams:
        async def team_cmd(ctx, team=team):
            players = [p for p in MSI_PLAYERS if p["team"].lower() == team]
            if not players:
                await ctx.send(f"No hay jugadores para el equipo '{team.upper()}'.")
                return
            lines = []
            for p in players:
                # Usa el rank del JSON si existe
                rank = None
                if "rank" in p and p["rank"]:
                    r = p["rank"]
                    # Formatea igual que el resto
                    if isinstance(r, dict) and "tier" in r and "rank" in r and "leaguePoints" in r:
                        rank = f"{r['tier'].capitalize()} {r['rank']} ({r['leaguePoints']} LP)"
                if not rank:
                    # Si no hay rank en el JSON, consulta la API
                    rank = await get_rank_str(p["puuid"])
                lines.append(
                    f"**{p['name']}** ({p['riot_id']['game_name']}#{p['riot_id']['tag_line']}) - {rank}"
                )
            await ctx.send(f"**Jugadores de {team.upper()}:**\n" + "\n".join(lines))
        # Agrega el comando dinámicamente
        bot.command(name=team)(team_cmd)

add_team_commands(bot)



def add_player_commands(bot):
    registered = set()

    def make_player_cmd(player, cmd_name, display_name):
        async def player_cmd(ctx):
            puuid = player.get("puuid")
            if not puuid:
                await ctx.send(f"No hay PUUID para {display_name}.")
                return

            max_retries = 8
            delay = 2  # segundos entre intentos

            for intento in range(max_retries):
                active_game, status = await get_active_game(puuid)
                if active_game:
                    embed, bat_path = await create_match_embed(active_game)
                    embed.title = f"Partida de {display_name}! 🎮"
                    if bat_path:
                        await ctx.send(
                            content=f"⬇️ Archivo para espectar la partida de {display_name}:",
                            embed=embed,
                            file=nextcord.File(bat_path, filename="spectate_lol.bat")
                        )
                    else:
                        await ctx.send(embed=embed)
                    return
                if status == 404:
                    await ctx.send(f"❌ {display_name} no está en ninguna partida activa.")
                    return
                if status == 429:
    # Usa el caché de la última partida anunciada si existe
                    cache_entry = get_active_game_cache(puuid)
                    if cache_entry:
                        now = time.time()
                        # Si tenemos game_length real, úsalo como base y suma el tiempo desde que se guardó
                        if cache_entry.get("game_length") is not None:
                            tiempo_transcurrido = cache_entry["game_length"] + int(now - cache_entry["timestamp"])
                        else:
                            tiempo_transcurrido = int(now - cache_entry["timestamp"])
                        embed, bat_path = await create_match_embed(
                            cache_entry["active_game"],
                            mostrar_tiempo=False,
                            mostrar_hora=True
                        )
                        mins, secs = divmod(tiempo_transcurrido, 60)
                        embed.add_field(
                            name="⏳ Tiempo estimado desde notificación",
                            value=f"{mins}m {secs}s (estimado, por rate limit)",
                            inline=False
                        )
                        embed.title = f"Partida de {display_name}! 🎮 (rate limit, datos estimados)"
                        if bat_path:
                            await ctx.send(
                                content=f"⬇️ Archivo para espectar la partida de {display_name}: (datos estimados por rate limit)",
                                embed=embed,
                                file=nextcord.File(bat_path, filename="spectate_lol.bat")
                            )
                        else:
                            await ctx.send(embed=embed)
                        # AGREGA A LA COLA DE REINTENTO DIFERIDO
                        add_to_retry_queue(puuid)
                        return
                    else:
                        await ctx.send("⚠️ No se pudo consultar la partida activa por límite de peticiones de Riot y no hay datos de respaldo.")
                        # AGREGA A LA COLA DE REINTENTO DIFERIDO IGUALMENTE
                        add_to_retry_queue(puuid)
                        return
                if intento < max_retries - 1:
                    await asyncio.sleep(delay)
            await ctx.send(f"❌ {display_name} no está en ninguna partida activa.")
        return player_cmd

    for player in MSI_PLAYERS:
        cmd_name = player["name"].lower().replace(" ", "")
        display_name = player["name"]
        if cmd_name in registered:
            continue  # Evita duplicados
        registered.add(cmd_name)
        bot.command(name=cmd_name)(make_player_cmd(player, cmd_name, display_name))

add_player_commands(bot)















@bot.event
async def on_ready():
    await bot.change_presence(activity=nextcord.Game(name="Escribe !help"))
    print(f"✅ Bot conectado como {bot.user}")

    if not check_games_loop.is_running():
        check_games_loop.start()
    if not actualizar_accounts_json.is_running():
        actualizar_accounts_json.start()
    if not actualizar_puuids_poco_a_poco.is_running():
        actualizar_puuids_poco_a_poco.start()


@bot.event
async def on_guild_join(guild):
    # Intenta enviar un mensaje al primer canal de texto disponible
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            await channel.send("¡Hola! Usa `!help` para ver la lista de comandos del bot.")
            break    
     


@tasks.loop(seconds=60)
async def check_games_loop():
    await check_active_games(bot) # type: ignore
    
    
@tasks.loop(hours=3)
async def actualizar_accounts_json():
    print("🔄 Actualizando accounts.json desde dpm.lol…")
    # Ejecuta el script que actualiza accounts.json
    subprocess.run(["python", "-m", "tracking.update_accounts_from_leaderboard"], check=True)
    print("✅ accounts.json actualizado.")
    reload_msi_players()  # <--- AGREGA ESTA LÍNEA
    print("✅ MSI_PLAYERS recargado en memoria.")    


@tasks.loop(seconds=60)
async def actualizar_puuids_poco_a_poco():
    # Guarda el índice actual en un archivo o variable global si quieres persistencia
    if not hasattr(actualizar_puuids_poco_a_poco, "i"):
        actualizar_puuids_poco_a_poco.i = 0
    i = actualizar_puuids_poco_a_poco.i # type: ignore

    if i >= len(MSI_PLAYERS):
        actualizar_puuids_poco_a_poco.i = 0 # type: ignore
        return

    player = MSI_PLAYERS[i]
    riot_id = player["riot_id"]
    game_name = riot_id["game_name"]
    tag_line = riot_id["tag_line"]
    print(f"🔄 Revisando PUUID para {player['name']} ({game_name}#{tag_line})...")
    # Primero intenta dpm.lol
    puuid_real = await get_puuid_from_dpmlol(game_name, tag_line)
    if not puuid_real:
        # Si dpm.lol falla, usa la API de Riot como respaldo
        puuid_real, status = await get_puuid_from_riot_id(game_name, tag_line)
    if puuid_real and puuid_real != player.get("puuid"):
        print(f"✅ PUUID actualizado para {player['name']}")
        player["puuid"] = puuid_real
        # Guarda el cambio
        with open(ACCOUNTS_PATH, "w", encoding="utf-8") as f:
            json.dump(MSI_PLAYERS, f, ensure_ascii=False, indent=2)
    else:
        print(f"PUUID sin cambios para {player['name']}")
    actualizar_puuids_poco_a_poco.i += 1 # type: ignore


















@bot.command()
@commands.has_permissions(administrator=True)
async def setchannel(ctx):
    """Guarda este canal como el canal de notificaciones para este servidor."""
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    from tracking.tracker import save_channel_id
    save_channel_id(guild_id, channel_id)
    await ctx.send(f"✅ Canal de notificaciones configurado para este servidor: {ctx.channel.mention}")
    
    
    
    
@bot.command()
@commands.has_permissions(administrator=True)
async def unsubscribe(ctx):
    """Quita el canal de notificaciones del servidor actual."""
    guild_id = str(ctx.guild.id)
    config_path = os.path.join(os.path.dirname(__file__), "tracking", "notify_config.json")
    if not os.path.exists(config_path):
        await ctx.send("No hay canales suscritos todavía.")
        return
    import json
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if guild_id in data:
        del data[guild_id]
        with open(config_path, "w", encoding="utf-8") as f2:
            json.dump(data, f2, ensure_ascii=False, indent=2)
        await ctx.send("✅ Canal de notificaciones eliminado para este servidor.")
    else:
        await ctx.send("Este servidor no tenía canal de notificaciones configurado.")
    
    
@bot.command()
async def historial(ctx, *, nombre: str):
    nombre = nombre.strip().lower()
    print(f"[HISTORIAL] Buscando jugador: '{nombre}'")
    players = [p for p in MSI_PLAYERS if p["name"].lower() == nombre]
    print(f"[HISTORIAL] Jugadores encontrados: {[p['name'] for p in players]}")
    if not players:
        await ctx.send(f"No se encontró el jugador '{nombre}'.")
        return
    for player in players:
        riot_id = player.get("riot_id", {})
        game_name = riot_id.get("game_name", "")
        tag_line = riot_id.get("tag_line", "")
        print(f"[HISTORIAL] Buscando dpmlol_puuid para {player['name']} ({game_name}#{tag_line})")
        dpmlol_puuid = await get_dpmlol_puuid(game_name, tag_line)
        print(f"[HISTORIAL] dpmlol_puuid para {player['name']}: {dpmlol_puuid}")
        if not dpmlol_puuid:
            await ctx.send(f"No se pudo obtener el historial para {player['name']} (no se encontró en dpm.lol).")
            continue

        print(f"[HISTORIAL] Consultando dpm.lol match-history para {player['name']} ({dpmlol_puuid})")
        data = await get_match_history_from_dpmlol(dpmlol_puuid)
        print(f"[HISTORIAL] Respuesta de dpm.lol para {player['name']}: OK, {len(data['matches']) if data and 'matches' in data else 0} matches")
        if not data or "matches" not in data or not data["matches"]:
            await ctx.send(f"No hay partidas recientes para {player['name']}.")
            continue

        partidas = []
        POS_EMOJI = {
            "TOP": "🗻",
            "JUNGLE": "🌲",
            "MID": "✨",
            "ADC": "🏹",
            "BOTTOM": "🏹",
            "SUPPORT": "🛡️",
        }
        for match in data["matches"][:10]:  # Solo las 10 más recientes
            # Busca el participante correcto
            participante = None
            for part in match.get("participants", []):
                if part.get("puuid") == dpmlol_puuid:
                    participante = part
                    break
            if not participante:
                continue  # No encontrado, salta

            champ = participante.get("championName", "???")
            kills = participante.get("kills", 0)
            deaths = participante.get("deaths", 0)
            assists = participante.get("assists", 0)
            win = participante.get("win", False)
            duration = match.get("gameDuration", 0)
            mins = duration // 60
            pos = participante.get("teamPosition", "") or participante.get("position", "")
            if pos.upper() == "UTILITY":
                pos = "SUPPORT"
            pos_str = f" ({pos.title()})" if pos else ""
            emoji = POS_EMOJI.get(pos.upper(), "") if pos else ""
            start_ts = match.get("gameCreation")
            if isinstance(start_ts, int):
                timestamp = int(start_ts / 1000)
                hora_inicio_str = f"<t:{timestamp}:f>"
            else:
                hora_inicio_str = "¿?"
            resultado = "✅" if win else "❌"
            partidas.append(f"{resultado} **{champ}**{pos_str} {emoji} | {kills}/{deaths}/{assists} | {mins} min | 🕒 {hora_inicio_str}")

        nick_str = f"{player['name']} ({game_name}#{tag_line})" if game_name and tag_line else player['name']

        msg = f"**{nick_str}** últimas partidas:\n\n"
        for i, linea in enumerate(partidas, 1):
            msg += f"{i}. {linea}\n"
        await ctx.send(msg)




@bot.command(name="help")
async def help_command(ctx):
    help_text = (
        "**Comandos disponibles:**\n"
        "`!help` - Muestra esta ayuda\n"
        "`!setchannel` - Configura este canal para notificaciones automáticas(solo admin)\n"
        "`!<equipo>` - Muestra los jugadores de un equipo (ej: `!g2`)\n"
        "`!live` - Muestra los jugadores MSI actualmente en partida (OJO puede tardar un poco)\n"
        "`!<nombrejugador>` - Muestra la partida activa de un jugador (ej: `!elk`)\n"
        "`!historial <jugador>` - Muestra las últimas partidas de un jugador MSI\n"
        "`!ranking` - Muestra la tabla de clasificación actual de los jugadores MSI\n"
        "`!unsubscribe` - Elimina el canal de notificaciones del servidor (solo admin)\n"

        "\n"
        "Las horas de inicio y partidas se muestran automáticamente en tu zona horaria local gracias a Discord.\n"
        "Si ves un mensaje de rate limit en los mensajes de partida, significa que Riot está limitando las peticiones (poca capacidad de respuesta).\n"
        "En ese caso, el bot usará los últimos datos de partida que tenga como respaldo (se actualiza en unos segundos en la mayoria de veces).\n"
        
    )
    await ctx.send(help_text)   


@bot.command()
async def live(ctx):
    """
    Muestra SOLO partidas MSI realmente en vivo.
    Usa caché <15min directamente.
    Para partidas >15min, consulta la API de Riot hasta 2 veces.
    Si da 429, consulta dpm.lol /players/search. Si isLive y actualizado hace <10min, usa el caché.
    """
    import time
    from datetime import datetime, timezone
    
     # Envía mensaje inicial para feedback al usuario
    loading_msg = await ctx.send("⏳ Calculando datos, por favor espera...")

    #print("\n[!LIVE] ===== INICIO DE COMANDO !LIVE =====")
    start_total = time.time()
    limpiar_cache_partidas_viejas()  # Limpia partidas viejas del caché

    now = time.time()
    vivos = []
    MAX_CACHE_AGE = 5 * 60  # 5 minutos en segundos
    MAX_DPM_AGE = 10 * 60     # 10 minutos en segundos

    for idx, player in enumerate(MSI_PLAYERS):
        #print(f"\n[!LIVE] Procesando jugador {idx+1}/{len(MSI_PLAYERS)}: {player['name']}")
        puuid = player.get("puuid")
        display_name = player["name"]
        riot_id = player.get("riot_id", {})
        game_name = riot_id.get("game_name", "")
        tag_line = riot_id.get("tag_line", "")
        if not puuid or not game_name or not tag_line:
            #print(f"[!LIVE]  -> Saltando: Faltan datos (puuid/game_name/tag_line)")
            continue

        updated_at_str = None
        cache_entry = ACTIVE_GAME_CACHE.get(puuid)
        cache_ok = False
        active_game = None

        if cache_entry and "active_game" in cache_entry:
            timestamp_guardado = cache_entry.get("timestamp", 0)
            game_length = cache_entry.get("game_length", 0) or 0
            tiempo_transcurrido = int(game_length + (now - timestamp_guardado))
            #print(f"[!LIVE]  -> Hay caché para {display_name}. Tiempo transcurrido: {tiempo_transcurrido}s")
            if tiempo_transcurrido < MAX_CACHE_AGE:
                # Si el caché es reciente (<5min), úsalo directamente
                cache_ok = True
                active_game = cache_entry["active_game"]
                #print(f"[!LIVE]  -> Usando caché reciente (<5min)")
            else:
                print(f"[!LIVE]  -> Caché viejo (>5min), se intentará API/dpm.lol")

        # Si el caché es viejo, consulta la API de Riot hasta 2 veces
        if not cache_ok and cache_entry and "active_game" in cache_entry:
            for intento in range(2):
               # print(f"[!LIVE]  -> Intento {intento+1} de API Riot para {display_name}")
                t0 = time.time()
                active_game, status = await get_active_game(puuid)
                #print(f"[!LIVE]    -> API status: {status}, t={time.time()-t0:.2f}s")
                if status == 200 and active_game:
                    from tracking.active_game_cache import set_active_game
                    set_active_game(puuid, active_game)
                    cache_ok = True
                    print(f"[!LIVE]    -> API OK, datos frescos. Se actualiza caché y se usa.")
                    break
                elif status == 429:
                   # print(f"[!LIVE]    -> API 429, esperando 2s y reintentando...")
                    await asyncio.sleep(2)
                    continue
                else:
                   # print(f"[!LIVE]    -> API no válida, status={status}.")
                    active_game = None
                    break
            # Si sigue sin datos frescos, consulta dpm.lol
            if not cache_ok:
               # print(f"[!LIVE]  -> Consultando dpm.lol para {display_name}")
                t1 = time.time()
                is_live, updated_at = await get_is_live_and_updated_from_dpmlol(game_name, tag_line)
               # print(f"[!LIVE]    -> dpm.lol isLive={is_live}, updated_at={updated_at}, t={time.time()-t1:.2f}s")
                updated_at_str = updated_at  # Guarda el string ISO para mostrarlo después
                if is_live and updated_at:
                    try:
                        dt_updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                        age = (datetime.now(timezone.utc) - dt_updated).total_seconds()
                       # print(f"[!LIVE]    -> dpm.lol age={age:.1f}s")
                        if age < MAX_DPM_AGE:
                            active_game = cache_entry["active_game"]
                            cache_ok = True
                            print(f"[!LIVE]    -> Usando caché por dpm.lol reciente (<10min)")
                        else:
                            print(f"[!LIVE]    -> dpm.lol muy viejo (>10min), no se usa")
                    except Exception as e:
                        print(f"[!LIVE]    -> Error parseando fecha dpm.lol: {e}")
                else:
                    print(f"[!LIVE]    -> dpm.lol no está en partida o sin fecha")

        if not cache_ok:
            print(f"[!LIVE]  -> No hay datos válidos para {display_name}, no se muestra.")
            continue  # No hay datos válidos

        # Si llegamos aquí, hay datos válidos y frescos
        champ_id = None
        participants = active_game.get("participants", []) if isinstance(active_game, dict) else []
        for part in participants:
            if part.get("puuid") == puuid:
                champ_id = part.get("championId")
                break
        champ_name = await get_champion_name_by_id(champ_id) if champ_id is not None else "?"
        game_length = active_game.get("gameLength", 0) if isinstance(active_game, dict) else 0
        mins, secs = divmod(game_length, 60)
        tiempo_str = f"{mins:02d}:{secs:02d}"
        cmd_name = display_name.lower().replace(" ", "")
        if updated_at_str:
            try:
                dt_updated = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                unix_ts = int(dt_updated.timestamp())
                hora_str = f"<t:{unix_ts}:T>"
            except Exception:
                hora_str = updated_at_str
            print(f"[!LIVE]  -> Mostrando {display_name} (dpm.lol hora: {hora_str})")
            vivos.append(f"**{display_name}** ({champ_name}) | {tiempo_str} en partida (`!{cmd_name}` para +info) | Última actualización: {hora_str}")
        else:
            print(f"[!LIVE]  -> Mostrando {display_name} (solo caché/API)")
            vivos.append(f"**{display_name}** ({champ_name}) | {tiempo_str} en partida (`!{cmd_name}` para +info)")

    print(f"\n[!LIVE] ===== FIN DE COMANDO !LIVE ===== (t_total={time.time()-start_total:.2f}s)\n")

    
    if not vivos:
        final_msg = "No hay jugadores MSI en partida en este momento.\n*(Algunas partidas pueden no estar actualizadas del todo, para más consistencia usa !<jugador>)*"
    else:
        final_msg = "**Jugadores MSI en partida ahora mismo:** (*Últimos 15 min aprox*)\n\n" + "\n".join(vivos)
        final_msg += "\n\n*(Algunas partidas pueden no estar actualizadas del todo, para más consistencia usa !<jugador>)*"

    # Edita el mensaje inicial con el resultado final
    await loading_msg.edit(content=final_msg)
        
        
@bot.command()
async def ranking(ctx):
    """
    Muestra el ranking MSI (caché 3h, fuente dpm.lol)
    """
    ranking = load_ranking_cache()
    if not ranking:
        players = fetch_leaderboard()
        # Ordena por leaderboardPosition si existe
        players.sort(key=lambda p: p.get("leaderboardPosition", 9999))
        ranking = []
        for p in players:
            name = p.get("displayName", p.get("gameName", "???"))
            team = p.get("team", "")
            lane = p.get("lane") or {}
            role = lane.get("value", "")
            rank_data = p.get("rank") or {}
            rank_tier = rank_data.get("tier", "")
            rank_div = rank_data.get("rank", "")
            rank = f"{rank_tier} {rank_div}".strip()
            lp = rank_data.get("leaguePoints", 0)
            wins = rank_data.get("wins", 0)
            losses = rank_data.get("losses", 0)
            winrate = f"{round(100 * wins / (wins + losses))}%" if (wins + losses) > 0 else "?"
            kda = f"{p.get('kda', '?')}"
            champs = p.get("championIds", [])
            # Convierte IDs a nombres de campeón
            champ_names = []
            from riot.champion_cache import CHAMPION_ID_TO_NAME
            for cid in champs[:3]:
                champ_names.append(CHAMPION_ID_TO_NAME.get(str(cid), str(cid)))
            champ_str = ", ".join(champ_names)
            ranking.append({
                "name": name,
                "team": team,
                "role": role,
                "rank": rank,
                "lp": lp,
                "winrate": winrate,
                "kda": kda,
                "champs": champ_str
            })
        save_ranking_cache(ranking)

    lines = [
        "Pos | Jugador | Equipo | Rol | Rango | LP | Winrate | KDA | Mejores campeones",
        "----|---------|--------|-----|-------|----|---------|-----|-------------------"
    ]
    for i, p in enumerate(ranking, 1):
        lines.append(
            f"{i:>2} | {p['name']} | {p['team']} | {p['role']} | {p['rank']} | {p['lp']} | {p['winrate']} | {p['kda']} | {p['champs']}"
        )

    # Divide en bloques de máximo 2000 caracteres (sin cortar líneas)
    current_chunk = "```markdown\n"
    for line in lines:
        if len(current_chunk) + len(line) + 1 > 1990:  # +1 por el salto de línea final
            current_chunk += "```"
            await ctx.send(current_chunk)
            current_chunk = "```markdown\n"
        current_chunk += line + "\n"

    if current_chunk.strip() != "```markdown":
        current_chunk += "```"
        await ctx.send(current_chunk)