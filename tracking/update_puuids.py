import asyncio
import os
from tracking.accounts import MSI_PLAYERS
from riot.riot_api import get_puuid_from_riot_id
import json

ACCOUNTS_PATH = os.path.join(os.path.dirname(__file__), "accounts.py")

async def update_accounts_with_puuids():
    updated_players = []

    for player in MSI_PLAYERS:
        riot_id = player["riot_id"]
        game_name = riot_id["game_name"]
        tag_line = riot_id["tag_line"]

        print(f"Verificando puuid para {player['name']} ({game_name}#{tag_line})...")
        puuid_real = await get_puuid_from_riot_id(game_name, tag_line)
        puuid_guardado = player.get("puuid")

        if puuid_real:
            if puuid_guardado != puuid_real:
                print(f"⚠️ PUUID desactualizado para {player['name']}:")
                print(f"    Guardado:   {puuid_guardado}")
                print(f"    Correcto:   {puuid_real}")
                player["puuid"] = puuid_real
            else:
                print(f"✅ PUUID correcto para {player['name']}")
        else:
            print(f"❌ No se pudo obtener el PUUID para {player['name']} ({game_name}#{tag_line})")

        updated_players.append(player)

    # Generar el contenido válido de accounts.py
    content = "MSI_PLAYERS = [\n"
    for p in updated_players:
        content += "    {\n"
        content += f"        'riot_id': {{'game_name': '{p['riot_id']['game_name']}', 'tag_line': '{p['riot_id']['tag_line']}' }},\n"
        content += f"        'team': '{p['team']}',\n"
        content += f"        'name': '{p['name']}',\n"
        if "puuid" in p:
            content += f"        'puuid': '{p['puuid']}',\n"
        content += "    },\n"
    content += "]\n"

 
    # Guarda también en JSON
    json_path = os.path.join(os.path.dirname(__file__), "accounts.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(updated_players, f, ensure_ascii=False, indent=2)

    print("✅ accounts.py actualizado con puuids")
    print("✅ accounts.json actualizado con puuids")    

   

if __name__ == "__main__":
    asyncio.run(update_accounts_with_puuids())
