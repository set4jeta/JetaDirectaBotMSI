def parse_ranked_data(ranked_data):
    if ranked_data is not None:
        if isinstance(ranked_data, list) and ranked_data:
            soloq = next((q for q in ranked_data if q["queueType"] == "RANKED_SOLO_5x5"), None)
            if soloq:
                tier = soloq["tier"].capitalize()
                rank = soloq["rank"]
                lp = soloq["leaguePoints"]
                return f"{tier} {rank} ({lp} LP)"
            else:
                return "Unranked"
        else:
            return "Unranked"
    else:
        return "Sin datos de ranked"