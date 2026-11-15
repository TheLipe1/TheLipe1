"""Space shooter activity panel: a ship patrols under the contribution grid and shoots
every day with contributions. Output is an animated SVG in the profile's HUD style.

Usage:
  GITHUB_TOKEN=... python3 space_shooter.py <login> <out.svg>
  python3 space_shooter.py --demo <out.svg>        # random data, for local preview
"""
import json
import math
import os
import random
import sys
import urllib.request

SPACE, CARD = "#070812", "#0b0c1a"
C1, C2, C3 = "#22d3ee", "#8b5cf6", "#f472b6"
LEVEL_COLORS = {1: "#7c3aed", 2: "#8b5cf6", 3: C1, 4: C3}
EMPTY = "#23264a"
MONO = "'Cascadia Code','Fira Code',Consolas,'Courier New',monospace"
PAD, W, H, CUT = 12, 1000, 270, 26
COLS, ROWS, STEP, R = 53, 7, 15, 4.6
GX0 = (W - (COLS - 1) * STEP) / 2
GY0 = 82
SHIP_Y = 228
T = 16.0                      # loop duration (s)
SWEEP = 0.78                  # fraction of the loop used by the left->right attack run
BULLET = 0.28 / T             # bullet travel time (fraction)

LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


# ------------------------------------------------------------------ data
def fetch_grid(login, token):
    query = """query($login:String!){user(login:$login){contributionsCollection{contributionCalendar{
      weeks{contributionDays{weekday contributionLevel}}}}}}"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-space-shooter"})
    data = json.load(urllib.request.urlopen(req, timeout=30))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = {}
    for c, week in enumerate(weeks[-COLS:]):
        for day in week["contributionDays"]:
            grid[(c, day["weekday"])] = LEVELS.get(day["contributionLevel"], 0)
    return grid


def demo_grid():
    r = random.Random(4)
    return {(c, d): (r.choice([1, 2, 3, 4]) if r.random() < .06 else 0) for c in range(COLS) for d in range(ROWS)}


# ------------------------------------------------------------------ helpers
def f(x):
    return f"{x:.4f}".rstrip("0").rstrip(".") if x not in (0, 1) else str(int(x))


def times(*ts):
    """keyTimes strictly increasing, clamped to [0,1]."""
    out, prev = [], -1.0
    for t in ts:
        t = min(max(t, 0.0), 1.0)
        if t <= prev:
            t = prev + 1e-4
        out.append(min(t, 1.0))
        prev = out[-1]
    out[-1] = 1.0
    return ";".join(f(t) for t in out)


def anim(attr, values, key_times, extra=""):
    return (f'<animate attributeName="{attr}" values="{values}" keyTimes="{key_times}" '
            f'dur="{T}s" repeatCount="indefinite" {extra}/>')


def chamfer(w, h, c, cut, i=0):
    pts = [(c + i, i)] if "tl" in cut else [(i, i)]
    pts += [(w - c - i, i), (w - i, c + i)] if "tr" in cut else [(w - i, i)]
    pts += [(w - i, h - c - i), (w - c - i, h - i)] if "br" in cut else [(w - i, h - i)]
    pts += [(c + i, h - i), (i, h - c - i)] if "bl" in cut else [(i, h - i)]
    if "tl" in cut:
        pts += [(i, c + i)]
    return "M" + " L".join(f"{x:g} {y:g}" for x, y in pts) + "Z"


def cut_edges(w, h, c, cut):
    seg = {"tl": (c + 1, 1, 1, c + 1), "br": (w - 1, h - c - 1, w - c - 1, h - 1)}
    out = ""
    for k in cut:
        x1, y1, x2, y2 = seg[k]
        out += (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="url(#gb)" stroke-width="6" stroke-linecap="round" filter="url(#eg)">'
                f'<animate attributeName="opacity" values=".9;.4;.9" dur="3s" repeatCount="indefinite"/></line>'
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>')
    return out


def stars(n, seed):
    r = random.Random(seed)
    out = ""
    for _ in range(n):
        x, y, o = r.uniform(0, W), r.uniform(0, H), r.uniform(.3, .9)
        out += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r.choice([.5, .7, .9, 1.2])}" fill="#fff" opacity="{o:.2f}">'
                f'<animate attributeName="opacity" values="{o:.2f};{o * .15:.2f};{o:.2f}" dur="{r.uniform(2, 6):.1f}s" '
                f'begin="-{r.uniform(0, 6):.1f}s" repeatCount="indefinite"/></circle>')
    return out


def eq_bars(x, y):
    out = ""
    for i in range(5):
        r = random.Random(i * 13)
        vals = [r.choice([4, 12, 7, 14, 5, 10]) for _ in range(5)]
        vals.append(vals[0])
        d = f"{1.6 + i * .2:.1f}s"
        out += (f'<rect x="{x + i * 6}" y="{y - 14}" width="3" height="14" rx="1.5" fill="#ffffff" opacity=".55">'
                f'<animate attributeName="height" values="{";".join(map(str, vals))}" dur="{d}" repeatCount="indefinite"/>'
                f'<animate attributeName="y" values="{";".join(str(y - v) for v in vals)}" dur="{d}" repeatCount="indefinite"/></rect>')
    return out


def grad(id_):
    def stop(off, vals):
        return (f'<stop offset="{off}" stop-color="{vals.split(";")[0]}">'
                f'<animate attributeName="stop-color" values="{vals}" dur="8s" repeatCount="indefinite"/></stop>')
    return (f'<linearGradient id="{id_}" x1="0" y1="0" x2="1" y2="0">'
            + stop("0", f"{C1};{C2};{C3};{C1}") + stop(".5", f"{C2};{C3};{C1};{C2}")
            + stop("1", f"{C3};{C1};{C2};{C3}") + "</linearGradient>")


# ------------------------------------------------------------------ scene
def build(grid):
    xs_ship, xe_ship = GX0 - 40, GX0 + (COLS - 1) * STEP + 40

    def t_at(x):  # moment (fraction) the ship is under column x during the attack run
        return SWEEP * (x - xs_ship) / (xe_ship - xs_ship)

    respawn = 0.93
    dots, enemies, shots, booms = "", "", "", ""
    for c in range(COLS):
        cx = GX0 + c * STEP
        targets = sorted([d for d in range(ROWS) if grid.get((c, d), 0) > 0], reverse=True)  # bottom first
        for d in range(ROWS):  # full grid of empty dots (targets sit on top of them)
            dots += f'<circle cx="{cx:g}" cy="{GY0 + d * STEP:g}" r="{R}" fill="{EMPTY}"/>'
        for k, d in enumerate(targets):
            cy = GY0 + d * STEP
            col = LEVEL_COLORS[grid[(c, d)]]
            fire = t_at(cx) + k * (0.09 / T)
            hit = fire + BULLET * (SHIP_Y - cy) / (SHIP_Y - GY0)
            # enemy: glowing dot that flashes and vanishes when hit, respawns at the end
            enemies += (f'<g><circle cx="{cx:g}" cy="{cy:g}" r="{R + 3}" fill="{col}" opacity=".35" filter="url(#sg)"/>'
                        f'<circle cx="{cx:g}" cy="{cy:g}" r="{R}" fill="{col}"/>'
                        + anim("opacity", "1;1;1;0;0;1", times(0, hit, hit + .004, hit + .02, respawn, 1))
                        + "</g>")
            # laser
            shots += (f'<rect x="{cx - 1.5:g}" width="3" height="14" rx="1.5" fill="url(#laser)" y="{SHIP_Y - 18}" opacity="0">'
                      + anim("y", f"{SHIP_Y - 18};{SHIP_Y - 18};{cy - 6:g};{cy - 6:g}", times(0, fire, hit, 1))
                      + anim("opacity", "0;0;1;1;0;0", times(0, fire, fire + .002, hit, hit + .002, 1))
                      + "</rect>")
            shots += (f'<circle cx="{cx:g}" cy="{SHIP_Y - 24}" r="0" fill="#ffffff" opacity="0">'
                      + anim("r", "0;0;6;0;0", times(0, fire, fire + .004, fire + .012, 1))
                      + anim("opacity", "0;0;1;0;0", times(0, fire, fire + .002, fire + .012, 1))
                      + "</circle>")
            # explosion: flash ring + particles
            booms += (f'<circle cx="{cx:g}" cy="{cy:g}" r="2" fill="none" stroke="#ffffff" stroke-width="2" opacity="0">'
                      + anim("r", "2;2;14;14", times(0, hit, hit + .03, 1))
                      + anim("opacity", "0;0;1;0;0", times(0, hit, hit + .003, hit + .03, 1))
                      + "</circle>")
            r = random.Random(c * 10 + d)
            for p in range(6):
                ang = p * 60 + r.uniform(-20, 20)
                dx, dy = math.cos(math.radians(ang)) * r.uniform(10, 18), math.sin(math.radians(ang)) * r.uniform(10, 18)
                booms += (f'<circle cx="{cx:g}" cy="{cy:g}" r="1.6" fill="{col}" opacity="0">'
                          + f'<animateTransform attributeName="transform" type="translate" values="0 0;0 0;{dx:.1f} {dy:.1f};{dx:.1f} {dy:.1f}" '
                            f'keyTimes="{times(0, hit, hit + .04, 1)}" dur="{T}s" repeatCount="indefinite"/>'
                          + anim("opacity", "0;0;1;0;0", times(0, hit, hit + .003, hit + .04, 1))
                          + "</circle>")

    def flame(x):
        return (f'<path d="M{x - 2.6} 13 L{x} 22 L{x + 2.6} 13Z" fill="{C1}" opacity=".95">'
                f'<animate attributeName="d" values="M{x - 2.6} 13 L{x} 22 L{x + 2.6} 13Z;M{x - 2.2} 13 L{x} 29 L{x + 2.2} 13Z;M{x - 2.6} 13 L{x} 22 L{x + 2.6} 13Z" dur=".22s" repeatCount="indefinite"/></path>'
                f'<path d="M{x - 1.2} 13 L{x} 18 L{x + 1.2} 13Z" fill="#ffffff"/>')

    exhaust = "".join(
        f'<circle cx="{x}" cy="16" r="1.4" fill="{C1}">'
        f'<animate attributeName="cy" values="16;34" dur=".7s" begin="{i * .23:.2f}s" repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values=".9;0" dur=".7s" begin="{i * .23:.2f}s" repeatCount="indefinite"/></circle>'
        for i, x in enumerate([-4, 4, 0]))

    ship = f'''
<g>
  <animateTransform attributeName="transform" type="translate" values="{xs_ship:g} {SHIP_Y};{xe_ship:g} {SHIP_Y};{xs_ship:g} {SHIP_Y}"
    keyTimes="0;{SWEEP};1" dur="{T}s" repeatCount="indefinite"/>
  <g>
    <animateTransform attributeName="transform" type="translate" values="0 0;0 -2;0 0" dur="1.2s" repeatCount="indefinite"/>
    <circle cy="2" r="26" fill="{C2}" opacity=".28" filter="url(#sg)"/>
    {exhaust}{flame(-4)}{flame(4)}
    <!-- asas -->
    <path d="M5 -2 L22 9 L23 16 L6 12Z" fill="url(#wing)" stroke="#ffffff" stroke-opacity=".45" stroke-width=".8" stroke-linejoin="round"/>
    <path d="M-5 -2 L-22 9 L-23 16 L-6 12Z" fill="url(#wing)" stroke="#ffffff" stroke-opacity=".45" stroke-width=".8" stroke-linejoin="round"/>
    <path d="M9 4 L19 11 M-9 4 L-19 11" stroke="#ffffff" stroke-opacity=".35" stroke-width=".8"/>
    <!-- canhões e luzes nas pontas -->
    <rect x="21.5" y="2" width="2" height="9" rx="1" fill="#e6e9f2"/><rect x="-23.5" y="2" width="2" height="9" rx="1" fill="#e6e9f2"/>
    <circle cx="23" cy="16.5" r="1.8" fill="{C3}"><animate attributeName="opacity" values="1;.15;1" dur="1s" repeatCount="indefinite"/></circle>
    <circle cx="-23" cy="16.5" r="1.8" fill="{C1}"><animate attributeName="opacity" values=".15;1;.15" dur="1s" repeatCount="indefinite"/></circle>
    <!-- motores -->
    <rect x="-6.5" y="8" width="5" height="6" rx="1.5" fill="#1e1b4b" stroke="url(#ship)" stroke-width="1"/>
    <rect x="1.5" y="8" width="5" height="6" rx="1.5" fill="#1e1b4b" stroke="url(#ship)" stroke-width="1"/>
    <!-- fuselagem -->
    <path d="M0 -22 C4 -16 6.5 -8 6.5 1 L6.5 11 L-6.5 11 L-6.5 1 C-6.5 -8 -4 -16 0 -22Z" fill="url(#ship)" stroke="#ffffff" stroke-opacity=".7" stroke-width="1"/>
    <path d="M0 -15 V9" stroke="#ffffff" stroke-opacity=".25" stroke-width=".8"/>
    <!-- cabine -->
    <ellipse cx="0" cy="-7" rx="3.2" ry="6.5" fill="url(#glass)" stroke="#ffffff" stroke-opacity=".8" stroke-width=".7"/>
    <ellipse cx="-1" cy="-9.5" rx="1" ry="2.2" fill="#ffffff" opacity=".85"/>
  </g>
</g>'''

    cut = {"tl", "br"}
    body = f'''
<g clip-path="url(#pclip)">
  <rect width="{W}" height="{H}" fill="{CARD}"/>
  <ellipse cx="500" cy="150" rx="520" ry="130" fill="{C2}" opacity=".14" filter="url(#pblur)"/>
  {stars(90, 31)}
  {dots}{enemies}{booms}{shots}{ship}
</g>
<path d="{chamfer(W, H, CUT, cut, 1)}" stroke="url(#gb)" stroke-opacity=".75" stroke-width="1.5" stroke-linejoin="round"/>
{cut_edges(W, H, CUT, cut)}
<text x="30" y="44" font-family="{MONO}" font-size="13" font-weight="700" fill="#ffffff" fill-opacity=".55">05</text>
<text x="58" y="44" font-family="{MONO}" font-size="13" letter-spacing="4" fill="#ffffff">ACTIVITY</text>
<rect x="30" y="54" width="22" height="2" fill="url(#gb)"/>
{eq_bars(W - 62, 46)}'''
    defs = (grad("gb")
            + f'<linearGradient id="ship" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{C1}"/><stop offset=".6" stop-color="{C2}"/><stop offset="1" stop-color="{C3}"/></linearGradient>'
            + f'<linearGradient id="wing" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{C2}"/><stop offset="1" stop-color="{C3}"/></linearGradient>'
            + '<radialGradient id="glass" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#ffffff"/><stop offset=".45" stop-color="#a5f3fc"/><stop offset="1" stop-color="#0e7490"/></radialGradient>'
            + f'<linearGradient id="laser" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="{C1}" stop-opacity="0"/></linearGradient>'
            + f'<clipPath id="pclip"><path d="{chamfer(W, H, CUT, cut)}"/></clipPath>'
            + '<filter id="pblur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="40"/></filter>'
            + '<filter id="sg" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="4"/></filter>'
            + '<filter id="eg" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W + 2 * PAD}" height="{H + 2 * PAD}" '
            f'viewBox="0 0 {W + 2 * PAD} {H + 2 * PAD}" fill="none"><defs>{defs}</defs>'
            f'<g transform="translate({PAD} {PAD})">{body}</g></svg>')


def main():
    if sys.argv[1] == "--demo":
        grid, out = demo_grid(), sys.argv[2]
    else:
        login, out = sys.argv[1], sys.argv[2]
        try:
            grid = fetch_grid(login, os.environ["GITHUB_TOKEN"])
        except Exception as exc:  # keep the panel alive even if the API fails
            print(f"warning: could not fetch contributions ({exc}); rendering empty grid")
            grid = {}
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(build(grid))
    print(f"targets: {sum(1 for v in grid.values() if v)} -> {out}")


if __name__ == "__main__":
    main()
