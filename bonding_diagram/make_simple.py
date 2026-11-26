"""Simple W2W vs C2W bonding illustration (DRAM on Logic) -> SVG -> PNG via Node Playwright."""
import pathlib, subprocess

W, H = 1600, 800
FONT = "'Noto Sans KR','Noto Sans CJK KR',sans-serif"
K = 0.42                       # vertical squash for the tilted view
DRAM = dict(face="#5b7fe0", die="#7d9bec", line="#3f61c4", side="#3552a8")
LOGIC = dict(face="#e8893a", die="#f2a965", line="#c96d22", side="#b35f1c")
INK, MUTED = "#1f2430", "#5b6472"
out, uid = [], [0]
add = out.append

def text(x, y, s, size=20, color=INK, weight="normal", anchor="middle"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" '
        f'text-anchor="{anchor}" font-family="{FONT}">{s}</text>')

def P(cx, cy, u, v, lift=0):
    return f"{cx + u:.1f},{cy + v * K - lift:.1f}"

def dies(R, d):
    n = int(R // d) + 1
    for i in range(-n, n):
        for j in range(-n, n):
            u0, v0 = i * d, j * d
            if all((u) ** 2 + (v) ** 2 <= (R - 6) ** 2 for u in (u0, u0 + d) for v in (v0, v0 + d)):
                yield u0, v0

def wafer(cx, cy, R, c, t=14, d=34, grid=True):
    # side band
    add(f'<path d="M{cx - R},{cy} A{R},{R * K} 0 0 0 {cx + R},{cy} L{cx + R},{cy + t} '
        f'A{R},{R * K} 0 0 1 {cx - R},{cy + t} Z" fill="{c["side"]}"/>')
    add(f'<ellipse cx="{cx}" cy="{cy}" rx="{R}" ry="{R * K}" fill="{c["face"]}"/>')
    if grid:
        for u, v in dies(R, d):
            pts = " ".join(P(cx, cy, a, b) for a, b in [(u + 2, v + 2), (u + d - 2, v + 2), (u + d - 2, v + d - 2), (u + 2, v + d - 2)])
            add(f'<polygon points="{pts}" fill="{c["die"]}" stroke="{c["line"]}" stroke-width="0.8"/>')
    # notch
    add(f'<circle cx="{cx}" cy="{cy + R * K - 2}" r="4" fill="{c["side"]}"/>')

def chip(cx, cy, u, v, d, c, h=9, inset=4):
    a, b = u + inset, v + inset
    e = d - 2 * inset
    top = " ".join(P(cx, cy, x, y, h) for x, y in [(a, b), (a + e, b), (a + e, b + e), (a, b + e)])
    front = " ".join([P(cx, cy, a, b + e, h), P(cx, cy, a + e, b + e, h), P(cx, cy, a + e, b + e), P(cx, cy, a, b + e)])
    add(f'<polygon points="{front}" fill="{c["side"]}"/>')
    add(f'<polygon points="{top}" fill="{c["die"]}" stroke="{c["line"]}" stroke-width="1"/>')

def plus(x, y):
    text(x, y + 16, "+", 54, MUTED, "bold")

def arrow(x1, x2, y):
    add(f'<line x1="{x1}" y1="{y}" x2="{x2 - 14}" y2="{y}" stroke="{INK}" stroke-width="5"/>')
    add(f'<path d="M{x2},{y} L{x2 - 22},{y - 13} L{x2 - 22},{y + 13} Z" fill="{INK}"/>')

add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
add(f'<rect width="{W}" height="{H}" fill="#ffffff"/>')

R, D = 170, 44
rows = [(75, 210, "Wafer-to-Wafer Bonding"), (455, 590, "Chip-to-Wafer Bonding")]
for (ty, cy, title), bg in zip(rows, ["#f3f6fd", "#f6f2fc"]):
    add(f'<rect x="30" y="{ty - 45}" width="{W - 60}" height="335" rx="18" fill="{bg}"/>')
    text(70, ty, title, 30, INK, "bold", "start")

# ---------- Row 1: W2W ----------
cy = rows[0][1]
wafer(250, cy, R, DRAM); text(250, cy + 130, "DRAM Wafer", 24, DRAM["side"], "bold")
plus(490, cy)
wafer(730, cy, R, LOGIC); text(730, cy + 130, "Logic Wafer", 24, LOGIC["side"], "bold")
arrow(940, 1060, cy)
wafer(1300, cy + 16, R, LOGIC, grid=False)
wafer(1300, cy, R, DRAM)
text(1300, cy + 130, "DRAM on Logic Wafer", 24, INK, "bold")

# ---------- Row 2: C2W ----------
cy = rows[1][1]
cd = 48
for i, (u, v) in enumerate([(-80, -70), (-20, -70), (40, -70), (-110, 10), (-50, 10), (10, 10), (70, 10),
                            (-80, 90), (-20, 90), (40, 90)]):
    chip(250, cy - 10, u, v, cd, DRAM, h=12)
text(250, cy + 130, "DRAM Chips", 24, DRAM["side"], "bold")
plus(490, cy)
wafer(730, cy, R, LOGIC, d=D); text(730, cy + 130, "Logic Wafer", 24, LOGIC["side"], "bold")
arrow(940, 1060, cy)
wafer(1300, cy, R, LOGIC, d=D)
for u, v in sorted(dies(R, D), key=lambda p: p[1]):
    chip(1300, cy, u, v, D, DRAM, h=5, inset=6)
text(1300, cy + 130, "DRAM Chips on Logic Wafer", 24, INK, "bold")
add("</svg>")

here = pathlib.Path(__file__).parent.resolve()
svgp, pngp = here / "w2w_c2w_simple.svg", here / "w2w_c2w_simple.png"
svgp.write_text("\n".join(out), encoding="utf-8")
js = f"""const {{ chromium }} = require('playwright');
(async () => {{ const b = await chromium.launch();
  const pg = await b.newPage({{ viewport: {{ width: {W}, height: {H} }}, deviceScaleFactor: 2 }});
  await pg.goto('file://{svgp}'); await pg.screenshot({{ path: '{pngp}' }}); await b.close(); }})();"""
subprocess.run(["node", "-e", js], check=True)
