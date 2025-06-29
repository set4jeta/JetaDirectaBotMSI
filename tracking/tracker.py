# tracking/tracker.py
import asyncio
import json
import os
from riot.riot_api import get_active_game, is_valid_puuid
from ui.embeds import create_match_embed, QUEUE_ID_TO_NAME
from tracking.accounts import MSI_PLAYERS
from tracking.active_game_cache import set_active_game
from utils.spectate_bat import generar_bat_spectate
import nextcord

last_checked_index = 0
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "notify_config.json")
RETRY_PATH = os.path.join(os.path.dirname(__file__), "puuid_retry_queue.json")
announced_games = set()

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
        print("⚠️ No hay canales de notificación configurados aún.")
        return

    global last_checked_index
    partidas_ya_checadas = set()
    retry_queue = load_retry_queue()
    retry_puuuids = set(r["puuid"] for r in retry_queue)
    new_retry_queue = []

    print(f"[CICLO] last_checked_index al inicio: {last_checked_index}")
    print(f"[CICLO] Total jugadores MSI: {len(MSI_PLAYERS)}")

    for guild_id_str, channel_id in channel_ids.items():
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"⚠️ No se encontró el canal configurado: {channel_id}")
            continue

        print(f"🔎 Comprobando partidas activas de MSI_PLAYERS para guild {guild_id_str}...")

        # 1. Si hay retry_queue, SOLO procesar esos jugadores (en orden)
        if retry_queue:
            print(f"[RETRY] Procesando {len(retry_queue)} jugadores en retry_queue...")
            for retry_item in retry_queue:
                puuid = retry_item["puuid"]
                player = next((p for p in MSI_PLAYERS if p.get("puuid") == puuid), None)
                if not player:
                    print(f"   → PUUID {puuid} de retry_queue no está en MSI_PLAYERS, saltando.")
                    continue
                print(f"   → Revisando jugador: {player['name']} ({player['riot_id']['game_name']}#{player['riot_id']['tag_line']}) | PUUID: {puuid} [RETRY QUEUE]")
                
                while True:
                    active_game, status = await get_active_game(puuid)
                    if status == 429:
                        print(f"⚠️ Rate limit (429) para {player['name']}, reintentando en 8s...")
                        await asyncio.sleep(8)
                        continue
                    break

                if active_game is None:
                    if status == 404:
                        if not await is_valid_puuid(puuid):
                            print(f"❌ PUUID inválido para {player['name']} ({player['riot_id']['game_name']}#{player['riot_id']['tag_line']}): {puuid}")
                        else:
                            print(f"   → {player['name']} NO está en partida activa.")
                    elif status == 429:
                        print(f"⚠️ Rate limit (429) para {player['name']}, agregando a retry_queue")
                        new_retry_queue.append({
                            "puuid": puuid,
                            "game_name": player["riot_id"]["game_name"],
                            "tag_line": player["riot_id"]["tag_line"]
                        })
                    else:
                        print(f"⚠️ Error al consultar partida activa para {player['name']} (status={status})")
                    continue

                # Resto de la lógica de verificación de partidas...
                game_type = active_game.get("gameType")
                game_mode = active_game.get("gameMode")
                queue_id = active_game.get("gameQueueConfigId")

                if game_type != "MATCHED":
                    print(f"⏩ Partida ignorada (gameType={game_type}) para {player['name']}")
                    continue
                if game_mode != "CLASSIC":
                    print(f"⏩ Partida ignorada (gameMode={game_mode}) para {player['name']}")
                    continue
                if queue_id not in [400, 420, 430, 440]:
                    if isinstance(queue_id, int):
                        cola = QUEUE_ID_TO_NAME.get(queue_id, f"Desconocida ({queue_id})")
                    else:
                        cola = "Desconocida (None)"
                    print(f"⏩ Partida ignorada (queueId={queue_id} - {cola}) para {player['name']}")
                    continue

                participants = active_game.get("participants", [])
                team_ids = {p["teamId"] for p in participants}
                if not (100 in team_ids and 200 in team_ids):
                    print(f"⏩ Partida ignorada (solo un equipo): {active_game.get('gameId')}")
                    continue

                game_id = active_game.get("gameId")
                if game_id in partidas_ya_checadas or game_id in announced_games:
                    continue

                msi_puuids = {p["puuid"] for p in active_game["participants"] if p["puuid"] in {p["puuid"] for p in MSI_PLAYERS}}
                if not msi_puuids:
                    continue

                partidas_ya_checadas.add(game_id)
                announced_games.add(game_id)
                print(f"   ✅ Anunciando partida {game_id} con MSI: {msi_puuids}")

                embed, bat_path = await create_match_embed(active_game, mostrar_tiempo=False, mostrar_hora=True)
                if bat_path:
                    await channel.send(
                        content="⬇️ **Archivo para espectar la partida:**",
                        embed=embed,
                        file=nextcord.File(bat_path, filename="spectate_lol.bat")
                    )
                else:
                    await channel.send(embed=embed)

                for msi_puuid in msi_puuids:
                    set_active_game(msi_puuid, active_game)

            # No avanzar el índice circular si hubo retry_queue
            print(f"[CICLO] Retry queue procesada. last_checked_index NO se mueve: {last_checked_index}")
        else:
            # 2. Si NO hay retry_queue, procesar ciclo circular completo
            n = len(MSI_PLAYERS)
            if n == 0:
                print("⚠️ No hay jugadores en MSI_PLAYERS.")
                continue
            print(f"[CIRCULAR] Procesando ciclo circular desde índice {last_checked_index}")
            indices = [(last_checked_index + i) % n for i in range(n)]
            rate_limited_this_cycle = False
            for offset, idx in enumerate(indices):
                player = MSI_PLAYERS[idx]
                puuid = player.get("puuid")
                print(f"   → Revisando jugador: {player['name']} ({player['riot_id']['game_name']}#{player['riot_id']['tag_line']}) | PUUID: {puuid} | idx_circular: {idx} (offset {offset})")
                
                active_game, status = await get_active_game(puuid)

                if active_game is None:
                    if status == 404:
                        if not await is_valid_puuid(puuid):
                            print(f"❌ PUUID inválido para {player['name']} ({player['riot_id']['game_name']}#{player['riot_id']['tag_line']}): {puuid}")
                        else:
                            print(f"   → {player['name']} NO está en partida activa.")
                    elif status == 429:
                        print(f"⚠️ Rate limit (429) para {player['name']}, agregando a retry_queue")
                        new_retry_queue.append({
                            "puuid": puuid,
                            "game_name": player["riot_id"]["game_name"],
                            "tag_line": player["riot_id"]["tag_line"]
                        })
                        rate_limited_this_cycle = True
                    else:
                        print(f"⚠️ Error al consultar partida activa para {player['name']} (status={status})")
                    continue

                # Resto de la lógica de verificación de partidas...
                game_type = active_game.get("gameType")
                game_mode = active_game.get("gameMode")
                queue_id = active_game.get("gameQueueConfigId")

                if game_type != "MATCHED":
                    print(f"⏩ Partida ignorada (gameType={game_type}) para {player['name']}")
                    continue
                if game_mode != "CLASSIC":
                    print(f"⏩ Partida ignorada (gameMode={game_mode}) para {player['name']}")
                    continue
                if queue_id not in [400, 420, 430, 440]:
                    if isinstance(queue_id, int):
                        cola = QUEUE_ID_TO_NAME.get(queue_id, f"Desconocida ({queue_id})")
                    else:
                        cola = "Desconocida (None)"
                    print(f"⏩ Partida ignorada (queueId={queue_id} - {cola}) para {player['name']}")
                    continue

                participants = active_game.get("participants", [])
                team_ids = {p["teamId"] for p in participants}
                if not (100 in team_ids and 200 in team_ids):
                    print(f"⏩ Partida ignorada (solo un equipo): {active_game.get('gameId')}")
                    continue

                game_id = active_game.get("gameId")
                if game_id in partidas_ya_checadas or game_id in announced_games:
                    continue

                msi_puuids = {p["puuid"] for p in active_game["participants"] if p["puuid"] in {p["puuid"] for p in MSI_PLAYERS}}
                if not msi_puuids:
                    continue

                partidas_ya_checadas.add(game_id)
                announced_games.add(game_id)
                print(f"   ✅ Anunciando partida {game_id} con MSI: {msi_puuids}")

                embed, bat_path = await create_match_embed(active_game, mostrar_tiempo=False, mostrar_hora=True)
                if bat_path:
                    await channel.send(
                        content="⬇️ **Archivo para espectar la partida:**",
                        embed=embed,
                        file=nextcord.File(bat_path, filename="spectate_lol.bat")
                    )
                else:
                    await channel.send(embed=embed)

                for msi_puuid in msi_puuids:
                    set_active_game(msi_puuid, active_game)

            if not rate_limited_this_cycle:
                last_checked_index = (last_checked_index + 1) % n
                print(f"[CICLO] last_checked_index actualizado para el próximo ciclo: {last_checked_index}")
            else:
                print(f"[CICLO] Hubo rate limit, last_checked_index NO se mueve: {last_checked_index}")

    save_retry_queue(new_retry_queue)