# tracking/tracker.py
import asyncio
import json
import os
from riot.riot_api import get_active_game, is_valid_puuid
from ui.embeds import create_match_embed, QUEUE_ID_TO_NAME
from tracking.accounts import MSI_PLAYERS
from utils.spectate_bat import generar_bat_spectate
import nextcord 

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "notify_config.json")
announced_games = set()

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

    for guild_id_str, channel_id in channel_ids.items():
        channel = bot.get_channel(channel_id)
        if not channel:
            print(f"⚠️ No se encontró el canal configurado: {channel_id}")
            continue

        print(f"🔎 Comprobando partidas activas de MSI_PLAYERS para guild {guild_id_str}...")

        for player in MSI_PLAYERS:
            puuid = player.get("puuid")
            print(f"   → Revisando jugador: {player['name']} ({player['riot_id']['game_name']}#{player['riot_id']['tag_line']}) | PUUID: {puuid}")
            if not puuid:
                print(f"❌ No se encontró puuid para {player['name']}")
                continue

            if not await is_valid_puuid(puuid):
                print(f"❌ PUUID inválido para {player['name']} ({player['riot_id']['game_name']}#{player['riot_id']['tag_line']}): {puuid}")
                continue
            
            
            active_game = await get_active_game(puuid)
            if not active_game:
                print(f"   → {player['name']} NO está en partida activa.")
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

            embed, bat_path = await create_match_embed(active_game)
            if bat_path:
                await channel.send(
                    content="⬇️ **Archivo para espectar la partida:**\nAdjunto encontrarás el archivo `spectate_lol.bat` personalizado para esta partida. Descárgalo y ejecútalo para espectar desde tu cliente de LoL.",
                    embed=embed,
                    file=nextcord.File(bat_path, filename="spectate_lol.bat")
                )
            else:
                await channel.send(embed=embed)