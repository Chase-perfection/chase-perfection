#!/usr/bin/env python3
"""
Genere stats.svg : une carte facon terminal avec tes vrais chiffres GitHub
(depots, etoiles, abonnes, commits de l'annee, pull requests, issues),
en tuiles qui apparaissent en fondu.

Donnees reelles via l'API GraphQL GitHub.
  - En local (test)     : sans token -> chiffres factices.
  - Dans GitHub Actions : le token est fourni automatiquement (voir le workflow).

Variables d'environnement :
  GH_TOKEN : jeton GitHub
  GH_LOGIN : ton pseudo GitHub
"""

import os
import json
import datetime
import urllib.request

LOGIN = os.environ.get("GH_LOGIN", "Chase-perfection")
TOKEN = os.environ.get("GH_TOKEN")

# --- Couleurs (theme GitHub dark) ---
BG      = "#0d1117"
BORDER  = "#30363d"
TILE    = "#161b22"
FG      = "#c9d1d9"
DIM     = "#8b949e"
ACCENT  = "#39d353"
CYAN    = "#58a6ff"
RED     = "#ff5f56"
YELLOW  = "#ffbd2e"
GREEN   = "#27c93f"

FONT   = "ui-monospace, 'SF Mono', 'DejaVu Sans Mono', Consolas, monospace"
width  = 720
PADX   = 22
GAP    = 16
TOP    = 52          # sous la barre de titre
TILE_H = 82
COLS   = 3


def _graphql(query, variables, token, login):
    payload = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": login,
        },
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def fetch_stats(login, token):
    # 1) Donnees de base + annee de creation du compte.
    base_q = """
    query($login: String!) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          nodes { stargazerCount }
        }
        pullRequests { totalCount }
        issues { totalCount }
      }
    }"""
    u = _graphql(base_q, {"login": login}, token, login)["user"]
    stars = sum(n["stargazerCount"] for n in u["repositories"]["nodes"])
    start_year = int(u["createdAt"][:4])

    # 2) Total des commits sur TOUTES les annees (contributionsCollection est
    #    limite a 1 an, donc on interroge annee par annee et on additionne).
    #    'restrictedContributionsCount' ajoute les contributions privees
    #    (visibles seulement avec un token qui y a acces, ex. GH_PAT).
    year_q = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          totalCommitContributions
          restrictedContributionsCount
        }
      }
    }"""
    this_year = datetime.datetime.now(datetime.timezone.utc).year
    commits = 0
    for year in range(start_year, this_year + 1):
        variables = {
            "login": login,
            "from": f"{year}-01-01T00:00:00Z",
            "to":   f"{year}-12-31T23:59:59Z",
        }
        cc = _graphql(year_q, variables, token, login)["user"]["contributionsCollection"]
        commits += cc["totalCommitContributions"] + cc["restrictedContributionsCount"]

    return {
        "repos":     u["repositories"]["totalCount"],
        "stars":     stars,
        "followers": u["followers"]["totalCount"],
        "commits":   commits,
        "prs":       u["pullRequests"]["totalCount"],
        "issues":    u["issues"]["totalCount"],
    }


def mock_stats():
    return {"repos": 24, "stars": 87, "followers": 41,
            "commits": 1342, "prs": 63, "issues": 19}


def human(n):
    if n >= 1000:
        return f"{n/1000:.1f}k".replace(".0k", "k")
    return str(n)


# Ordre d'affichage : (cle, etiquette, couleur)
TILES = [
    ("repos",     "dépôts",        CYAN),
    ("stars",     "étoiles",       YELLOW),
    ("followers", "abonnés",       ACCENT),
    ("commits",   "commits",       ACCENT),
    ("prs",       "pull requests", CYAN),
    ("issues",    "issues",        YELLOW),
]


def build_svg(stats):
    rows = (len(TILES) + COLS - 1) // COLS
    tile_w = (width - 2 * PADX - (COLS - 1) * GAP) / COLS
    height = TOP + rows * TILE_H + (rows - 1) * GAP + PADX

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height:.0f}" '
        f'viewBox="0 0 {width} {height:.0f}" font-family="{FONT}">'
    ]
    parts.append('''<style>
      .tile { opacity:0; animation: pop .5s ease forwards; }
      @keyframes pop { from { opacity:0; transform: translateY(8px); }
                       to   { opacity:1; transform: translateY(0);   } }
    </style>''')

    # Fenetre + barre de titre
    parts.append(f'<rect x="1" y="1" width="{width-2}" height="{height-2:.0f}" rx="10" '
                 f'fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>')
    parts.append(f'<rect x="1" y="1" width="{width-2}" height="34" rx="10" fill="{TILE}"/>')
    parts.append(f'<rect x="1" y="20" width="{width-2}" height="15" fill="{TILE}"/>')
    for i, c in enumerate((RED, YELLOW, GREEN)):
        parts.append(f'<circle cx="{22+i*20}" cy="18" r="6" fill="{c}"/>')
    parts.append(f'<text x="{width/2}" y="23" text-anchor="middle" fill="{DIM}" '
                 f'font-size="13">{LOGIN}@stats: ~</text>')

    # Tuiles
    for i, (key, label, color) in enumerate(TILES):
        r, c = divmod(i, COLS)
        x = PADX + c * (tile_w + GAP)
        y = TOP + r * (TILE_H + GAP)
        delay = 0.15 + i * 0.1
        val = human(stats.get(key, 0))
        cx = x + tile_w / 2
        parts.append(f'<g class="tile" style="animation-delay:{delay:.2f}s">')
        parts.append(f'<rect x="{x:.1f}" y="{y}" width="{tile_w:.1f}" height="{TILE_H}" '
                     f'rx="8" fill="{TILE}" stroke="{BORDER}" stroke-width="1"/>')
        parts.append(f'<text x="{cx:.1f}" y="{y+42}" text-anchor="middle" '
                     f'fill="{color}" font-size="30" font-weight="700">{val}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{y+64}" text-anchor="middle" '
                     f'fill="{DIM}" font-size="13">{label}</text>')
        parts.append('</g>')

    parts.append('</svg>')
    return "\n".join(parts)


def main():
    if TOKEN:
        try:
            stats = fetch_stats(LOGIN, TOKEN)
            print(f"Stats reelles recuperees pour {LOGIN}.")
        except Exception as e:
            print(f"Echec API ({e}) -> stats factices.")
            stats = mock_stats()
    else:
        print("Pas de GH_TOKEN -> stats factices (mode test local).")
        stats = mock_stats()

    with open("stats.svg", "w", encoding="utf-8") as f:
        f.write(build_svg(stats))
    print("stats.svg genere.")


if __name__ == "__main__":
    main()
