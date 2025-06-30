import aiohttp
import os
from .champion_cache import CHAMPION_ID_TO_NAME
import urllib.parse
import cloudscraper
import asyncio

RIOT_API_KEY = os.getenv("RIOT_API_KEY")
HEADERS = {"X-Riot-Token": RIOT_API_KEY}

# Región para Riot Account API (Americas)
RIOT_BASE_URL = "https://americas.api.riotgames.com"
# Región para NA-specific endpoints
NA_BASE_URL = "https://na1.api.riotgames.com"

# ————————————————

async def get_puuid_from_riot_id(game_name: str, tag_line: str) -> tuple[str | None, int]:
    url = f"{RIOT_BASE_URL}/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp: # type: ignore
            if resp.status == 200:
                data = await resp.json()
                return data.get("puuid"), 200
            return None, resp.status

# ————————————————

async def get_summoner_by_puuid(puuid: str) -> dict | None:
    url = f"{NA_BASE_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp: # type: ignore # type: ignore
            if resp.status == 200:
                return await resp.json()
            return None

# ————————————————

async def get_active_game(puuid: str) -> tuple[dict | None, int]:
    url = f"{NA_BASE_URL}/lol/spectator/v5/active-games/by-summoner/{puuid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp: # type: ignore
            if resp.status == 200:
                return await resp.json(), 200
            return None, resp.status

# ————————————————

async def get_ranked_data(puuid: str) -> dict | None:
    url = f"{NA_BASE_URL}/lol/league/v4/entries/by-puuid/{puuid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp: # type: ignore
            if resp.status == 200:
                return await resp.json()
            return None

# ————————————————

async def get_champion_name_by_id(champion_id: int) -> str:
    if str(champion_id) == "799":
        return "Ambessa"
    if str(champion_id) == "800":
        return "Mel"
    return CHAMPION_ID_TO_NAME.get(str(champion_id), "Unknown")


async def is_valid_puuid(puuid: str) -> bool:
    url = f"{NA_BASE_URL}/lol/summoner/v4/summoners/by-puuid/{puuid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp: # type: ignore
            if resp.status == 429:
                print(f"[DEBUG] is_valid_puuid: RATE LIMIT (429) para {puuid}")
                return True  # No marcar como inválido, solo saltar
            if resp.status != 200:
                print(f"[DEBUG] is_valid_puuid: status={resp.status} para {puuid}")
            return resp.status == 200


#async def get_match_ids_by_puuid(puuid: str, start_time: int, end_time: int, queue: int = None, count: int = 10) -> list[str]: # type: ignore
    #"""
   # Devuelve una lista de match IDs para el puuid entre start_time y end_time (epoch segundos).
   # """
   # params = {
        #"startTime": start_time,
       # "endTime": end_time,
      #  "count": count
  #  }
  #  if queue:
  #      params["queue"] = queue
 #   url = f"https://americas.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"
 #   async with aiohttp.ClientSession() as session:
  #      async with session.get(url, headers=HEADERS, params=params) as resp: # type: ignore
 #           if resp.status == 200:
  #              return await resp.json()
 #           return []



#async def get_match_by_id(match_id: str) -> dict | None:
    #url = f"https://americas.api.riotgames.com/lol/match/v5/matches/{match_id}"
    #async with aiohttp.ClientSession() as session:
        #async with session.get(url, headers=HEADERS) as resp: # type: ignore
           # if resp.status == 200:
               # return await resp.json()
            #return None
        


async def get_is_live_and_updated_from_dpmlol(game_name, tag_line):
    import functools
    game_name_enc = game_name.replace(" ", "+")
    tag_line_enc = tag_line
    url = f"https://dpm.lol/v1/players/search?gameName={game_name_enc}&tagLine={tag_line_enc}"
    print(f"[DPMLOL] Consultando (cloudscraper): {url}")

    def fetch():
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url)
        print(f"[DPMLOL] Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"[DPMLOL] Respuesta: {data}")
            if isinstance(data, list):
                for player in data:
                    if (
                        player.get("gameName", "").lower() == game_name.lower()
                        and player.get("tagLine", "").lower() == tag_line.lower()
                    ):
                        print(f"[DPMLOL] Encontrado en lista: isLive={player.get('isLive')}, updatedAt={player.get('updatedAt')}")
                        return player.get("isLive", False), player.get("updatedAt", None)
                print("[DPMLOL] No encontrado en lista")
                return False, None
            print(f"[DPMLOL] Dict directo: isLive={data.get('isLive')}, updatedAt={data.get('updatedAt')}")
            is_live = data.get("isLive", False)
            updated_at = data.get("updatedAt", None)
            return is_live, updated_at
        print("[DPMLOL] Respuesta no válida o error")
        return False, None

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fetch)


async def get_puuid_from_dpmlol(game_name, tag_line):
    url = f"https://dpm.lol/v1/players/search?gameName={game_name}&tagLine={tag_line}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("puuid")
    return None




async def get_match_history_from_dpmlol(puuid):
    url = f"https://dpm.lol/v1/players/{puuid}/match-history"
    def fetch():
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url)
        if resp.status_code == 200:
            return resp.json()
        return None
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fetch)




async def get_dpmlol_puuid(game_name, tag_line):
    url = f"https://dpm.lol/v1/players/search?gameName={game_name.replace(' ', '+')}&tagLine={tag_line}"
    def fetch():
        scraper = cloudscraper.create_scraper()
        resp = scraper.get(url)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, dict):
                return data.get("puuid")
            elif isinstance(data, list) and data:
                return data[0].get("puuid")
        return None
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, fetch)