# bot.py
import nextcord
from nextcord.ext import commands, tasks
from config import DISCORD_TOKEN
from tracking.tracker import check_active_games, save_channel_id
from tracking.accounts import MSI_PLAYERS
from riot.riot_api import get_ranked_data




intents = nextcord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)



def get_teams():
    return sorted(set(p["team"].lower() for p in MSI_PLAYERS if p["team"]))

async def get_rank_str(puuid: str) -> str:
    ranked_data = await get_ranked_data(puuid)
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
                rank = await get_rank_str(p["puuid"])
                lines.append(
                    f"**{p['name']}** ({p['riot_id']['game_name']}#{p['riot_id']['tag_line']}) - {rank}"
                )
            await ctx.send(f"**Jugadores de {team.upper()}:**\n" + "\n".join(lines))
        # Agrega el comando dinámicamente
        bot.command(name=team)(team_cmd)

add_team_commands(bot)















@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    check_games_loop.start()


@tasks.loop(seconds=60)
async def check_games_loop():
    await check_active_games(bot) # type: ignore


@bot.command()
async def setchannel(ctx):
    """Guarda este canal como el canal de notificaciones para este servidor."""
    guild_id = ctx.guild.id
    channel_id = ctx.channel.id
    from tracking.tracker import save_channel_id
    save_channel_id(guild_id, channel_id)
    await ctx.send(f"✅ Canal de notificaciones configurado para este servidor: {ctx.channel.mention}")