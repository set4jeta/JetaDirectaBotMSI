import time

# Estructura: {puuid: {"active_game": dict, "timestamp": float}}
ACTIVE_GAME_CACHE = {}

def set_active_game(puuid, active_game):
    ACTIVE_GAME_CACHE[puuid] = {
        "active_game": active_game,
        "timestamp": time.time()
    }

def get_active_game_cache(puuid):
    return ACTIVE_GAME_CACHE.get(puuid)