import os
import time
import json
import asyncio
import subprocess
from datetime import datetime, timezone

import nextcord
from nextcord.ext import commands

# Importa el objeto bot principal
from core.bot import bot

# Funciones y constantes de tu proyecto
from tracking.active_game_cache import get_active_game_cache, ACTIVE_GAME_CACHE
from tracking.accounts import MSI_PLAYERS, reload_msi_players
from tracking.update_accounts_from_leaderboard import fetch_leaderboard
from riot.riot_api import (
    get_ranked_data,
    get_active_game,
    get_puuid_from_riot_id,
    get_is_live_and_updated_from_dpmlol,
    get_puuid_from_dpmlol,
    get_match_history_from_dpmlol,
    get_dpmlol_puuid,
)
from ui.embeds import (
    create_match_embed,
    get_player_display,
    get_champion_name_by_id,
    TEAM_TRICODES,
)
from utils.cache_utils import (
    limpiar_cache_partidas_viejas,
    load_ranking_cache,
    save_ranking_cache,
    load_historial_cache,
    save_historial_cache,
)

def register_commands(bot):

    @bot.command()
    @commands.has_permissions(administrator=True)
    async def setchannel(ctx):
        """Guarda este canal como el canal de notificaciones para este servidor."""
        guild_id = ctx.guild.id
        channel_id = ctx.channel.id
        from tracking.tracker import save_channel_id
        save_channel_id(guild_id, channel_id)
        await ctx.send(f"✅ Canal de notificaciones configurado para este servidor: {ctx.channel.mention}")
        
        
        
        
    @bot.command()
    @commands.has_permissions(administrator=True)
    async def unsubscribe(ctx):
        """Quita el canal de notificaciones del servidor actual."""
        guild_id = str(ctx.guild.id)
        config_path = os.path.join(os.path.dirname(__file__), "tracking", "notify_config.json")
        if not os.path.exists(config_path):
            await ctx.send("No hay canales suscritos todavía.")
            return
        import json
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if guild_id in data:
            del data[guild_id]
            with open(config_path, "w", encoding="utf-8") as f2:
                json.dump(data, f2, ensure_ascii=False, indent=2)
            await ctx.send("✅ Canal de notificaciones eliminado para este servidor.")
        else:
            await ctx.send("Este servidor no tenía canal de notificaciones configurado.")
        
        
    @bot.command()
    async def historial(ctx, *, nombre: str = None): # type: ignore
        nombre = (nombre or "").strip().lower() if nombre else None # type: ignore
        loading_msg = await ctx.send("⏳ Calculando datos, por favor espera...")
        
        
        if not nombre:
                partidas_globales = []

                async def fetch_player_matches(player):
                    riot_id = player.get("riot_id", {})
                    game_name = riot_id.get("game_name", "")
                    tag_line = riot_id.get("tag_line", "")
                    dpmlol_puuid = await get_dpmlol_puuid(game_name, tag_line)
                    if not dpmlol_puuid:
                        return []
                    data = await get_match_history_from_dpmlol(dpmlol_puuid)
                    if not data or "matches" not in data or not data["matches"]:
                        return []
                    result = []
                    for match in data["matches"]:
                        participante = None
                        for part in match.get("participants", []):
                            if part.get("puuid") == dpmlol_puuid:
                                participante = part
                                break
                        if not participante:
                            continue
                        result.append({
                            "player": player,
                            "participante": participante,
                            "match": match
                        })
                    return result

                # Lanza todas las tareas en paralelo
                tasks = [fetch_player_matches(player) for player in MSI_PLAYERS]
                all_results = await asyncio.gather(*tasks)

                # Junta todos los resultados en una sola lista
                for result in all_results:
                    partidas_globales.extend(result)
                # 2. Ordena todas las partidas por fecha (gameCreation)
                partidas_globales.sort(key=lambda x: x["match"].get("gameCreation", 0), reverse=True)
                # 3. Toma las 10 más recientes
                partidas_top10 = partidas_globales[:10]
                # 4. Arma el mensaje
                POS_EMOJI = {
                    "TOP": "🗻",
                    "JUNGLE": "🌲",
                    "MID": "✨",
                    "ADC": "🏹",
                    "BOTTOM": "🏹",
                    "SUPPORT": "🛡️",
                }
                msg = "**Últimas 10 partidas MSI (todos los jugadores):**\n\n"
                for i, partida in enumerate(partidas_top10, 1):
                    player = partida["player"]
                    participante = partida["participante"]
                    match = partida["match"]
                    champ = participante.get("championName", "???")
                    kills = participante.get("kills", 0)
                    deaths = participante.get("deaths", 0)
                    assists = participante.get("assists", 0)
                    win = participante.get("win", False)
                    duration = match.get("gameDuration", 0)
                    mins = duration // 60
                    pos = participante.get("teamPosition", "") or participante.get("position", "")
                    if pos.upper() == "UTILITY":
                        pos = "SUPPORT"
                    pos_str = f" ({pos.title()})" if pos else ""
                    emoji = POS_EMOJI.get(pos.upper(), "") if pos else ""
                    start_ts = match.get("gameCreation")
                    if isinstance(start_ts, int):
                        timestamp = int(start_ts / 1000)
                        hora_inicio_str = f"<t:{timestamp}:f>"
                    else:
                        hora_inicio_str = "¿?"
                    resultado = "✅" if win else "❌"
                    riot_id = player.get("riot_id", {})
                    game_name = riot_id.get("game_name", "")
                    tag_line = riot_id.get("tag_line", "")
                    nick_str = f"{player['name']} ({game_name}#{tag_line})"
                    msg += f"{i}. {resultado} **{champ}**{pos_str} {emoji} | {kills}/{deaths}/{assists} | {mins} min | 🕒 {hora_inicio_str} | {nick_str}\n"
                await loading_msg.edit(content=msg)
                return

        
        if  nombre:
            print(f"[HISTORIAL] Buscando jugador: '{nombre}'")
            players = [p for p in MSI_PLAYERS if p["name"].lower() == nombre]
            print(f"[HISTORIAL] Jugadores encontrados: {[p['name'] for p in players]}")
            if not players:
                await ctx.send(f"No se encontró el jugador '{nombre}'.")
                return
            msgs = []
            for player in players:
                riot_id = player.get("riot_id", {})
                game_name = riot_id.get("game_name", "")
                tag_line = riot_id.get("tag_line", "")
                print(f"[HISTORIAL] Buscando dpmlol_puuid para {player['name']} ({game_name}#{tag_line})")
                dpmlol_puuid = await get_dpmlol_puuid(game_name, tag_line)
                print(f"[HISTORIAL] dpmlol_puuid para {player['name']}: {dpmlol_puuid}")
                if not dpmlol_puuid:
                    await ctx.send(f"No se pudo obtener el historial para {player['name']} (no se encontró en dpm.lol).")
                    continue

                print(f"[HISTORIAL] Consultando dpm.lol match-history para {player['name']} ({dpmlol_puuid})")
                data = await get_match_history_from_dpmlol(dpmlol_puuid)
                print(f"[HISTORIAL] Respuesta de dpm.lol para {player['name']}: OK, {len(data['matches']) if data and 'matches' in data else 0} matches")
                if not data or "matches" not in data or not data["matches"]:
                    await ctx.send(f"No hay partidas recientes para {player['name']}.")
                    continue

                partidas = []
                POS_EMOJI = {
                    "TOP": "🗻",
                    "JUNGLE": "🌲",
                    "MID": "✨",
                    "ADC": "🏹",
                    "BOTTOM": "🏹",
                    "SUPPORT": "🛡️",
                }
                for match in data["matches"][:10]:  # Solo las 10 más recientes
                    # Busca el participante correcto
                    participante = None
                    for part in match.get("participants", []):
                        if part.get("puuid") == dpmlol_puuid:
                            participante = part
                            break
                    if not participante:
                        continue  # No encontrado, salta

                    champ = participante.get("championName", "???")
                    kills = participante.get("kills", 0)
                    deaths = participante.get("deaths", 0)
                    assists = participante.get("assists", 0)
                    win = participante.get("win", False)
                    duration = match.get("gameDuration", 0)
                    mins = duration // 60
                    pos = participante.get("teamPosition", "") or participante.get("position", "")
                    if pos.upper() == "UTILITY":
                        pos = "SUPPORT"
                    pos_str = f" ({pos.title()})" if pos else ""
                    emoji = POS_EMOJI.get(pos.upper(), "") if pos else ""
                    start_ts = match.get("gameCreation")
                    if isinstance(start_ts, int):
                        timestamp = int(start_ts / 1000)
                        hora_inicio_str = f"<t:{timestamp}:f>"
                    else:
                        hora_inicio_str = "¿?"
                    resultado = "✅" if win else "❌"
                    partidas.append(f"{resultado} **{champ}**{pos_str} {emoji} | {kills}/{deaths}/{assists} | {mins} min | 🕒 {hora_inicio_str}")

                team = player.get("team", "")
                tricode = team.upper() if team else ""
                team_name = TEAM_TRICODES.get(tricode, team)
                nick_str = f"{player['name']} [{tricode}] ({game_name}#{tag_line})" if game_name and tag_line else player['name']

                msg = f"**{nick_str}** últimas partidas:\n\n"
                for i, linea in enumerate(partidas, 1):
                    msg += f"{i}. {linea}\n"
                msgs.append(msg)
            if msgs:
                await loading_msg.edit(content="\n\n".join(msgs))
            else:
                await loading_msg.edit(content="No se encontró historial para ese jugador.")
               
        
        
        
        
        
        
        
        
        


    @bot.command(name="help")
    async def help_command(ctx):
        help_text = (
            "**Comandos disponibles:**\n"
            "`!help` - Muestra esta ayuda\n"
            "`!setchannel` - Configura este canal para notificaciones automáticas(solo admin)\n"
            "`!<equipo>` - Muestra los jugadores de un equipo (ej: `!g2`)\n"
            "`!live` - Muestra los jugadores MSI actualmente en partida (OJO puede tardar un poco)\n"
            "`!info <jugador>` - Muestra información acerca de un Pro player de NA o uno presente en el MSI (ej: `!info spica`)\n"
            "`!<nombrejugador>` - Muestra la partida activa de un jugador (ej: `!elk`)\n"
            "`!historial` - Muestra las últimas partidas de todos los jugadores MSI\n"
            "`!historial <jugador>` - Muestra las últimas partidas de un jugador MSI\n"
            "`!ranking` - Muestra la tabla de clasificación actual de los jugadores MSI\n"
            "`!unsubscribe` - Elimina el canal de notificaciones del servidor (solo admin)\n"

            "\n"
            "Las horas de inicio y partidas se muestran automáticamente en tu zona horaria local gracias a Discord.\n"
            "Si ves un mensaje de rate limit en los mensajes de partida, significa que Riot está limitando las peticiones (poca capacidad de respuesta).\n"
            "En ese caso, el bot usará los últimos datos de partida que tenga como respaldo (se actualiza en unos segundos en la mayoria de veces).\n"
            
        )
        await ctx.send(help_text)   


    @bot.command()
    async def live(ctx):
        """
        Muestra SOLO partidas MSI realmente en vivo.
        Usa caché <15min directamente.
        Para partidas >15min, consulta la API de Riot hasta 2 veces.
        Si da 429, consulta dpm.lol /players/search. Si isLive y actualizado hace <10min, usa el caché.
        """
        import time
        from datetime import datetime, timezone
        
        # Envía mensaje inicial para feedback al usuario
        loading_msg = await ctx.send("⏳ Calculando datos, por favor espera...")

        #print("\n[!LIVE] ===== INICIO DE COMANDO !LIVE =====")
        start_total = time.time()
        limpiar_cache_partidas_viejas()  # Limpia partidas viejas del caché

        now = time.time()
        vivos = []
        MAX_CACHE_AGE = 5 * 60  # 5 minutos en segundos
        MAX_DPM_AGE = 10 * 60     # 10 minutos en segundos

        for idx, player in enumerate(MSI_PLAYERS):
            print(f"\n[!LIVE] Procesando jugador {idx+1}/{len(MSI_PLAYERS)}: {player['name']}")
            puuid = player.get("puuid")
            display_name = player["name"]
            riot_id = player.get("riot_id", {})
            game_name = riot_id.get("game_name", "")
            tag_line = riot_id.get("tag_line", "")
            if not puuid or not game_name or not tag_line:
                print(f"[!LIVE]  -> Saltando: Faltan datos (puuid/game_name/tag_line)")
                continue

            updated_at_str = None
            cache_entry = ACTIVE_GAME_CACHE.get(puuid)
            # Carga el tiempo de la última notificación de la partida (por gameId)
            last_notified_ts = None
            game_id = None
            if cache_entry and "active_game" in cache_entry:
                game_id = cache_entry["active_game"].get("gameId")
                # Carga el announced_games.json
                import json, os
                announced_path = os.path.join(os.path.dirname(__file__), "tracking", "announced_games.json")
                if os.path.exists(announced_path) and game_id:
                    with open(announced_path, "r", encoding="utf-8") as f:
                        announced_data = json.load(f)
                        # Busca el timestamp más reciente en cualquier canal
                        for chan_games in announced_data.values():
                            if str(game_id) in chan_games:
                                ts = chan_games[str(game_id)]
                                if not last_notified_ts or ts > last_notified_ts:
                                    last_notified_ts = ts
            cache_ok = False
            active_game = None

            if cache_entry and "active_game" in cache_entry:
                timestamp_guardado = cache_entry.get("timestamp", 0)
                edad_cache = now - timestamp_guardado
                print(f"[!LIVE]  -> Hay caché para {display_name}. Edad del caché: {edad_cache:.1f}s")
                if edad_cache < MAX_CACHE_AGE:
                    # Si el caché es reciente (<5min), úsalo directamente
                    cache_ok = True
                    active_game = cache_entry["active_game"]
                    print(f"[!LIVE]  -> Usando caché reciente (<5min)")
                else:
                    print(f"[!LIVE]  -> Caché viejo (>5min), se intentará API/dpm.lol")

            # Si el caché es viejo, consulta la API de Riot hasta 2 veces
            if not cache_ok and cache_entry and "active_game" in cache_entry:
                for intento in range(2):
                    print(f"[!LIVE]  -> Intento {intento+1} de API Riot para {display_name}")
                    t0 = time.time()
                    active_game, status = await get_active_game(puuid)
                    print(f"[!LIVE]    -> API status: {status}, t={time.time()-t0:.2f}s")
                    if status == 200 and active_game:
                        from tracking.active_game_cache import set_active_game
                        set_active_game(puuid, active_game)
                        cache_ok = True
                        print(f"[!LIVE]    -> API OK, datos frescos. Se actualiza caché y se usa.")
                        break
                    elif status == 429:
                    # print(f"[!LIVE]    -> API 429, esperando 2s y reintentando...")
                        await asyncio.sleep(2)
                        continue
                    else:
                    # print(f"[!LIVE]    -> API no válida, status={status}.")
                        active_game = None
                        break
                # Si sigue sin datos frescos, consulta dpm.lol
                if not cache_ok:
                    print(f"[!LIVE]  -> Consultando dpm.lol para {display_name}")
                    t1 = time.time()
                    is_live, updated_at = await get_is_live_and_updated_from_dpmlol(game_name, tag_line)
                    print(f"[!LIVE]    -> dpm.lol isLive={is_live}, updated_at={updated_at}, t={time.time()-t1:.2f}s")
                    updated_at_str = updated_at  # Guarda el string ISO para mostrarlo después
                    if is_live and updated_at:
                        try:
                            dt_updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                            age = (datetime.now(timezone.utc) - dt_updated).total_seconds()
                            print(f"[!LIVE]    -> dpm.lol age={age:.1f}s")
                            if age < MAX_DPM_AGE:
                                active_game = cache_entry["active_game"]
                                cache_ok = True
                                print(f"[!LIVE]    -> Usando caché por dpm.lol reciente (<10min)")
                            else:
                                print(f"[!LIVE]    -> dpm.lol muy viejo (>10min), no se usa")
                        except Exception as e:
                            print(f"[!LIVE]    -> Error parseando fecha dpm.lol: {e}")
                    else:
                        # Lógica de respaldo: si la partida fue notificada hace <5min, la mostramos igual pero con advertencia
                        show_as_recently_ended = False
                        if last_notified_ts and game_id:
                            seconds_since_notify = now - last_notified_ts
                            if seconds_since_notify < 5 * 60:
                                show_as_recently_ended = True
                        if show_as_recently_ended:
                            print(f"[!LIVE]    -> dpm.lol dice que terminó, pero la partida fue notificada hace {seconds_since_notify:.0f}s. Mostrando con advertencia.")
                            active_game = cache_entry["active_game"]
                            cache_ok = True
                            updated_at_str = None  # Para que abajo entre en el else y puedas poner el mensaje especial
                        else:
                            print(f"[!LIVE]    -> dpm.lol no está en partida o sin fecha")

            if not cache_ok:
                print(f"[!LIVE]  -> No hay datos válidos para {display_name}, no se muestra.")
                continue  # No hay datos válidos

            # Si llegamos aquí, hay datos válidos y frescos
            champ_id = None
            participants = active_game.get("participants", []) if isinstance(active_game, dict) else []
            for part in participants:
                if part.get("puuid") == puuid:
                    champ_id = part.get("championId")
                    break
            champ_name = await get_champion_name_by_id(champ_id) if champ_id is not None else "?"
            game_length = active_game.get("gameLength", 0) if isinstance(active_game, dict) else 0
            mins, secs = divmod(game_length, 60)
            tiempo_str = f"{mins:02d}:{secs:02d}"
            cmd_name = display_name.lower().replace(" ", "")
            if updated_at_str:
                try:
                    dt_updated = datetime.fromisoformat(updated_at_str.replace("Z", "+00:00"))
                    unix_ts = int(dt_updated.timestamp())
                    hora_str = f"<t:{unix_ts}:T>"
                except Exception:
                    hora_str = updated_at_str
                print(f"[!LIVE]  -> Mostrando {display_name} (dpm.lol hora: {hora_str})")
                vivos.append(f"**{display_name}** ({champ_name}) | {tiempo_str} en partida (`!{cmd_name}` para +info) | Última actualización: {hora_str}")
            else:
                # Si la partida fue notificada hace <5min y dpm.lol dice que terminó, muestra advertencia
                recently_ended = False
                if last_notified_ts and game_id:
                    seconds_since_notify = now - last_notified_ts
                    # Solo muestra la advertencia si han pasado al menos 2 minutos desde la notificación
                    if 120 <= seconds_since_notify < 5 * 60:
                        recently_ended = True
                print(f"[!LIVE]  -> Mostrando {display_name} (solo caché/API)")
                msg = f"**{display_name}** ({champ_name}) | {tiempo_str} en partida (`!{cmd_name}` para +info)"
                if recently_ended:
                    msg += "  *(Esta partida podría haber terminado recientemente)*"
                vivos.append(msg)

        print(f"\n[!LIVE] ===== FIN DE COMANDO !LIVE ===== (t_total={time.time()-start_total:.2f}s)\n")

        
        if not vivos:
            final_msg = "No hay jugadores MSI en partida en este momento.\n*(Algunas partidas pueden no estar actualizadas del todo, para más consistencia usa !<jugador>)*"
        else:
            final_msg = "**Jugadores MSI en partida ahora mismo:** (*Últimos 15 min aprox*)\n\n" + "\n".join(vivos)
            final_msg += "\n\n*(Algunas partidas pueden no estar actualizadas del todo, para más consistencia usa !<jugador>)*"

        # Edita el mensaje inicial con el resultado final
        await loading_msg.edit(content=final_msg)
            

    @bot.command()
    async def info(ctx, *, nombre: str):
        """
        Muestra información detallada de un jugador (pro NA o bootcamp) en un embed con imágenes.
        """
        from ui.embeds import buscar_pro_player, crear_info_embed
        jugador = buscar_pro_player(nombre)
        if not jugador:
            await ctx.send(f"No se encontró información para '{nombre}'.")
            return
        embed, files = await crear_info_embed(jugador)
        await ctx.send(embed=embed, files=files if files else None)






            
    @bot.command()
    async def ranking(ctx):
        """
        Muestra el ranking MSI (caché 3h, fuente dpm.lol)
        """
        ranking = load_ranking_cache()
        if not ranking:
            players = fetch_leaderboard()
            # Ordena por leaderboardPosition si existe
            players.sort(key=lambda p: p.get("leaderboardPosition", 9999))
            ranking = []
            for p in players:
                name = p.get("displayName", p.get("gameName", "???"))
                team = p.get("team", "")
                lane = p.get("lane") or {}
                role = lane.get("value", "")
                rank_data = p.get("rank") or {}
                rank_tier = rank_data.get("tier", "")
                rank_div = rank_data.get("rank", "")
                rank = f"{rank_tier} {rank_div}".strip()
                lp = rank_data.get("leaguePoints", 0)
                wins = rank_data.get("wins", 0)
                losses = rank_data.get("losses", 0)
                winrate = f"{round(100 * wins / (wins + losses))}%" if (wins + losses) > 0 else "?"
                kda = f"{p.get('kda', '?')}"
                champs = p.get("championIds", [])
                # Convierte IDs a nombres de campeón
                champ_names = []
                from riot.champion_cache import CHAMPION_ID_TO_NAME
                for cid in champs[:3]:
                    champ_names.append(CHAMPION_ID_TO_NAME.get(str(cid), str(cid)))
                champ_str = ", ".join(champ_names)
                ranking.append({
                    "name": name,
                    "team": team,
                    "role": role,
                    "rank": rank,
                    "lp": lp,
                    "winrate": winrate,
                    "kda": kda,
                    "champs": champ_str
                })
            save_ranking_cache(ranking)

                # Define los encabezados y extrae los datos
        headers = ["Pos", "Jugador", "Equipo", "Rol", "Rango", "LP", "Winrate", "KDA", "Mejores campeones"]
        rows = []
        for i, p in enumerate(ranking, 1):
            rows.append([
                str(i),
                p['name'],
                p['team'],
                p['role'],
                p['rank'],
                str(p['lp']),
                p['winrate'],
                p['kda'],
                p['champs']
            ])

        # Calcula el ancho máximo de cada columna
        col_widths = [len(h) for h in headers]
        for row in rows:
            for idx, cell in enumerate(row):
                col_widths[idx] = max(col_widths[idx], len(str(cell)))

        # Función para centrar texto en un ancho dado
        def center(text, width):
            text = str(text)
            if len(text) >= width:
                return text
            padding = width - len(text)
            left = padding // 2
            right = padding - left
            return " " * left + text + " " * right

        # Construye la tabla
        lines = []
        # Encabezado
        header_line = "| " + " | ".join(center(h, col_widths[i]) for i, h in enumerate(headers)) + " |"
        lines.append(header_line)
        # Separador
        sep_line = "|-" + "-|-".join("-" * col_widths[i] for i in range(len(headers))) + "-|"
        lines.append(sep_line)
        # Filas
        for row in rows:
            line = "| " + " | ".join(center(cell, col_widths[i]) for i, cell in enumerate(row)) + " |"
            lines.append(line)

        # Divide en bloques de máximo 2000 caracteres (sin cortar líneas)
        current_chunk = "```markdown\n"
        for line in lines:
            if len(current_chunk) + len(line) + 1 > 1990:  # +1 por el salto de línea final
                current_chunk += "```"
                await ctx.send(current_chunk)
                current_chunk = "```markdown\n"
            current_chunk += line + "\n"

        if current_chunk.strip() != "```markdown":
            current_chunk += "```"
            await ctx.send(current_chunk)