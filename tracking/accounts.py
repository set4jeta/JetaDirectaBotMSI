import os
import json

JSON_PATH = os.path.join(os.path.dirname(__file__), "accounts.json")

if os.path.exists(JSON_PATH):
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        MSI_PLAYERS = json.load(f)
else:
    MSI_PLAYERS = []