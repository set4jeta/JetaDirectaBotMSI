# bot.py
import nextcord
from nextcord.ext import commands, tasks
from config import DISCORD_TOKEN
from tracking.tracker import check_active_games, save_channel_id
from tracking.accounts import MSI_PLAYERS
from riot.riot_api import get_ranked_data, get_active_game
from ui.embeds import create_match_embed
import time
import asyncio
import subprocess


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
            active_game, status = await get_active_game(puuid)
            if not active_game:
                await ctx.send(f"❌ {display_name} no está en ninguna partida activa.")
                return
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