# PDV Ibix - Classificação de visitantes (IP + User-Agent)
# Tipos: HUMANO, BOT, CLOUD


def classificar_visitante(ip: str | None, user_agent: str | None) -> str:
    """
    Classifica o visitante com base em IP e User-Agent.
    Retorna: "HUMANO", "BOT" ou "CLOUD".
    """
    ua = (user_agent or "").lower()
    ip_str = (ip or "").strip()

    # BOT: User-Agent contém indicadores de bot
    if any(bot in ua for bot in ["bot", "crawler", "spider", "checker", "gptbot"]):
        return "BOT"

    # CLOUD: IP de data center (prefixos típicos de GCP, AWS, Azure, etc.)
    prefixes_cloud = ("34.", "104.", "136.", "35.", "52.", "54.")
    if ip_str and any(ip_str.startswith(p) for p in prefixes_cloud):
        return "CLOUD"

    return "HUMANO"
