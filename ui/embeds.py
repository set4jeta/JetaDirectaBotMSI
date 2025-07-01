from typing import Tuple, Optional
import nextcord
import datetime
import pprint
from riot.riot_api import get_champion_name_by_id, get_ranked_data
from tracking.accounts import MSI_PLAYERS
from utils.spectate_bat import generar_bat_spectate
from datetime import datetime, timedelta
import os
import PIL.Image



PUUID_TO_PLAYER = {p["puuid"]: p for p in MSI_PLAYERS if "puuid" in p}

def is_msi_player(puuid: str) -> bool:
    return puuid in PUUID_TO_PLAYER

def get_player_display(puuid: str, riot_id: str = None, incluir_team_name: bool = True) -> str: # type: ignore
    player = PUUID_TO_PLAYER.get(puuid)
    if player:
        team = player.get("team", "")
        tricode = team.upper() if team else ""
        team_name = TEAM_TRICODES.get(tricode, team)
        name = player["name"]
        game_name = player["riot_id"]["game_name"]
        tag_line = player["riot_id"]["tag_line"]
        # Ejemplo: Rest [CFO] (Rest#1234) (CTBC Flying Oyster)
        if incluir_team_name:
            return f'**{name} [{tricode}]** ({game_name}#{tag_line}) ({team_name})'
        else:
            return f'**{name} [{tricode}]** ({game_name}#{tag_line})'
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


TEAM_TRICODES = {
    "FLY": "FlyQuest",
    "G2": "G2 Esports",
    "CFO": "CTBC Flying Oyster",
    "BLG": "Bilibili Gaming",
    "GENG": "Gen.G",
    "T1": "T1",
    "MKOI": "MOVISTAR KOI",
    "FUR": "FURIA",
    "GAM": "GAM Esports",
    "AL": "Anyone's Legend",
}







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
            player = PUUID_TO_PLAYER.get(puuid)
            if player:
                display = f"**{player['name']} ({riot_id})**"
            else:
                display = riot_id
            roles = get_possible_roles(champ_name, p["spell1Id"], p["spell2Id"])
            jugadores.append({
                "champ_name": champ_name,
                "spell1": p["spell1Id"],
                "spell2": p["spell2Id"],
                "display": display,
                "roles": roles,
                "role": None,
                "puuid": puuid
            })

    # 1. Asigna jungla por Smite
    junglers = [j for j in jugadores if 11 in (j["spell1"], j["spell2"])]
    if len(junglers) == 1:
        junglers[0]["role"] = "JUNGLE"

    # 2. Asigna roles únicos
    for rol in ROLE_ORDER:
        candidatos = [j for j in jugadores if j["role"] is None and j["roles"] == [rol]]
        if len(candidatos) == 1:
            candidatos[0]["role"] = rol

    # 3. Asigna el resto por exclusión
    for rol in ROLE_ORDER:
        if any(j["role"] == rol for j in jugadores):
            continue
        candidatos = [j for j in jugadores if j["role"] is None and rol in j["roles"]]
        if len(candidatos) == 1:
            candidatos[0]["role"] = rol

    # 4. Si queda alguien sin rol, asigna por orden de ROLE_ORDER
    sin_asignar = [j for j in jugadores if j["role"] is None]
    for j, rol in zip(sin_asignar, [r for r in ROLE_ORDER if not any(x["role"] == r for x in jugadores)]):
        j["role"] = rol

    # Ordena por ROLE_ORDER
    jugadores.sort(key=lambda x: ROLE_ORDER.index(x["role"]) if x["role"] in ROLE_ORDER else 99)
    return [f"{j['display']} ({j['champ_name']})" for j in jugadores]






async def create_match_embed(active_game: dict, mostrar_tiempo: bool = True, mostrar_hora: bool = True) -> tuple[nextcord.Embed, Optional[str], list]:
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
    displays = [get_player_display(p["puuid"], p.get("riotId", "Desconocido")) for p in msi_players_in_game]

    if not msi_players_in_game:
        title = "No hay jugadores MSI en esta partida."
    elif len(msi_players_in_game) == 1:
        player = PUUID_TO_PLAYER[msi_players_in_game[0]['puuid']]
        riot_id = player["riot_id"]
        name = player["name"]
        game_name = riot_id["game_name"]
        tag_line = riot_id["tag_line"]
        title = f"{name} ({game_name}#{tag_line}) está jugando! :loudspeaker:"
    elif len(msi_players_in_game) == 2:
        player1 = PUUID_TO_PLAYER[msi_players_in_game[0]['puuid']]
        player2 = PUUID_TO_PLAYER[msi_players_in_game[1]['puuid']]
        name1 = player1["name"]
        riot_id1 = player1["riot_id"]
        name2 = player2["name"]
        riot_id2 = player2["riot_id"]
        title = f"{name1} ({riot_id1['game_name']}#{riot_id1['tag_line']}) y {name2} ({riot_id2['game_name']}#{riot_id2['tag_line']}) están jugando! :loudspeaker:"
    else:
        def short_disp(p):
            player = PUUID_TO_PLAYER[p['puuid']]
            name = player["name"]
            riot_id = player["riot_id"]
            return f"{name} ({riot_id['game_name']}#{riot_id['tag_line']})"
        short_displays = [short_disp(p) for p in msi_players_in_game]
        title = f"{', '.join(short_displays[:-1])} y {short_displays[-1]} están jugando! :loudspeaker:"

    MAX_TITLE_LEN = 256
    if len(title) > MAX_TITLE_LEN:
        # Recorta y agrega "..."
        title = title[:MAX_TITLE_LEN - 3] + "..."



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
    equipo_line = ""
    if len(msi_players_in_game) == 1:
        player = PUUID_TO_PLAYER[msi_players_in_game[0]["puuid"]]
        team = player.get("team", "")
        tricode = team.upper() if team else ""
        team_name = TEAM_TRICODES.get(tricode, team)
        equipo_line = f"**Equipo:** {team_name}\n"   
    desc = f"{equipo_line}**Cola:** {queue_name}\n**Modo:** {game_mode}"
    
    delay_espectador = False
    if isinstance(game_start_time, int):
        now_ts = int(datetime.utcnow().timestamp())
        delay_espectador = (now_ts - int(game_start_time / 1000)) < 0
    
    
    if mostrar_tiempo:
        if delay_espectador:
            desc += f"\n**Tiempo transcurrido:** {tiempo_str} *(-3 min delay de espectador)*"
        else:
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
        player = PUUID_TO_PLAYER.get(puuid)
        name = player["name"] if player else "Desconocido"
        riot_id = player["riot_id"] if player else {}
        game_name = riot_id.get("game_name", "?")
        tag_line = riot_id.get("tag_line", "?")
        display = f"{game_name}#{tag_line}"
        # Recorta si es muy largo
        if len(display) > 22: #22
            display = display[:19] + "..."
        rank_str = await get_rank_str(puuid)
        champion_row.append(champ_name)
        account_row.append(display)
        rank_row.append(rank_str)

    if champion_row:
        # Tabla 1: Champion | Account
        table1_lines = [
            f"{'Champion':<10} | {'Account':<16}",
            "-" * 29
        ]
        for champ, acc in zip(champion_row, account_row):
            champ_txt = champ[:10]
            acc_txt = acc[:16]
            table1_lines.append(f"{champ_txt:<10} | {acc_txt:<16}")

        # Tabla 2: Rank (una línea por jugador, bonito)
        table2_lines = ["Rank 🏆"]
        table2_lines.append("-" * 16)
        for rank in rank_row:
            table2_lines.append(rank)

        # Añade ambas tablas como campos separados
        embed.add_field(
            name="Jugadores MSI",
            value="```\n" + "\n".join(table1_lines) + "\n```",
            inline=False
        )
        embed.add_field(
            name="",
            value="```\n" + "\n".join(table2_lines) + "\n```",
            inline=False
        )

        for line in table1_lines:
            print(f"[EMBED TABLE1] ({len(line)}): {line}")
        for line in table2_lines:
            print(f"[EMBED TABLE2] ({len(line)}): {line}")
    
    
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
       # embed.add_field(
       #     name="⚠️ Advertencia importante",
      #      value=(
      #              "Al ejecutar el archivo **spectate_lol.bat**, se reiniciará Riot Vanguard (anticheat). "
      #              "Para volver a jugar partidas normales de LoL o Valorant, "
      #              "**reinicia tu PC antes de abrir el cliente**.\n\n"
      #              "Si solo quieres espectar, no hay problema."
      #              "(OJO, sólo sirve para partidas que estén en vivo, partida terminada sólo mostrará el minuto final o nada)" 
      #      ),
       #     inline=False
     #   )
    else:
        embed.add_field(
            name="🔗 Espectar en directo",
            value="No disponible para esta partida.",
            inline=False
        )

    
    
    
    
        # === IMÁGENES DE JUGADOR Y EQUIPO (LOCALES) ===
    files = []
    if len(msi_players_in_game) == 1:
        player = msi_players_in_game[0]
        player_name = PUUID_TO_PLAYER[player["puuid"]]["name"]
        team = PUUID_TO_PLAYER[player["puuid"]].get("team", "")
        tricode = team.upper() if team else ""

        # Rutas locales
        player_img_path = os.path.join("assets", "players", f"{player_name}.webp")
        team_img_path = os.path.join("assets", "teams", f"{tricode}.png")

        # Adjunta thumbnail solo si la imagen existe y es válida
        if os.path.exists(player_img_path):
            try:
                with PIL.Image.open(player_img_path) as img:
                    print(f"[EMBED IMG] Player image {player_img_path}: {img.size}")
                files.append(nextcord.File(player_img_path, filename=f"{player_name}.webp"))
                embed.set_thumbnail(url=f"attachment://{player_name}.webp")
            except Exception as e:
                print(f"[EMBED IMG] Error al abrir {player_img_path}: {e}")

        # Adjunta imagen principal solo si la imagen existe y es válida
        if os.path.exists(team_img_path):
            try:
                with PIL.Image.open(team_img_path) as img:
                    print(f"[EMBED IMG] Team image {team_img_path}: {img.size}")
                files.append(nextcord.File(team_img_path, filename=f"{tricode}.png"))
                embed.set_image(url=f"attachment://{tricode}.png")
            except Exception as e:
                print(f"[EMBED IMG] Error al abrir {team_img_path}: {e}")
    elif len(msi_players_in_game) > 1:
        player = msi_players_in_game[0]
        team = PUUID_TO_PLAYER[player["puuid"]].get("team", "")
        tricode = team.upper() if team else ""
        team_img_path = os.path.join("assets", "teams", f"{tricode}.png")
        if os.path.exists(team_img_path):
            try:
                with PIL.Image.open(team_img_path) as img:
                    print(f"[EMBED IMG] Team image {team_img_path}: {img.size}")
                files.append(nextcord.File(team_img_path, filename=f"{tricode}.png"))
                embed.set_image(url=f"attachment://{tricode}.png")
            except Exception as e:
                print(f"[EMBED IMG] Error al abrir {team_img_path}: {e}")

    
    if hasattr(embed, '_image') and embed._image:
        print(f"[EMBED] set_image: {embed._image['url']}")
    else:
        print(f"[EMBED] set_image: None")
    if hasattr(embed, '_thumbnail') and embed._thumbnail:
        print(f"[EMBED] set_thumbnail: {embed._thumbnail['url']}")
    else:
        print(f"[EMBED] set_thumbnail: None")
    
    print(f"[EMBED DEBUG] Title ({len(embed.title or '')}): {embed.title}")
    print(f"[EMBED DEBUG] Description ({len(embed.description or '')}): {embed.description}")
    for i, field in enumerate(embed.fields):
        print(f"[EMBED DEBUG] Field {i} name ({len(field.name or '')}): {field.name}")
        print(f"[EMBED DEBUG] Field {i} value ({len(field.value or '')}): {field.value}")
        # Imprime la línea más larga de cada campo
        if field.value is not None and field.value.startswith("```"):
            max_line = max((len(line) for line in field.value.splitlines()), default=0)
            print(f"[EMBED DEBUG] Field {i} max line length: {max_line}")

    return embed, bat_path, files







   