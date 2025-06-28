from typing import Tuple, Optional
import nextcord
import datetime
import pprint
from riot.riot_api import get_champion_name_by_id, get_ranked_data
from tracking.accounts import MSI_PLAYERS
from utils.spectate_bat import generar_bat_spectate

PUUID_TO_PLAYER = {p["puuid"]: p for p in MSI_PLAYERS if "puuid" in p}

def is_msi_player(puuid: str) -> bool:
    return puuid in PUUID_TO_PLAYER

def get_player_display(puuid: str, riot_id: str = None) -> str: # type: ignore
    player = PUUID_TO_PLAYER.get(puuid)
    if player:
        return f'**{player["name"]} ({player["riot_id"]["game_name"]}#{player["riot_id"]["tag_line"]})**'
    return riot_id or "Desconocido"

def get_player_name(puuid: str, riot_id: str = None) -> str: # type: ignore
    player = PUUID_TO_PLAYER.get(puuid)
    if player:
        return f'**{player["name"]}**'
    return riot_id or "Desconocido"

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

QUEUE_ID_TO_NAME: dict[int, str] = {
    400: "Normal Draft",
    420: "Clasificatoria Solo/Duo",
    430: "Normal Blind",
    440: "Clasificatoria Flex",
    450: "ARAM",
    700: "Clash",
    900: "URF",
    1700: "Arena",
    1300: "Nexus Blitz",
    1090: "TFT Normal",
    1100: "TFT Ranked",
    0: "Personalizada",
    830: "Tutorial",
    840: "Bots",
}




ROLE_ORDER = ["TOP", "JUNGLE", "MID", "ADC", "SUPPORT"]

CHAMPION_TO_ROLES = {
    "Aatrox": ["TOP"],
    "Ahri": ["MID"],
    "Akali": ["TOP", "MID"],
    "Akshan": ["MID", "ADC"],
    "Alistar": ["SUPPORT"],
    "Amumu": ["JUNGLE"],
    "Anivia": ["MID"],
    "Annie": ["MID", "SUPPORT"],
    "Aphelios": ["ADC"],
    "Ashe": ["ADC"],
    "Aurelion Sol": ["MID"],
    "Aurora": ["TOP", "MID"],
    "Azir": ["MID"],
    "Bard": ["SUPPORT"],
    "Bel'Veth": ["JUNGLE"],
    "Blitzcrank": ["SUPPORT"],
    "Brand": ["MID", "SUPPORT", "JUNGLE"],
    "Braum": ["SUPPORT", "TOP"],
    "Briar": ["JUNGLE", "TOP"],
    "Caitlyn": ["ADC"],
    "Camille": ["TOP"],
    "Cassiopeia": ["MID"],
    "Cho'Gath": ["TOP", "MID"],
    "Corki": ["MID", "ADC"],
    "Darius": ["TOP"],
    "Diana": ["MID", "JUNGLE"],
    "Dr. Mundo": ["TOP", "JUNGLE"],
    "Draven": ["ADC"],
    "Ekko": ["JUNGLE", "MID"],
    "Elise": ["JUNGLE"],
    "Evelynn": ["JUNGLE"],
    "Ezreal": ["ADC"],
    "Fiddlesticks": ["JUNGLE", "SUPPORT", "MID"],
    "Fiora": ["TOP"],
    "Fizz": ["MID", "TOP"],
    "Galio": ["MID", "SUPPORT", "TOP"],
    "Gangplank": ["TOP", "MID"],
    "Garen": ["TOP"],
    "Gnar": ["TOP"],
    "Gragas": ["TOP", "JUNGLE", "MID"], 
    "Graves": ["JUNGLE"],
    "Gwen": ["TOP"],
    "Hecarim": ["JUNGLE"],
    "Heimerdinger": ["MID", "TOP", "SUPPORT"],
    "Hwei": ["MID", "ADC"],  # flex pending clarificación
    "Illaoi": ["TOP"],
    "Irelia": ["TOP", "MID"],
    "Ivern": ["JUNGLE"],
    "Janna": ["SUPPORT"],
    "Jarvan IV": ["JUNGLE", "TOP"],
    "Jax": ["TOP", "JUNGLE"],
    "Jayce": ["TOP", "MID", "ADC"],
    "Jhin": ["ADC"],
    "Jinx": ["ADC"],
    "Kai'Sa": ["ADC"],
    "Kalista": ["ADC"],
    "Karma": [ "SUPPORT","TOP", "MID" ],
    "Karthus": ["JUNGLE", "MID"],
    "Kassadin": ["MID"],
    "Katarina": ["MID"],
    "Kayle": ["TOP", "MID"],
    "Kayn": ["JUNGLE"],
    "K'Sante": ["TOP"],
    "Kennen": ["TOP", "MID"],
    "Kha'Zix": ["JUNGLE"],
    "Kindred": ["JUNGLE"],
    "Kled": ["TOP"],
    "Kog'Maw": ["ADC"],
    "Leblanc": ["MID"],
    "Lee Sin": ["JUNGLE"],
    "Leona": ["SUPPORT"],
    "Lillia": ["JUNGLE"],
    "Lissandra": ["MID"],
    "Lucian": ["ADC"],
    "Lulu": ["SUPPORT"],
    "Lux": ["MID", "SUPPORT"],
    "Malphite": ["TOP", "JUNGLE"],
    "Malzahar": ["MID"],
    "Maokai": [ "JUNGLE", "TOP", "SUPPORT" ],
    "Master Yi": ["JUNGLE"],
    "Mel": ["MID", "SUPPORT"],  # champion #170, pero posterior a Ambessa :contentReference[oaicite:1]{index=1}
    "Milio": ["SUPPORT"],
    "Miss Fortune": ["ADC"],
    "Mordekaiser": ["TOP", "MID"],
    "Morgana": ["SUPPORT", "MID"],
    "Naafiri": ["JUNGLE"],
    "Nami": ["SUPPORT"],
    "Nasus": ["TOP"],
    "Nautilus": ["SUPPORT", "TOP"],
    "Neeko": [ "SUPPORT", "TOP", "MID" ],
    "Nilah": ["ADC"],
    "Nocturne": ["JUNGLE"],
    "Nunu & Willump": ["JUNGLE", "MID", "SUPPORT"],
    "Olaf": ["JUNGLE", "TOP"],
    "Orianna": ["MID"],
    "Ornn": ["TOP"],
    "Pantheon": ["JUNGLE", "TOP", "MID"],
    "Poppy": ["TOP", "JUNGLE", "SUPPORT"],
    "Pyke": ["SUPPORT", "JUNGLE"],
    "Qiyana": ["MID"],
    "Quinn": ["TOP"],
    "Rakan": ["SUPPORT"],
    "Rammus": ["JUNGLE"],
    "Renekton": ["TOP"],
    "Rell": ["SUPPORT", "TOP"],
    "Rengar": ["JUNGLE", "ADC"],
    "Riven": ["TOP"],
    "Rumble": ["TOP", "JUNGLE", "MID"],
    "Ryze": ["MID" , "TOP"],
    "Samira": ["ADC"],
    "Sejuani": ["JUNGLE"],
    "Senna": ["SUPPORT", "ADC"],
    "Seraphine": ["SUPPORT", "ADC", "MID"],
    "Sett": ["TOP", "JUNGLE"],
    "Shaco": ["JUNGLE"],
    "Shen": ["TOP", "SUPPORT"],
    "Shyvana": ["JUNGLE", "TOP"],
    "Singed": ["TOP"],
    "Sion": ["TOP"],
    "Sivir": ["ADC"],
    "Skarner": ["JUNGLE"],
    "Smolder": ["ADC", "MID"],
    "Sona": ["SUPPORT"],
    "Soraka": ["SUPPORT"],
    "Swain": ["SUPPORT", "MID", "TOP"],
    "Sylas": ["MID", "JUNGLE"],
    "Syndra": ["MID"],
    "Tahm Kench": ["SUPPORT", "TOP"],
    "Taliyah": ["MID", "JUNGLE"],
    "Talon": ["MID"],
    "Taric": ["SUPPORT", "TOP"],
    "Teemo": ["TOP", "JUNGLE", "MID"],
    "Thresh": ["SUPPORT"],
    "Tristana": ["ADC", "MID"],
    "Trundle": ["TOP", "JUNGLE"],
    "Tryndamere": ["TOP"],
    "Twisted Fate": ["MID", "JUNGLE"],
    "Twitch": ["ADC"],
    "Udyr": ["JUNGLE"],
    "Urgot": ["TOP"],
    "Varus": ["ADC"],
    "Vayne": ["ADC", "TOP"],
    "Veigar": ["MID", "SUPPORT"],
    "Vex": ["MID", "SUPPORT"],
    "Vi": ["JUNGLE", "TOP"],
    "Viego": ["JUNGLE"],
    "Viktor": ["MID"],
    "Vladimir": ["TOP", "MID"],
    "Volibear": ["JUNGLE", "TOP"],
    "Warwick": ["JUNGLE", "TOP"],
    "Wukong": ["TOP", "JUNGLE"],
    "Xayah": ["ADC"],
    "Xerath": ["MID"],
    "Xin Zhao": ["JUNGLE"],
    "Yasuo": ["MID", "TOP", "ADC"],
    "Yone": ["MID", "TOP", "ADC"],
    "Yuumi": ["SUPPORT"],
    "Zed": ["MID", "TOP"],
    "Zeri": ["ADC"],
    "Ziggs": ["MID"],
    "Zilean": ["SUPPORT", "MID", "TOP"],
    "Zoe": ["MID"],
    "Zyra": ["JUNGLE", "SUPPORT"],
    
    "Ambessa": ["TOP", "JUNGLE", "MID"],  # flex alta :contentReference[oaicite:2]{index=2}
}


def get_possible_roles(champ_name, spell1, spell2):
    # Si tiene Smite, es jungla sí o sí
    if spell1 == 11 or spell2 == 11:
        return ["JUNGLE"]
    return CHAMPION_TO_ROLES.get(champ_name, ["FILL"])

async def ordenar_equipo_por_rol(participants, team_id):
    jugadores = []
    for p in participants:
        if p["teamId"] == team_id:
            champ_name = await get_champion_name_by_id(p["championId"])
            riot_id = p.get("riotId", "Desconocido")
            puuid = p["puuid"]
            display = get_player_display(puuid, riot_id)
            roles = get_possible_roles(champ_name, p["spell1Id"], p["spell2Id"])
            jugadores.append({
                "champ_name": champ_name,
                "spell1": p["spell1Id"],
                "spell2": p["spell2Id"],
                "display": display,
                "roles": roles,
                "role": None
            })

    asignados = {}
    sin_asignar = jugadores[:]
    roles_disponibles = set(ROLE_ORDER)

    for rol in ROLE_ORDER:
        # Busca candidatos para este rol entre los que no tienen rol aún
        candidatos = [j for j in sin_asignar if rol in j["roles"]]
        if candidatos:
            # Elige el que tenga menos opciones (menos flexibilidad)
            candidato = min(candidatos, key=lambda j: len(j["roles"]))
            candidato["role"] = rol
            asignados[rol] = candidato
            sin_asignar.remove(candidato)
            roles_disponibles.remove(rol)

    # Si queda alguien sin rol, asigna FILL
    for j in sin_asignar:
        j["role"] = "FILL"

    # Ordena por ROLE_ORDER
    jugadores.sort(key=lambda x: ROLE_ORDER.index(x["role"]) if x["role"] in ROLE_ORDER else 99)
    return [f"{j['display']} ({j['champ_name']})" for j in jugadores]






async def create_match_embed(active_game: dict, mostrar_tiempo: bool = True, mostrar_hora: bool = True) -> tuple[nextcord.Embed, Optional[str]]:
    participants = active_game["participants"]
    
    #print("=== PARTICIPANTS DEBUG ===")
    #for p in participants:
       # print(
           # f"Summoner: {p.get('summonerName', '???')}, "
            #f"ChampionId: {p.get('championId')}, "
           # f"TeamId: {p.get('teamId')}, "
          #  f"PUUID: {p.get('puuid')}, "
          #  f"MSI: {is_msi_player(p.get('puuid'))}"
       # )
   # print("=========================")










    # MSI players en la partida
    msi_players_in_game = [p for p in participants if is_msi_player(p["puuid"])]
    names = [PUUID_TO_PLAYER[p["puuid"]]["name"] for p in msi_players_in_game if p["puuid"] in PUUID_TO_PLAYER]

    if not names:
        title = "No hay jugadores MSI en esta partida."
    elif len(names) == 1:
        title = f"{names[0]} está jugando! :loudspeaker:"
    elif len(names) == 2:
        title = f"{names[0]} y {names[1]} están jugando! :loudspeaker:"
    else:
        title = f"{', '.join(names[:-1])} y {names[-1]} están jugando! :loudspeaker:"

    queue_id = active_game.get("gameQueueConfigId")
    if isinstance(queue_id, int):
        queue_name = QUEUE_ID_TO_NAME.get(queue_id, f"Desconocida ({queue_id})")
    else:
        queue_name = "Desconocida (None)"
    game_mode = active_game.get("gameMode", "Desconocido")
    game_start_time = active_game.get("gameStartTime")
    game_length = active_game.get("gameLength")

    # Formatea el tiempo transcurrido
    if isinstance(game_length, int):
        mins, secs = divmod(game_length, 60)
        tiempo_str = f"{mins}m {secs}s"
    else:
        tiempo_str = "Desconocido"

    # Formatea la hora de inicio
    if isinstance(game_start_time, int):
        timestamp = int(game_start_time / 1000)
        hora_inicio_str = f"<t:{timestamp}:T>"
        fecha_inicio_str = f"<t:{timestamp}:F>"
    else:
        hora_inicio_str = "Desconocida"
        fecha_inicio_str = "Desconocida"

    desc = f"**Cola:** {queue_name}\n**Modo:** {game_mode}"
    if mostrar_tiempo:
        desc += f"\n**Tiempo transcurrido:** {tiempo_str}"
    if mostrar_hora:
        desc += f"\n**Hora de inicio:** {fecha_inicio_str}"

    embed = nextcord.Embed(
        title=title,
        description=desc,
        color=nextcord.Color.red()
    )

    # Tabla horizontal: Champion | Account | Rank (solo MSI)
    champion_row = []
    account_row = []
    rank_row = []

    for p in msi_players_in_game:
        puuid = p["puuid"]
        champ_id = p["championId"]
        champ_name = await get_champion_name_by_id(champ_id)
        riot_id = p.get("riotId", "Desconocido")
        display = get_player_display(puuid, riot_id)
        rank_str = await get_rank_str(puuid)
        champion_row.append(f"**{champ_name}**")
        account_row.append(display)
        rank_row.append(rank_str)

    if champion_row:
        table_lines = ["Champion | Account | Rank", "--------------------------"]
        for champ, acc, rank in zip(champion_row, account_row, rank_row):
            table_lines.append(f"{champ} | {acc} | {rank}")
        embed.add_field(
            name="Jugadores MSI",
            value=f"```\n" + "\n".join(table_lines) + "\n```",
            inline=False
        ) 

    
    
    
    # Equipos: ordena por rol dentro de cada equipo y muestra MSI en negrita
    blue_team = await ordenar_equipo_por_rol(participants, 100)
    red_team = await ordenar_equipo_por_rol(participants, 200)

    embed.add_field(
        name="🔵 Blue Team",
        value="\n".join(blue_team) if blue_team else "Ningún jugador del MSI en el equipo.",
        inline=False
    )
    embed.add_field(
        name="🔴 Red Team",
        value="\n".join(red_team) if red_team else "Ningún jugador del MSI en el equipo.",
        inline=False
    )

    # === BLOQUE PARA ESPECTAR LA PARTIDA ===
    game_id = active_game.get("gameId")
    platform_id = active_game.get("platformId")
    encryption_key = active_game.get("observers", {}).get("encryptionKey")

    bat_path = None
    if game_id and platform_id and encryption_key:
        # Genera el .bat y solo muestra el mensaje de descarga
        bat_path = generar_bat_spectate(
            server=f"spectator.{platform_id.lower()}.lol.pvp.net:8080",
            key=encryption_key,
            match_id=game_id,
            region=platform_id
        )
        embed.add_field(
            name="🔗 Espectar en directo",
            value="Descarga y ejecuta el archivo **spectate_lol.bat** adjunto arriba para espectar la partida desde tu cliente. (Debes tener el cliente de LoL cerrado)",
            inline=False
        )
        embed.add_field(
            name="⚠️ Advertencia importante",
            value=(
                    "Al ejecutar el archivo **spectate_lol.bat**, se reiniciará Riot Vanguard (anticheat). "
                    "Para volver a jugar partidas normales de LoL o Valorant, "
                    "**reinicia tu PC antes de abrir el cliente**.\n\n"
                    "Si solo quieres espectar, no hay problema."
                    "(OJO, sólo sirve para partidas que estén en vivo, partida terminada sólo mostrará el minuto final)" 
            ),
            inline=False
        )
    else:
        embed.add_field(
            name="🔗 Espectar en directo",
            value="No disponible para esta partida.",
            inline=False
        )

    return embed, bat_path







   