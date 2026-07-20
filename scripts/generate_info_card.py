#!/usr/bin/env python3
"""
Genere info-card.svg : un panneau facon "neofetch" qui se devoile ligne par ligne.

Le logo a gauche est ton VRAI avatar GitHub, converti en ASCII couleur.
  - Si Pillow est installe et l'avatar accessible : rendu de l'avatar.
  - Sinon : repli sur le petit logo ASCII statique (LOGO ci-dessous).

=> EDITE LE BLOC 'CONFIG' CI-DESSOUS avec tes infos.

Variable d'environnement optionnelle :
  GH_LOGIN : ton pseudo GitHub (defaut : Chase-perfection)
"""

import os
import io
import urllib.request
from html import escape

# ============================ CONFIG (a personnaliser) ============================
USER   = os.environ.get("GH_LOGIN", "Chase-perfection")   # en-tete + avatar
TITLE  = "~"                          # ce qui suit les ":" dans la barre de titre

# Logo ASCII de secours (utilise seulement si l'avatar ne peut pas etre charge).
LOGO = r"""
   __
  /  \___
 /       \
 \  o  o  /
  \  __  /
   \____/
"""

# --- Avatar -> ASCII couleur ---
AV_COLS = 24                 # largeur en caracteres
AV_CW   = 6.6                # avance d'un caractere (px) a la taille AV_FS
AV_CH   = 11                 # hauteur d'une ligne (px)
AV_FS   = 11                 # taille de police du logo
AV_RAMP = "@%#*+=-:. "       # du plus dense (sombre) au plus clair (vide)


def _avatar_image(login):
    """Telecharge l'avatar GitHub et le pose sur fond blanc. Renvoie une image RGB."""
    from PIL import Image
    urls = [
        f"https://avatars.githubusercontent.com/{login}",
        f"https://github.com/{login}.png",
    ]
    raw = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": login})
            with urllib.request.urlopen(req, timeout=30) as r:
                raw = r.read()
            break
        except Exception:
            continue
    if raw is None:
        raise RuntimeError("avatar introuvable")
    im = Image.open(io.BytesIO(raw)).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    return Image.alpha_composite(bg, im).convert("RGB")


def avatar_cells(login):
    """Renvoie une grille [ligne][col] de (caractere, couleur_hex ou None)."""
    im = _avatar_image(login)
    rows = max(1, round(AV_COLS * AV_CW / AV_CH))
    small = im.resize((AV_COLS, rows))
    grid = []
    for y in range(rows):
        line = []
        for x in range(AV_COLS):
            r, g, b = small.getpixel((x, y))
            lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255
            ch = AV_RAMP[min(len(AV_RAMP) - 1, int(lum * len(AV_RAMP)))]
            if ch == " ":
                line.append((" ", None))
            else:
                # Rehausse un peu la luminosite pour rester lisible sur fond sombre.
                br = lambda c: min(255, int(c * 0.8 + 55))
                line.append((ch, f"#{br(r):02x}{br(g):02x}{br(b):02x}"))
        grid.append(line)
    return grid

# Lignes d'info a droite : (etiquette, valeur). L'ordre = l'ordre d'apparition.
INFO = [
    ("role",    "Consultant en cybersécurité et automatisation des processus"),
    ("Compétence",   "Concevoir et déployer des solutions d'automatisation pour les équipes IT et cybersécurité, en intégrant des technologies d'intelligence artificielle afin d'optimiser les processus, renforcer la sécurité du système d'information et réduire les tâches répétitives."),
    ("editor",  "VS Code / Antigravity / Manus / Claude"),
    ("os",      "Linux  ·  Windows"),
    ("focus",   "AI builder  ·  Open source"),
    ("uptime",  "coding since 2020"),
]
# ================================================================================

# --- Couleurs (theme GitHub dark) ---
BG      = "#0d1117"
BORDER  = "#30363d"
FG      = "#c9d1d9"
DIM     = "#8b949e"
ACCENT  = "#39d353"
CYAN    = "#58a6ff"
RED     = "#ff5f56"
YELLOW  = "#ffbd2e"
GREEN   = "#27c93f"

# --- Geometrie ---
PAD        = 20
LINE_H     = 22
LOGO_X     = PAD
INFO_X     = 200
TOP        = 60          # espace pour la barre de titre
FONT       = "ui-monospace, 'SF Mono', 'DejaVu Sans Mono', Consolas, monospace"
CHAR_W     = 8.4         # largeur approx. d'un caractere en monospace 14px
width      = 720


def wrap(text, max_chars):
    """Coupe 'text' en lignes d'au plus 'max_chars' caracteres, sur les espaces."""
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if not cur:
            cur = w
        elif len(cur) + 1 + len(w) <= max_chars:
            cur += " " + w
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


# Pre-calcule les lignes rendues pour chaque info (avec retour a la ligne des
# valeurs trop longues) afin de dimensionner correctement la carte.
# Chaque valeur commence a une colonne alignee juste apres "cle: ".
info_rows = []   # liste de (value_x, [ (label|None, chunk) ... ]) une entree par ligne rendue
for k, v in INFO:
    prefix_len = len(k) + 2                      # "cle: "
    value_x = INFO_X + prefix_len * CHAR_W
    max_chars = max(8, int((width - value_x - PAD) / CHAR_W))
    chunks = wrap(v, max_chars)
    for j, chunk in enumerate(chunks):
        info_rows.append((value_x, k if j == 0 else None, chunk))

# Essaie de construire l'avatar en ASCII couleur ; repli sur le logo statique.
avatar = None
try:
    avatar = avatar_cells(USER)
    print(f"Avatar ASCII genere pour {USER} ({len(avatar)} lignes).")
except Exception as e:
    print(f"Avatar indisponible ({e}) -> logo ASCII de secours.")

logo_lines = [l for l in LOGO.splitlines() if l.strip("\n")]

# +2 : ligne "user@profile" + separateur, puis toutes les lignes d'info (avec wrap)
n_info_lines = 2 + len(info_rows)
info_h = n_info_lines * LINE_H
logo_h = len(avatar) * AV_CH if avatar else len(logo_lines) * LINE_H
height = TOP + max(info_h, logo_h) + PAD

parts = []
parts.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
    f'viewBox="0 0 {width} {height}" font-family="{FONT}" font-size="14">'
)

# Styles + keyframes (le fondu ligne par ligne)
parts.append(f'''<style>
  .row {{ opacity:0; animation: appear .5s ease forwards; }}
  @keyframes appear {{
    from {{ opacity:0; transform: translateX(10px); }}
    to   {{ opacity:1; transform: translateX(0);    }}
  }}
  .k {{ fill:{ACCENT}; font-weight:600; }}
  .v {{ fill:{FG}; }}
  .logo {{ fill:{CYAN}; white-space:pre; }}
</style>''')

# Fond + bordure (fenetre terminal)
parts.append(
    f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="10" '
    f'fill="{BG}" stroke="{BORDER}" stroke-width="1.5"/>'
)
# Barre de titre
parts.append(f'<rect x="1" y="1" width="{width-2}" height="34" rx="10" fill="#161b22"/>')
parts.append(f'<rect x="1" y="20" width="{width-2}" height="15" fill="#161b22"/>')
for i, c in enumerate((RED, YELLOW, GREEN)):
    parts.append(f'<circle cx="{22+i*20}" cy="18" r="6" fill="{c}"/>')
parts.append(
    f'<text x="{width/2}" y="23" text-anchor="middle" fill="{DIM}" font-size="13">'
    f'{escape(USER)}@profile: {escape(TITLE)}</text>'
)

# Logo (gauche) : avatar ASCII couleur, ou logo statique en repli.
if avatar:
    av_top = TOP + LINE_H          # aligne le haut de l'avatar avec l'info
    for r, line in enumerate(avatar):
        y = av_top + r * AV_CH
        delay = r * 0.05
        spans = []
        for c, (ch, color) in enumerate(line):
            if ch == " ":
                continue
            x = LOGO_X + c * AV_CW
            spans.append(f'<tspan x="{x:.1f}" y="{y:.1f}" fill="{color}">{escape(ch)}</tspan>')
        if spans:
            parts.append(
                f'<text class="row" font-size="{AV_FS}" xml:space="preserve" '
                f'style="animation-delay:{delay:.2f}s">{"".join(spans)}</text>'
            )
else:
    for i, line in enumerate(logo_lines):
        y = TOP + (i + 1) * LINE_H
        delay = i * 0.08
        parts.append(
            f'<text class="row logo" x="{LOGO_X}" y="{y}" xml:space="preserve" '
            f'style="animation-delay:{delay:.2f}s">{escape(line)}</text>'
        )

# En-tete "user@profile" + ligne de separation (droite)
def row(y, delay, content):
    return (f'<g class="row" style="animation-delay:{delay:.2f}s">'
            f'<text x="{INFO_X}" y="{y}">{content}</text></g>')

y0 = TOP + LINE_H
parts.append(row(y0, 0.0,
    f'<tspan class="k">{escape(USER)}</tspan>'
    f'<tspan class="v">@</tspan>'
    f'<tspan fill="{CYAN}">profile</tspan>'))
parts.append(row(y0 + LINE_H, 0.12,
    f'<tspan class="v">{"—" * 22}</tspan>'))

# Lignes d'info (valeurs longues coupees sur plusieurs lignes)
for i, (value_x, label, chunk) in enumerate(info_rows):
    y = y0 + (i + 2) * LINE_H
    delay = 0.24 + i * 0.12
    if label is not None:
        # Premiere ligne d'une info : "cle: valeur..."
        parts.append(row(y, delay,
            f'<tspan class="k">{escape(label)}</tspan>'
            f'<tspan class="v">: {escape(chunk)}</tspan>'))
    else:
        # Suite d'une valeur : alignee sous le debut de la valeur.
        parts.append(
            f'<g class="row" style="animation-delay:{delay:.2f}s">'
            f'<text x="{value_x:.0f}" y="{y}"><tspan class="v">{escape(chunk)}</tspan></text></g>')

parts.append('</svg>')

with open("info-card.svg", "w", encoding="utf-8") as f:
    f.write("\n".join(parts))

print("info-card.svg genere.")
