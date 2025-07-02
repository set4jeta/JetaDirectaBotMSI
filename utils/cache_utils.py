import os
import json
import time
from tracking.active_game_cache import ACTIVE_GAME_CACHE

def limpiar_cache_partidas_viejas():
    now = time.time()
    MAX_CACHE_AGE = 90 * 60  # 90 minutos en segundos
    to_delete = []
    for puuid, entry in list(ACTIVE_GAME_CACHE.items()):
        timestamp_guardado = entry["timestamp"]
        game_length = entry.get("game_length", 0) or 0
        tiempo_transcurrido = int(game_length + (now - timestamp_guardado))
        if tiempo_transcurrido > MAX_CACHE_AGE:
            to_delete.append(puuid)
    for puuid in to_delete:
        del ACTIVE_GAME_CACHE[puuid]

RANKING_CACHE_PATH = os.path.join("tracking", "ranking_cache.json")
RANKING_CACHE_TTL = 1800  # 30 minutos

def load_ranking_cache():
    if os.path.exists(RANKING_CACHE_PATH):
        with open(RANKING_CACHE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            if time.time() - data.get("timestamp", 0) < RANKING_CACHE_TTL:
                return data["ranking"]
    return None

def save_ranking_cache(ranking):
    with open(RANKING_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump({"timestamp": time.time(), "ranking": ranking}, f, ensure_ascii=False, indent=2)

HISTORIAL_CACHE_PATH = os.path.join("tracking", "historial_cache.json")

def load_historial_cache():
    if os.path.exists(HISTORIAL_CACHE_PATH):
        with open(HISTORIAL_CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_historial_cache(cache):
    with open(HISTORIAL_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)