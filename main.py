# main.py

import asyncio
import subprocess
import importlib
from config import DISCORD_TOKEN
from keep_alive import keep_alive

if __name__ == "__main__":
    # 0) Actualiza accounts.py desde el endpoint externo
    print("🔄 Actualizando MSI_PLAYERS desde leaderboard externo…")
    subprocess.run(["python", "-m", "tracking.update_accounts_from_leaderboard"], check=True)
    print("✅ accounts.py actualizado desde leaderboard externo.")

    # 1) Verifica/corrige los PUUIDs
    print("🔄 Verificando/corrigiendo PUUIDs…")
    subprocess.run(["python", "-m", "tracking.update_puuids"], check=True)
    print("✅ PUUIDs verificados/corregidos.")

    # 1.5) Recarga el módulo de cuentas para que MSI_PLAYERS esté actualizado
    import tracking.accounts
    importlib.reload(tracking.accounts)

    # 2) Comprueba que el token exista y sea str
    if DISCORD_TOKEN is None:
        raise RuntimeError("❌ La variable DISCORD_TOKEN no está definida en .env")

    # 3) Arranca el bot (importa aquí, después de recargar accounts)
    print("🚀 Iniciando bot de Discord…")
    keep_alive() # Mantiene el bot activo en Discloud
    from bot import bot
    bot.run(DISCORD_TOKEN)