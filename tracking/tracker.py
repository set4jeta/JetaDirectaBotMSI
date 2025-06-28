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

    # Para evitar anunciar dos veces la misma partida si hay varios MSI en la misma
    partidas_ya_checadas = set()
    
    
        # --- INICIO SISTEMA RETRY ---
    retry_queue = load_retry_queue()
    retry_puuids = set(r["puuid"] for r in retry_queue)
    new_retry_queue = []
    # --- FIN SISTEMA RETRY ---
    
    
    

    for guild_id_str, channel_id in channel_ids.items():
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"⚠️ No se encontró el canal configurado: {channel_id}")
            continue

        print(f"🔎 Comprobando partidas activas de MSI_PLAYERS para guild {guild_id_str}...")

        # --- INICIO: prioriza los de retry ---
        players_to_check = [p for p in MSI_PLAYERS if p.get("puuid") in retry_puuids] + \
                           [p for p in MSI_PLAYERS if p.get("puuid") not in retry_puuids]
        # --- FIN: prioriza los de retry ---

        for player in players_to_check:
            puuid = player.get("puuid")
            print(f"   → Revisando jugador: {player['name']} ({player['riot_id']['game_name']}#{player['riot_id']['tag_line']}) | PUUID: {puuid}")
            if not puuid:
                print(f"❌ No se encontró puuid para {player['name']}")
                continue

            # Quita la llamada directa a is_valid_puuid aquí

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
                else:
                    print(f"⚠️ Error al consultar partida activa para {player['name']} (status={status})")
                continue
            
            # FILTRO: Solo partidas relevantes
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
                            
            
            
            
            
            
            
            
            participants = active_game.get("participants", [])
            team_ids = {p["teamId"] for p in participants}
            if not (100 in team_ids and 200 in team_ids):
                print(f"⏩ Partida ignorada (solo un equipo): {active_game.get('gameId')}")
                continue

            game_id = active_game.get("gameId")
            if game_id in partidas_ya_checadas or game_id in announced_games:
                continue

            # Busca todos los MSI en esta partida
            msi_puuids = {p["puuid"] for p in active_game["participants"] if p["puuid"] in {p["puuid"] for p in MSI_PLAYERS}}
            if not msi_puuids:
                continue  # No hay MSI en esta partida

            partidas_ya_checadas.add(game_id)
            announced_games.add(game_id)
            print(f"   ✅ Anunciando partida {game_id} con MSI: {msi_puuids}")

            embed, bat_path = await create_match_embed(active_game, mostrar_tiempo=False, mostrar_hora=True)
            if bat_path:
                await channel.send(
                    content="⬇️ **Archivo para espectar la partida:**\nAdjunto encontrarás el archivo `spectate_lol.bat` personalizado para esta partida. Descárgalo y ejecútalo para espectar desde tu cliente de LoL.",
                    embed=embed,
                    file=nextcord.File(bat_path, filename="spectate_lol.bat")
                )
            else:
                await channel.send(embed=embed)
                
            

            # GUARDA EL CACHÉ PARA TODOS LOS MSI EN LA PARTIDA
            
            for msi_puuid in msi_puuids:
                set_active_game(msi_puuid, active_game)

    save_retry_queue(new_retry_queue)