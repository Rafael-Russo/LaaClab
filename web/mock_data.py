"""In-memory mock data for the LaaCLab screens.

There is no database model layer yet ("nada complexo por enquanto"): the JSON
endpoints in ``api.py`` build their responses from the structures below. When a
real data layer arrives, only ``api.py`` needs to change — the front-end
contract (the JSON shapes) stays the same.
"""

import math


# --- Status thresholds ------------------------------------------------------
# A game's "bug score" (0-100) maps to a stability level. The CSS turns each
# level into a colour (critical=red, warning=orange, stable=green).

def status_for(score: int) -> dict:
    if score >= 65:
        return {"label": "Crítico", "level": "critical"}
    if score >= 40:
        return {"label": "Instável", "level": "warning"}
    return {"label": "Estável", "level": "stable"}


# --- Games catalogue --------------------------------------------------------
# ``cover`` is a two-colour gradient used to render a placeholder cover tile in
# CSS (we intentionally ship no third-party cover art). ``initials`` labels it.

_GAMES = [
    {"slug": "warzone", "name": "Warzone", "score": 72, "initials": "WZ",
     "cover": ["#3a4a3f", "#1b241f"], "favorite": True},
    {"slug": "fortnite", "name": "Fortnite", "score": 12, "initials": "FN",
     "cover": ["#2b6cb0", "#1a365d"], "favorite": False},
    {"slug": "cyberpunk-2077", "name": "Cyberpunk 2077", "score": 45, "initials": "CP",
     "cover": ["#b7950b", "#4a3f0b"], "favorite": False},
    {"slug": "gta-v", "name": "GTA V", "score": 18, "initials": "GV",
     "cover": ["#2f7d5b", "#14352a"], "favorite": False},
    {"slug": "valorant", "name": "Valorant", "score": 25, "initials": "VA",
     "cover": ["#bd3b4a", "#2b3a3f"], "favorite": True},
    {"slug": "apex-legends", "name": "Apex Legends", "score": 50, "initials": "AL",
     "cover": ["#a1421f", "#3a1a10"], "favorite": True},
    {"slug": "cs2", "name": "CS2", "score": 32, "initials": "C2",
     "cover": ["#c07f2a", "#241608"], "favorite": True},
    {"slug": "the-last-of-us", "name": "The Last Of Us Part 1", "score": 40, "initials": "TL",
     "cover": ["#3f4a55", "#161c22"], "favorite": False},
    {"slug": "red-dead-2", "name": "Red Dead 2", "score": 22, "initials": "RD",
     "cover": ["#8a3a2a", "#2a140d"], "favorite": False},
    {"slug": "elden-ring", "name": "Elden Ring", "score": 35, "initials": "ER",
     "cover": ["#b7902b", "#2a2410"], "favorite": False},
    {"slug": "mortal-kombat-1", "name": "Mortal Kombat 1", "score": 30, "initials": "MK",
     "cover": ["#7a2a2a", "#1c0d0d"], "favorite": True},
]


def _game_card(game: dict) -> dict:
    """A game with its derived status, as sent to the front-end."""
    return {
        "slug": game["slug"],
        "name": game["name"],
        "score": game["score"],
        "initials": game["initials"],
        "cover": game["cover"],
        "favorite": game["favorite"],
        "status": status_for(game["score"]),
    }


def all_games() -> list[dict]:
    return [_game_card(g) for g in _GAMES]


def get_game(slug: str) -> dict | None:
    for g in _GAMES:
        if g["slug"] == slug:
            return _game_card(g)
    return None


def favorite_games() -> list[dict]:
    return [_game_card(g) for g in _GAMES if g["favorite"]]


# --- Current (mock) user ----------------------------------------------------

CURRENT_USER = {
    "username": "GamerPro",
    "handle": "Nikola98",
    "level": 12,
    "xp": 1250,
    "xp_max": 2000,
    "bio": "Jogando, aprendendo e evoluindo todos os dias.",
    "achievements": 24,
    "friends": 8,
    "days_active": 47,
    "avatar_color": "#6b7cff",
}


# --- 24h chart series (deterministic, no randomness) ------------------------

def _series(amplitude: float, phase: float, base: float) -> list[int]:
    points = []
    for i in range(24):
        value = base + amplitude * math.sin((i / 24) * math.pi * 2 + phase)
        points.append(round(max(0, value)))
    return points


CHART_LABELS = [
    "06h", "07h", "08h", "09h", "10h", "11h", "12h", "13h",
    "14h", "15h", "16h", "17h", "18h", "19h", "20h", "21h",
    "22h", "23h", "00h", "01h", "02h", "03h", "04h", "05h",
]


def bugometro_chart() -> dict:
    return {
        "labels": CHART_LABELS,
        "series": [
            {"key": "crash", "label": "Crash", "color": "#ef4444", "data": _series(35, 0.4, 55)},
            {"key": "bug", "label": "Bug", "color": "#f59e0b", "data": _series(28, 1.6, 45)},
            {"key": "stutter", "label": "Stutter", "color": "#a855f7", "data": _series(22, 2.7, 35)},
            {"key": "fps", "label": "FPS Drop", "color": "#ec4899", "data": _series(30, 3.9, 48)},
        ],
    }


# --- Per-screen mock payloads ----------------------------------------------

HOME_BANNERS = [
    {"title": "Novas atualizações em 3 jogos que você viu nos últimos 30 dias",
     "game": "Fortnite", "cover": ["#3aa0d8", "#1a5a8f"]},
    {"title": "Warzone recebe correção emergencial de crashes",
     "game": "Warzone", "cover": ["#3a4a3f", "#1b241f"]},
    {"title": "Temporada nova de Valorant já disponível",
     "game": "Valorant", "cover": ["#bd3b4a", "#2b3a3f"]},
]

HOME_UPDATES = [
    {"game": "Cyberpunk 2077", "tag": "Atualização", "level": "stable",
     "title": "CYBERPUNK 2077",
     "text": "O novo patch de atualização 1.4.3 de Cyberpunk 2077 foi lançado.",
     "when": "Há 21 horas", "cover": ["#b7950b", "#4a3f0b"]},
    {"game": "Warzone", "tag": "Instável", "level": "warning",
     "title": "WARZONE",
     "text": "Relatos de quedas de FPS em partidas cheias após o último update.",
     "when": "Há 3 horas", "cover": ["#3a4a3f", "#1b241f"]},
    {"game": "Valorant", "tag": "Novidade", "level": "critical",
     "title": "VALORANT",
     "text": "Novo agente e mapa chegam na próxima semana.",
     "when": "Há 8 horas", "cover": ["#bd3b4a", "#2b3a3f"]},
    {"game": "GTA V", "tag": "Atualização", "level": "stable",
     "title": "GTA V",
     "text": "Correções de estabilidade no modo online.",
     "when": "Há 1 dia", "cover": ["#2f7d5b", "#14352a"]},
]

HOME_TRENDING = [
    {"title": "Lançamento GTA VI", "group": "Últimos assuntos"},
    {"title": "Lançamento GTA VI", "group": "Últimos assuntos"},
    {"title": "Lançamento GTA VI", "group": "Últimos assuntos"},
    {"title": "Lançamento GTA VI", "group": "Últimos assuntos"},
    {"title": "Lançamento GTA VI", "group": "Últimos assuntos"},
    {"title": "Lançamento GTA VI", "group": "Últimos assuntos"},
    {"title": "Lançamento GTA VI", "group": "Assuntos da última semana"},
    {"title": "Lançamento GTA VI", "group": "Assuntos da última semana"},
]

HOME_ALERT = {
    "message": "Muitos usuários reportaram CRASHES no CALL of DUTY Warzone nas últimas 24 horas!",
    "game": "warzone",
}


BUGOMETRO_METRICS = [
    {"key": "crash", "label": "Crash", "value": "Alto", "level": "critical", "icon": "shield"},
    {"key": "bugs", "label": "Bugs", "value": "Médio", "level": "warning", "icon": "bug"},
    {"key": "stutter", "label": "Stutter", "value": "Baixo", "level": "stable", "icon": "activity"},
    {"key": "fps", "label": "FPS Drop", "value": "Alto", "level": "critical", "icon": "gauge"},
]

BUGOMETRO_ACTIVITY = [
    {"title": "Aumento de crash", "subtitle": "Pico detectado às 14:32", "when": "há 3m", "level": "critical"},
    {"title": "Bug após atualização", "subtitle": "Vários relatos confirmados", "when": "há 8m", "level": "warning"},
    {"title": "Stutter em Verdansk", "subtitle": "Muitos jogadores afetados", "when": "há 15m", "level": "warning"},
    {"title": "Queda de FPS no lobby", "subtitle": "Relatos no PC e PS5", "when": "há 22m", "level": "warning"},
]

TOP_UNSTABLE = [
    {"name": "Warzone", "score": 78, "status": status_for(78)},
    {"name": "Warzone", "score": 64, "status": status_for(64)},
    {"name": "Warzone", "score": 60, "status": status_for(60)},
    {"name": "Warzone", "score": 18, "status": status_for(18)},
]


COMMUNITY_TOPICS = [
    {"title": "Queda de FPS depois da última atualização", "author": "Flamezera", "when": "há 2 anos",
     "type": "Discussão", "level": "discussion",
     "excerpt": "Depois da atualização de ontem, meu FPS caiu muito em todas partidas. Alguém mais está passando por isso?"},
    {"title": "Texturas não carregando no mapa inferno", "author": "rafaFPS", "when": "há 5 horas",
     "type": "Bug", "level": "warning",
     "excerpt": "Algumas texturas estão ficando pretas ou demorando pra carregar no inferno. Já verifiquei os arquivos e está tudo certo."},
    {"title": "Comando para melhor desempenho", "author": "Leozin", "when": "há 1 dia",
     "type": "Dica", "level": "stable",
     "excerpt": "Descobri um comando que melhorou bastante meu desempenho, vou deixar aqui caso ajude alguém: -novid -nojoy -threads 4"},
]

COMMUNITY_STATS = {
    "members": "12.458",
    "topics": "1.284",
    "messages": "8.672",
    "active_games": 24,
}

COMMUNITY_RULES = [
    "Respeite todos os membros.",
    "Não faça spam ou autopromoção.",
    "Evite conteúdos ofensivos.",
    "Ajude outros jogadores!",
]


ALERTS = [
    {"game": "Warzone", "slug": "warzone", "severity": "CRÍTICO", "level": "critical", "icon": "wifi",
     "text": "Instabilidade crítica nos servidores após atualização. Jogadores relatam desconexões e perda de progresso."},
    {"game": "Warzone", "slug": "warzone", "severity": "INSTÁVEL", "level": "warning", "icon": "alert",
     "text": "Quedas de FPS e travamentos em dispositivos de médio desempenho."},
    {"game": "Warzone", "slug": "warzone", "severity": "Atualização", "level": "stable", "icon": "check",
     "text": "Nova atualização disponível com melhorias gráficas e correções de falhas."},
    {"game": "Warzone", "slug": "warzone", "severity": "CRÍTICO", "level": "critical", "icon": "wifi",
     "text": "Instabilidade crítica nos servidores após atualização. Jogadores relatam desconexões e perda de progresso."},
]

ALERTS_SUMMARY = [
    {"label": "Críticos", "count": 2, "level": "critical"},
    {"label": "Instável", "count": 1, "level": "warning"},
    {"label": "Atualização", "count": 1, "level": "stable"},
]


def game_detail(slug: str) -> dict | None:
    game = get_game(slug)
    if game is None:
        return None
    return {
        **game,
        "last_update": "12/06/2026",
        "about": (
            "Lorem ipsum dolor sit amet consectetur adipiscing elit quisque faucibus ex "
            "sapien vitae pellentesque sem placerat in id cursus mi pretium tellus duis "
            "convallis tempus leo eu aenean sed diam urna tempor pulvinar vivamus fringilla "
            "lacus nec metus bibendum egestas iaculis massa nisl malesuada lacinia integer "
            "nunc posuere ut hendrerit semper vel class aptent taciti sociosqu ad litora."
        ),
        "merch": (
            "Lorem ipsum dolor sit amet consectetur adipiscing elit quisque faucibus ex "
            "sapien vitae pellentesque sem placerat in id cursus mi."
        ),
        "likes": "434k",
        "dislikes": "22k",
        "time_to_beat": {"medio": "X", "speedrun": "Y", "platina": "Z"},
        "achievements": "X",
        "comments": [
            {"author": "Joaozinho884", "text": "eu achei o jogo muito superestimado blablablabla"},
            {"author": "MariaGamer", "text": "eu achei o jogo muito superestimado blablablabla"},
            {"author": "ProPlayer_77", "text": "eu achei o jogo muito superestimado blablablabla"},
        ],
    }


PROFILE_RECENT = [
    {"game": "Call of Duty", "duration": "24h 30m", "percent": 72, "cover": ["#3a4a3f", "#1b241f"]},
    {"game": "Call of Duty", "duration": "21h 16m", "percent": 64, "cover": ["#3a4a3f", "#1b241f"]},
    {"game": "Call of Duty", "duration": "11h 07m", "percent": 37, "cover": ["#3a4a3f", "#1b241f"]},
]
