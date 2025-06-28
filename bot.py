# bot.py
import nextcord
import datetime 
from nextcord.ext import commands, tasks
from config import DISCORD_TOKEN
from tracking.tracker import check_active_games, save_channel_id
from tracking.active_game_cache import get_active_game_cache
from tracking.accounts import MSI_PLAYERS
from riot.riot_api import get_ranked_data, get_active_game, get_match_ids_by_puuid, get_match_by_id, is_live_from_dpm
from ui.embeds import create_match_embed
import time
import asyncio
import subprocess
import json
import os


HISTORIAL_CACHE_PATH = os.path.join("tracking", "historial_cache.json")

def load_historial_cache():
    if os.path.exists(HISTORIAL_CACHE_PATH):
        with open(HISTORIAL_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_historial_cache(cache):
    with open(HISTORIAL_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)










RANKED_CACHE = {}  # clave: puuid, valor: (timestamp, ranked_data)
CACHE_TTL = 120    # segundos que dura el caché (ajusta a gusto)




intents = nextcord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)



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

            max_retries = 2
            delay = 1  # segundos entre intentos

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
                if status == 429:
                    # Intenta usar el caché de la última partida anunciada
                    cache_entry = get_active_game_cache(puuid)
                    if cache_entry:
                        # Verifica si sigue en partida usando dpm.lol
                        sigue_en_partida = await is_live_from_dpm(puuid)
                        if sigue_en_partida:
                            # Calcula tiempo transcurrido desde la notificación
                            tiempo_transcurrido = int(time.time() - cache_entry["timestamp"])
                            # Crea embed usando el active_game del caché, pero sobreescribe el tiempo
                            embed, bat_path = await create_match_embed(
                                cache_entry["active_game"],
                                mostrar_tiempo=False,  # No muestres el tiempo real
                                mostrar_hora=True
                            )
                            # Agrega campo de tiempo estimado
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
                            return
                        else:
                            await ctx.send(f"❌ {display_name} no está en ninguna partida activa (según dpm.lol).")
                            return
                    else:
                        await ctx.send("⚠️ No se pudo consultar la partida activa por límite de peticiones de Riot y no hay datos de respaldo.")
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
    print(f"✅ Bot conectado como {bot.user}")
    
    check_games_loop.start()
    actualizar_accounts_json.start()
    actualizar_puuids.start()   


@tasks.loop(seconds=60)
async def check_games_loop():
    await check_active_games(bot) # type: ignore
    
    
@tasks.loop(minutes=20)
async def actualizar_accounts_json():
    print("🔄 Actualizando accounts.json desde dpm.lol…")
    # Ejecuta el script que actualiza accounts.json
    subprocess.run(["python", "-m", "tracking.update_accounts_from_leaderboard"], check=True)
    print("✅ accounts.json actualizado.")    


@tasks.loop(hours=1)
async def actualizar_puuids():
    await asyncio.sleep(3600)
    print("🔄 Actualizando PUUIDs de todos los jugadores…")
    import subprocess
    subprocess.run(["python", "-m", "tracking.update_puuids"], check=True)
    print("✅ PUUIDs actualizados.")



@bot.command()
async def setchannel(ctx):
    """Guarda este canal como el canal de notificaciones para este servidor."""
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    from tracking.tracker import save_channel_id
    save_channel_id(guild_id, channel_id)
    await ctx.send(f"✅ Canal de notificaciones configurado para este servidor: {ctx.channel.mention}")
    
    
    
    
@bot.command()
async def historial(ctx, *, nombre: str):
    import time
    nombre = nombre.strip().lower()
    player = next((p for p in MSI_PLAYERS if p["name"].lower() == nombre), None)
    if not player:
        await ctx.send(f"No se encontró el jugador '{nombre}'.")
        return
    puuid = player.get("puuid")
    if not puuid:
        await ctx.send(f"No hay PUUID para {player['name']}.")
        return

    cache = load_historial_cache()
    now = int(time.time())
    cache_entry = cache.get(puuid)
    # Si hay caché y no han pasado 15h, úsalo
    HISTORIAL_HORAS = 15
    
    if cache_entry and now - cache_entry["timestamp"] < HISTORIAL_HORAS * 3600:
        partidas = cache_entry["partidas"]
    else:
        match_ids = []  # <-- ¡Esta línea debe estar aquí!
        for queue_id in [420, 440]:
            ids = await get_match_ids_by_puuid(puuid, now - HISTORIAL_HORAS * 3600, now, queue=queue_id, count=20)
            match_ids.extend(ids)
        match_ids = list(dict.fromkeys(match_ids))
        print(f"[DEBUG] match_ids obtenidos para {player['name']}: {match_ids}")
        print(f"[DEBUG] Total match_ids: {len(match_ids)}")
        partidas = []
        POS_EMOJI = {
            "TOP": "🗻",
            "JUNGLE": "🌲",
            "MID": "✨",
            "ADC": "🏹",
            "BOTTOM": "🏹",
            "SUPPORT": "🛡️",
        }
        for match_id in match_ids:
            match = await get_match_by_id(match_id)
            if not match or "info" not in match:
                continue
            info = match["info"]
            duration = info.get("gameDuration", 0)
            mins = duration // 60
            part = next((p for p in info["participants"] if p["puuid"] == puuid), None)
            if not part:
                continue
            champ = part.get("championName", "???")
            kills = part.get("kills", 0)
            deaths = part.get("deaths", 0)
            assists = part.get("assists", 0)
            pos = part.get("teamPosition", "")
            if pos.upper() == "UTILITY":
                pos = "SUPPORT"
            pos_str = f" ({pos.title()})" if pos else ""
            emoji = POS_EMOJI.get(pos.upper(), "") if pos else ""
            start_ts = info.get("gameStartTimestamp")
            if isinstance(start_ts, int):
                dt = datetime.datetime.fromtimestamp(start_ts / 1000)
                hora_inicio_str = dt.strftime("%H:%M %d-%m-%Y")
            else:
                hora_inicio_str = "¿?"
            
            
            
            partidas.append(f"**{champ}**{pos_str} {emoji} | {kills}/{deaths}/{assists} | {mins} min | 🕒 {hora_inicio_str}")
        # Guarda en caché
        cache[puuid] = {"timestamp": now, "partidas": partidas}
        save_historial_cache(cache)

    if not partidas:
        await ctx.send(f"No se pudieron obtener los detalles de las partidas recientes de {player['name']}.")
        return

    riot_id = player.get("riot_id", {})
    game_name = riot_id.get("game_name", "")
    tag_line = riot_id.get("tag_line", "")
    nick_str = f"{player['name']} ({game_name}#{tag_line})" if game_name and tag_line else player['name']
    msg = f"**{nick_str}** últimas partidas 15h:\n\n"
    for i, linea in enumerate(partidas, 1):
        msg += f"{i}. {linea}\n"
    await ctx.send(msg)  