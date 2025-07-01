# tracking/tracker.py
import asyncio
import json
import os
from riot.riot_api import get_active_game, is_valid_puuid
from ui.embeds import create_match_embed, QUEUE_ID_TO_NAME
from tracking.accounts import MSI_PLAYERS
from tracking.active_game_cache import set_active_game, ACTIVE_GAME_CACHE
from utils.spectate_bat import generar_bat_spectate
import nextcord
import time




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




last_checked_index = 0
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "notify_config.json")
RETRY_PATH = os.path.join(os.path.dirname(__file__), "puuid_retry_queue.json")
LAST_INDEX_PATH = os.path.join(os.path.dirname(__file__), "last_checked_index.json")
ANNOUNCED_GAMES_PATH = os.path.join(os.path.dirname(__file__), "announced_games.json")
announced_games = set()

# Utilidades para estado por canal

def load_per_channel_json(path, default_factory=dict):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                # MIGRACIÓN: si es una lista, conviértelo a dict vacío (solo para retry_queue)
                if isinstance(data, list):
                    print(f"[MIGRACIÓN] El archivo {path} estaba en formato lista, convirtiendo a dict vacío.")
                    return default_factory()
                return data
            except Exception:
                return default_factory()
    return default_factory()

def save_per_channel_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_retry_queue():
    if os.path.exists(RETRY_PATH):
        with open(RETRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_retry_queue(queue):
    with open(RETRY_PATH, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

def load_channel_ids():
    if not os.path.exists(CONFIG_PATH):
        return {}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_channel_id(guild_id: int, channel_id: int):
    data = load_channel_ids()
    data[str(guild_id)] = channel_id
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f)

async def check_active_games(bot):
    channel_ids = load_channel_ids()
    if not channel_ids:
        print("[INFO] No hay canales configurados para notificaciones.")
        return

    announced_games_map = load_per_channel_json(ANNOUNCED_GAMES_PATH, dict)
    embed_cache = {}  # game_id: (embed, bat_path)

    # --- RECORRIDO ESTRICTAMENTE SECUENCIAL, 1 POR 1, BLOQUEANTE EN 429 ---
    if os.path.exists(LAST_INDEX_PATH):
        with open(LAST_INDEX_PATH, "r", encoding="utf-8") as f:
            try:
                last_index_data = json.load(f)
                last_checked_index = last_index_data.get("last_checked_index", 0)
            except Exception:
                last_checked_index = 0
    else:
        last_checked_index = 0

    total_players = len(MSI_PLAYERS)
    i = last_checked_index
    while i < total_players:
        player = MSI_PLAYERS[i]
        puuid = player.get("puuid")
        if not puuid:
            print(f"[WARN] Jugador sin PUUID: {player}")
            i += 1
            continue
        while True:
            try:
                active_game, status = await get_active_game(puuid)
            except Exception as e:
                print(f"[ERROR] Excepción al consultar API para {player.get('name', puuid)}: {e}")
                await asyncio.sleep(4)
                continue  # Reintenta indefinidamente si hay error
            if status == 429:
                print(f"[RATE LIMIT] 429 para {player.get('name', puuid)}. Reintentando en 4 segundos...")
                await asyncio.sleep(4)
                continue  # Reintenta indefinidamente hasta que no sea 429
            break  # Sale del while True solo si NO es 429 ni error
        if not active_game:
            print(f"[NO GAME] {player.get('name', puuid)} no está en partida.")
            # Borra del caché si existe
            from tracking.active_game_cache import ACTIVE_GAME_CACHE
            if puuid in ACTIVE_GAME_CACHE:
                del ACTIVE_GAME_CACHE[puuid]
            i += 1
            continue
        if active_game.get("gameType") != "MATCHED":
            print(f"[SKIP] {player.get('name', puuid)}: gameType no es MATCHED.")
            i += 1
            continue
        if active_game.get("gameMode") != "CLASSIC":
            print(f"[SKIP] {player.get('name', puuid)}: gameMode no es CLASSIC.")
            i += 1
            continue
        if active_game.get("gameQueueConfigId") not in [400, 420, 430, 440]:
            print(f"[SKIP] {player.get('name', puuid)}: Queue {active_game.get('gameQueueConfigId')} no válida.")
            i += 1
            continue
        
        participants = active_game.get("participants", [])
        for part in participants:
            if part.get("puuid") in {p["puuid"] for p in MSI_PLAYERS}:
                set_active_game(part["puuid"], active_game)
                
        
        team_ids = {p["teamId"] for p in participants}
        if not (100 in team_ids and 200 in team_ids):
            print(f"[SKIP] {player.get('name', puuid)}: Equipos incompletos.")
            i += 1
            continue
        game_id = active_game.get("gameId")
        msi_puuids = {p["puuid"] for p in participants if p["puuid"] in {p["puuid"] for p in MSI_PLAYERS}}
        if not msi_puuids:
            print(f"[SKIP] {player.get('name', puuid)}: Ningún MSI PUUID en partida.")
            i += 1
            continue
        print(f"[IN GAME] {player.get('name', puuid)} está en partida válida (gameId={game_id}). Notificando canales...")
        for guild_id_str, channel_id in channel_ids.items():
            chan_map = announced_games_map.get(str(channel_id), {})
            if str(game_id) in chan_map:
                print(f"[SKIP] Ya se notificó gameId={game_id} en canal {channel_id}.")
                continue
            channel = bot.get_channel(channel_id)
            if not channel:
                print(f"[ERROR] Canal {channel_id} no encontrado en el bot.")
                continue
            if game_id not in embed_cache:
                try:
                    embed, bat_path, files = await create_match_embed(active_game, mostrar_tiempo=False, mostrar_hora=True)
                    embed_cache[game_id] = (embed, bat_path, files)
                except Exception as e:
                    print(f"[ERROR] No se pudo crear embed para gameId={game_id}: {e}")
                    continue
            else:
                embed, bat_path, files = embed_cache[game_id]
            try:
                if bat_path:
                    all_files = []
                    # Vuelve a crear los archivos de imagen para cada canal
                    if files:
                        for f in files:
                            all_files.append(nextcord.File(f.fp.name, filename=f.filename))
                    all_files.append(nextcord.File(bat_path, filename="spectate_lol.bat"))
                    await channel.send(
                        content="⬇️ **Archivo para espectar la partida:**",
                        embed=embed,
                        files=all_files
                    )
                else:
                    if files:
                        await channel.send(embed=embed, files=files)
                    else:
                        await channel.send(embed=embed)
                print(f"[NOTIFY] Notificación enviada a canal {channel_id} para gameId={game_id}.")
                chan_map = announced_games_map.setdefault(str(channel_id), {})
                chan_map[str(game_id)] = int(time.time())
                announced_games_map[str(channel_id)] = chan_map
            except Exception as e:
                print(f"[ERROR] Fallo al enviar notificación a canal {channel_id} para gameId={game_id}: {e}")
        i += 1
        await asyncio.sleep(0.5)  # Esperar un poco antes de la siguiente iteración
    # Guardar el índice para el próximo ciclo
    with open(LAST_INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump({"last_checked_index": i if i < total_players else 0}, f)
    
     # Limpia gameId viejos (más de 2 horas)
    now = int(time.time())
    EXPIRATION = 2 * 3600  # 2 horas en segundos

    for chan_id, games in announced_games_map.items():
        # Si es lista antigua, conviértela a dict
        if isinstance(games, list):
            games = {str(gid): now for gid in games}
        # Borra los gameId viejos
        announced_games_map[chan_id] = {gid: ts for gid, ts in games.items() if now - ts < EXPIRATION}
    
    
    limpiar_cache_partidas_viejas()
    save_per_channel_json(ANNOUNCED_GAMES_PATH, announced_games_map)
    print(f"[INFO] Ciclo de notificación completado. Próximo ciclo comenzará en el jugador {i if i < total_players else 0}.")