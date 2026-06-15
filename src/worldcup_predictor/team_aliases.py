"""Team-name aliases.

Keep this as the only place with hardcoded team names. Add aliases when a data
source uses a different spelling from your fixtures file.
"""

TEAM_ALIASES = {
    "USA": "United States",
    "USMNT": "United States",
    "United States of America": "United States",
    "Korea Republic": "South Korea",
    "Republic of Ireland": "Ireland",
    "IR Iran": "Iran",
    "Czech Republic": "Czechia",
    "Türkiye": "Turkey",
    "Ivory Coast": "Cote d'Ivoire",
    "Côte d’Ivoire": "Cote d'Ivoire",
    "Côte d'Ivoire": "Cote d'Ivoire",
}


def normalize_team_name(name: object) -> str:
    if name is None:
        return ""
    text = str(name).strip()
    return TEAM_ALIASES.get(text, text)
