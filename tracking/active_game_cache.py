import time

# Estructura: {puuid: {"active_game": dict, "timestamp": float}}
ACTIVE_GAME_CACHE = {}

def set_active_game(puuid, active_game):
    print(f"[CACHE] Actualizando caché para {puuid} a {time.time()}")
    # Guarda también el gameLength y el timestamp de cuando se obtuvo
    
    game_length = active_game.get("gameLength")
    ACTIVE_GAME_CACHE[puuid] = {
        "active_game": active_game,
        "timestamp": time.time(),
        "game_length": game_length if isinstance(game_length, int) else None
    }

def get_active_game_cache(puuid):
    return ACTIVE_GAME_CACHE.get(puuid)