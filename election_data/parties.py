"""Party colours and name normalisation."""
import re

COLORS = {
    # United States
    "Republican": "#d22532", "Democratic": "#244999", "Libertarian": "#fed105",
    "Green": "#17aa5c", "Independent": "#9a9a9a",
    # United Kingdom
    "Labour": "#e4003b", "Conservative": "#0087dc", "Liberal Democrats": "#faa61a",
    "SNP": "#fdf38e", "Reform UK": "#12b6cf", "Plaid Cymru": "#005b54",
    "DUP": "#d46a4c", "Sinn Féin": "#326760", "SDLP": "#2aa82c", "Alliance": "#f6cb2f",
    "UUP": "#48a5ee", "TUV": "#0c3a6a", "Speaker": "#555555", "Brexit Party": "#12b6cf",
    "Workers Party": "#770000",
    # Bangladesh
    "Awami League": "#006a4e", "BNP": "#1f4fa3", "Jatiya Party (Ershad)": "#e6ab02",
    "Jatiya Party": "#e6ab02", "Jamaat-e-Islami": "#2e8b57", "NCP": "#e07b39",
    "Workers Party of Bangladesh": "#b22222", "Jatiya Samajtantrik Dal": "#cc3333",
    "Bangladesh Kalyan Party": "#6a5acd", "Islami Andolan Bangladesh": "#8b4513",
    "Gano Forum": "#ff8c00", "Khelafat Majlis": "#556b2f",
    "Tie": "#bbbbbb", "Withheld": "#cfcfcf", "Ganosamhati Andolan": "#c71585",
    "Bikalpa Dhara Bangladesh": "#ff7f50", "Tariqat Federation": "#2f4f4f", "Jatiya Party (Manju)": "#d2b48c",
    "Gano Odhikar Parishad": "#8a2be2", "Bangladesh Jatiya Party": "#9acd32", "Jatiya Samajtantrik Dal": "#cc3333", "Vacant": "#dddddd", "Other": "#7f7f7f", "Pending": "#e8e8e8",
}

ALIASES = {
    # UK
    "scottish national": "SNP", "scottish national party": "SNP", "snp": "SNP",
    "labour co-op": "Labour", "labour co-operative": "Labour", "labour and co-operative party": "Labour", "labour and co-operative": "Labour", "labour": "Labour",
    "liberal democrat": "Liberal Democrats", "liberal democrats": "Liberal Democrats",
    "conservative": "Conservative", "conservative and unionist": "Conservative",
    "reform": "Reform UK", "reform uk": "Reform UK", "brexit": "Brexit Party", "brexit party": "Brexit Party",
    "plaid cymru": "Plaid Cymru", "democratic unionist": "DUP", "democratic unionist party": "DUP", "dup": "DUP",
    "sinn fein": "Sinn Féin", "sinn féin": "Sinn Féin",
    "social democratic and labour": "SDLP", "social democratic and labour party": "SDLP", "sdlp": "SDLP",
    "alliance": "Alliance", "alliance party of northern ireland": "Alliance",
    "ulster unionist": "UUP", "ulster unionist party": "UUP", "uup": "UUP",
    "traditional unionist voice": "TUV", "speaker": "Speaker", "green": "Green", "green party of england and wales": "Green",
    "independent": "Independent", "workers party of britain": "Workers Party",
    # US
    "republican": "Republican", "democratic": "Democratic", "democrat": "Democratic",
    "libertarian": "Libertarian",
    # Bangladesh
    "awami league": "Awami League", "bangladesh awami league": "Awami League", "al": "Awami League",
    "bangladesh nationalist party": "BNP", "bnp": "BNP",
    "jatiya party (ershad)": "Jatiya Party", "jatiya party": "Jatiya Party", "jp(e)": "Jatiya Party",
    "jp (e)": "Jatiya Party",
    "bangladesh jamaat-e-islami": "Jamaat-e-Islami", "jamaat-e-islami": "Jamaat-e-Islami",
    "jamaat-e-islami bangladesh": "Jamaat-e-Islami", "jamaat": "Jamaat-e-Islami",
    "national citizen party": "NCP", "ncp": "NCP",
    "workers party of bangladesh": "Workers Party of Bangladesh",
    "bangladesh khelafat majlis": "Khelafat Majlis", "khelafat majlis": "Khelafat Majlis",
    "islami andolan bangladesh": "Islami Andolan Bangladesh",
}


def normalise(name: str) -> str:
    n = re.sub(r"\[[^\]]*\]", "", str(name or "")).strip()
    key = re.sub(r"\s+", " ", n.lower()).strip(" .")
    key = key.replace("’", "'")
    if key in ALIASES:
        return ALIASES[key]
    for k in ("party", "the "):
        key2 = key.replace(k, "").strip()
        if key2 in ALIASES:
            return ALIASES[key2]
    if key.startswith("independent"):
        return "Independent"
    return n or "Other"


def color(party: str) -> str:
    return COLORS.get(party, COLORS["Other"])


def color_map(parties) -> dict:
    return {p: color(p) for p in parties}
