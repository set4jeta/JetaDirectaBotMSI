import os
import cloudscraper
import json

ENDPOINT = "https://dpm.lol/v1/leaderboards/custom/f1a01cf4-0352-4dac-9c6d-e8e1e44db67a"
JSON_PATH = os.path.join(os.path.dirname(__file__), "accounts.json")

def fetch_players():
    scraper = cloudscraper.create_scraper()
    resp = scraper.get(ENDPOINT)
    try:
        data = resp.json()
    except Exception as e:
        print("❌ Error al parsear JSON:", e)
        return []
    return data.get("players", [])

def build_account_entry(player):
    entry = {
        'riot_id': {
            'game_name': player["gameName"],
            'tag_line': player["tagLine"]
        },
        'team': player.get("team", ""),
        'name': player.get("displayName", player["gameName"]),
        # NO GUARDES 'puuid' DEL ENDPOINT
    }
    # Si tiene rank, guárdalo, pero SIN el puuid interno
    if "rank" in player and player["rank"]:
        rank = dict(player["rank"])
        rank.pop("puuid", None)
        entry["rank"] = rank
    return entry

def main():
    # 1. Carga los jugadores actuales (manuales y automáticos)
    if os.path.exists(JSON_PATH):
        with open(JSON_PATH, "r", encoding="utf-8") as f:
            current_players = json.load(f)
    else:
        current_players = []

    # 2. Descarga los jugadores del endpoint
    players = fetch_players()
    entries = [build_account_entry(p) for p in players]

    # 3. Fusiona: agrega los que no están (por riot_id y tag_line)
    def riot_id_key(p):
        return (p["riot_id"]["game_name"].lower(), p["riot_id"]["tag_line"].lower())

    # --- CAMBIO AQUÍ ---
    # Crea un dict de los jugadores actuales por riot_id
    current_by_riot_id = {riot_id_key(p): p for p in current_players}

    # Para cada jugador nuevo, si ya existe y tiene puuid, consérvalo
    for entry in entries:
        key = riot_id_key(entry)
        if key in current_by_riot_id and "puuid" in current_by_riot_id[key]:
            entry["puuid"] = current_by_riot_id[key]["puuid"]

    existing_keys = {riot_id_key(p): p for p in entries}
    # Agrega los manuales que no están en el endpoint
    for p in current_players:
        key = riot_id_key(p)
        if key not in existing_keys:
            entries.append(p)

    # 4. Guarda el JSON fusionado
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    print(f"✅ accounts.json fusionado y actualizado con {len(entries)} jugadores.")
    print(f"Ruta absoluta de accounts.json: {os.path.abspath(JSON_PATH)}")

if __name__ == "__main__":
    main()
    
    
    
    
    
def fetch_leaderboard():
    scraper = cloudscraper.create_scraper()
    resp = scraper.get(ENDPOINT)
    try:
        data = resp.json()
    except Exception as e:
        print("❌ Error al parsear JSON:", e)
        return []
    return data.get("players", [])    
    
    