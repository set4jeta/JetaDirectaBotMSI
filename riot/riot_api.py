import aiohttp
import os
from .champion_cache import CHAMPION_ID_TO_NAME
import urllib.parse

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


