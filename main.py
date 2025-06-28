# main.py

import asyncio
import subprocess
from config import DISCORD_TOKEN
from keep_alive import keep_alive

from bot import bot

if __name__ == "__main__":
    # 0) Actualiza accounts.py desde el endpoint externo
    print("🔄 Actualizando MSI_PLAYERS desde leaderboard externo…")
    subprocess.run(["python", "-m", "tracking.update_accounts_from_leaderboard"], check=True)
    print("✅ accounts.py actualizado desde leaderboard externo.")

    # 1) Verifica/corrige los PUUIDs
    print("🔄 Verificando/corrigiendo PUUIDs…")
    subprocess.run(["python", "-m", "tracking.update_puuids"], check=True)
    print("✅ PUUIDs verificados/corregidos.")

    # 2) Comprueba que el token exista y sea str
    if DISCORD_TOKEN is None:
        raise RuntimeError("❌ La variable DISCORD_TOKEN no está definida en .env")

    # 3) Arranca el bot
    print("🚀 Iniciando bot de Discord…")
    keep_alive() # Mantiene el bot activo en Discloud
    bot.run(DISCORD_TOKEN)