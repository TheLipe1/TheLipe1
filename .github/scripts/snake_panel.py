"""Wraps the Platane/snk snake SVG in a space HUD panel matching the profile style.

Usage: python3 snake_panel.py <snake.svg> <out.svg>
"""
import random
import re
import sys

SPACE, CARD = "#070812", "#0b0c1a"
C1, C2, C3 = "#22d3ee", "#8b5cf6", "#f472b6"
MONO = "'Cascadia Code','Fira Code',Consolas,'Courier New',monospace"
PAD, W, H, CUT = 12, 1000, 250, 26


def lerp_hex(a, b, t):
    a, b = [int(a[i:i + 2], 16) for i in (1, 3, 5)], [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(a, b))


def ramp(t):
    return lerp_hex(C1, C2, t * 2) if t < .5 else lerp_hex(C2, C3, (t - .5) * 2)


def grad(id_):
    def stop(off, vals):
        return (f'<stop offset="{off}" stop-color="{vals.split(";")[0]}">'
                f'<animate attributeName="stop-color" values="{vals}" dur="8s" repeatCount="indefinite"/></stop>')
    return (f'<linearGradient id="{id_}" x1="0" y1="0" x2="1" y2="0">'
            + stop("0", f"{C1};{C2};{C3};{C1}") + stop(".5", f"{C2};{C3};{C1};{C2}")
            + stop("1", f"{C3};{C1};{C2};{C3}") + "</linearGradient>")


def chamfer(w, h, c, cut, i=0):
    pts = [(c + i, i)] if "tl" in cut else [(i, i)]
    pts += [(w - c - i, i), (w - i, c + i)] if "tr" in cut else [(w - i, i)]
    pts += [(w - i, h - c - i), (w - c - i, h - i)] if "br" in cut else [(w - i, h - i)]
    pts += [(c + i, h - i), (i, h - c - i)] if "bl" in cut else [(i, h - i)]
    if "tl" in cut:
        pts += [(i, c + i)]
    return "M" + " L".join(f"{x:g} {y:g}" for x, y in pts) + "Z"


def cut_edges(w, h, c, cut):
    seg = {"tl": (c + 1, 1, 1, c + 1), "br": (w - 1, h - c - 1, w - c - 1, h - 1),
           "tr": (w - c - 1, 1, w - 1, c + 1), "bl": (c + 1, h - 1, 1, h - c - 1)}
    out = ""
    for k in cut:
        x1, y1, x2, y2 = seg[k]
        out += (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="url(#pgb)" stroke-width="6" stroke-linecap="round" filter="url(#peg)">'
                f'<animate attributeName="opacity" values=".9;.4;.9" dur="3s" repeatCount="indefinite"/></line>'
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round"/>')
    return out


def stars(w, h, n, seed):
    r = random.Random(seed)
    out = ""
    for _ in range(n):
        x, y, o = r.uniform(0, w), r.uniform(0, h), r.uniform(.3, .9)
        out += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r.choice([.5, .7, .9, 1.2])}" fill="#ffffff" opacity="{o:.2f}">'
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


def restyle_snake(src):
    # remove the progress bar under the grid
    src = re.sub(r'<rect class="u[^"]*"[^>]*/>', "", src)
    # round cells -> star-like dots
    src = re.sub(r'(<rect class="c[^"]*"[^>]*?) rx="[\d.]+" ry="[\d.]+"', r'\1 rx="6" ry="6"', src)
    # complete the grid: fill days that don't exist yet (current/first week) with empty dots
    cells = {(float(x), float(y)) for x, y in re.findall(r'<rect class="c[^"]*" x="([\d.]+)" y="([\d.]+)"', src)}
    if cells:
        xs, ys = sorted({x for x, _ in cells}), sorted({y for _, y in cells})
        filler = "".join(f'<rect class="c" x="{x:g}" y="{y:g}" rx="6" ry="6"/>'
                         for x in xs for y in ys if (x, y) not in cells)
        src = src.replace('<rect class="s s0"', filler + '<rect class="s s0"', 1)
    # gradient snake (head cyan -> tail pink) with glow
    segs = re.findall(r'<rect class="s s(\d+)"', src)
    n = max(len(segs) - 1, 1)
    def paint(m):
        i = int(m.group(1))
        return f'<rect style="fill:{ramp(i / n)};filter:url(#psg)" class="s s{i}"'
    src = re.sub(r'<rect class="s s(\d+)"', paint, src)
    # crop away the bar area and place inside the panel
    src = re.sub(r'<svg viewBox="[^"]*" width="[^"]*" height="[^"]*"',
                 '<svg viewBox="-16 -24 880 152" x="60" y="72" width="880" height="152"', src, count=1)
    src = re.sub(r"<desc>.*?</desc>", "", src)
    return src


def main(inp, out):
    snake = restyle_snake(open(inp, encoding="utf-8").read())
    cut = {"tl", "br"}
    body = f'''
<g clip-path="url(#pclip)">
  <rect width="{W}" height="{H}" fill="{CARD}"/>
  <ellipse cx="500" cy="150" rx="520" ry="120" fill="{C2}" opacity=".14" filter="url(#pblur)"/>
  {stars(W, H, 80, 31)}
</g>
<path d="{chamfer(W, H, CUT, cut, 1)}" stroke="url(#pgb)" stroke-opacity=".75" stroke-width="1.5" stroke-linejoin="round"/>
{cut_edges(W, H, CUT, cut)}
<text x="30" y="44" font-family="{MONO}" font-size="13" font-weight="700" fill="#ffffff" fill-opacity=".55">05</text>
<text x="58" y="44" font-family="{MONO}" font-size="13" letter-spacing="4" fill="#ffffff">ACTIVITY</text>
<rect x="30" y="54" width="22" height="2" fill="url(#pgb)"/>
{eq_bars(W - 62, 46)}
{snake}'''
    defs = (grad("pgb")
            + f'<clipPath id="pclip"><path d="{chamfer(W, H, CUT, cut)}"/></clipPath>'
            + '<filter id="pblur" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="40"/></filter>'
            + '<filter id="peg" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="3"/></filter>'
            + '<filter id="psg" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="1.6" result="b"/>'
              '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W + 2 * PAD}" height="{H + 2 * PAD}" '
           f'viewBox="0 0 {W + 2 * PAD} {H + 2 * PAD}" fill="none"><defs>{defs}</defs>'
           f'<g transform="translate({PAD} {PAD})">{body}</g></svg>')
    open(out, "w", encoding="utf-8").write(svg)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
