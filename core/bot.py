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
from ui.embeds import TEAM_TRICODES 
from utils.helpers import parse_ranked_data
import time
import asyncio
import subprocess
import json
import os



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

from core.commands import register_commands
register_commands(bot)



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



def add_team_commands(bot):
    teams = get_teams()
    for team in teams:
        async def team_cmd(ctx, team=team):
            loading_msg = await ctx.send("⏳ Calculando datos, por favor espera...")
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
            team_name = TEAM_TRICODES.get(team.upper(), team.upper())
            await loading_msg.edit(content=f"**Jugadores de {team.upper()} ({team_name}):**\n\n" + "\n".join(lines))
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
                    # filepath: d:\msi_tracker_bot\bot.py
                    embed, bat_path, files = await create_match_embed(active_game)
                    embed.title = f"Partida de {display_name}! 🎮"
                    all_files = files.copy()
                    if bat_path:
                        all_files.append(nextcord.File(bat_path, filename="spectate_lol.bat"))
                        await ctx.send(
                            content="⬇️ **Archivo para espectar la partida:**",
                            embed=embed,
                            files=all_files
                        )
                    else:
                        if files:
                            await ctx.send(embed=embed, files=files)
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
                        ranked_data_map = cache_entry.get("ranked_data_map")
                        embed, bat_path, files = await create_match_embed(
                            cache_entry["active_game"],
                            mostrar_tiempo=False,
                            mostrar_hora=True,
                            ranked_data_map=ranked_data_map
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
                        await ctx.send(f"❌ {display_name} no está en ninguna partida activa.")
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
    
    
    ACCOUNTS_PATH = os.path.join(os.path.dirname(__file__), "tracking", "accounts.json")
    
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















