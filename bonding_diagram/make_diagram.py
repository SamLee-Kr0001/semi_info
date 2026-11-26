"""Wafer-to-Wafer vs Chip-to-Wafer hybrid bonding diagram -> SVG -> PNG (Playwright)."""
import pathlib

W, H = 1600, 1470
FONT = "'Noto Sans KR','Noto Sans CJK KR',sans-serif"
SI, SI_DARK = "#c9ced6", "#9aa2ad"
TOP, BOT = "#4a6fd6", "#e8893a"          # device layers: top die (memory/sensor), bottom die (logic)
OX, CU = "#eef1f7", "#b86b2a"            # bonding oxide, copper pads
GAP = "#d9cdf0"                           # gap fill
GOOD, BAD = "#2ca02c", "#d62728"
INK, MUTED = "#1f2430", "#5b6472"

out = []
def add(s): out.append(s)
def text(x, y, s, size=16, color=INK, anchor="start", weight="normal"):
    add(f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" text-anchor="{anchor}" '
        f'font-weight="{weight}" font-family="{FONT}">{s}</text>')
def rect(x, y, w, h, fill, stroke="none", sw=1, rx=0, extra=""):
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{fill}" stroke="{stroke}" '
        f'stroke-width="{sw}" rx="{rx}" {extra}/>')
def line(x1, y1, x2, y2, color=INK, sw=1.5, dash=None, arrow=False):
    d = f'stroke-dasharray="{dash}"' if dash else ""
    m = 'marker-end="url(#arr)"' if arrow else ""
    add(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" {d} {m}/>')

def bond_layer(x, y, w, pitch=14):
    rect(x, y, w, 6, OX)
    p = x + 4
    while p + 6 < x + w:
        rect(p, y + 1, 6, 4, CU); p += pitch

def die(x, y, w, si_h, dev, face="up", bond=True):
    """Cross-section of a die/wafer. face='up': device+bond on top; 'down': on bottom. Returns total height."""
    if face == "up":
        rect(x, y + 16, w, si_h, SI, SI_DARK, 0.8)
        rect(x, y + 6, w, 10, dev)
        if bond: bond_layer(x, y, w)
    else:
        rect(x, y, w, si_h, SI, SI_DARK, 0.8)
        rect(x, y + si_h, w, 10, dev)
        if bond: bond_layer(x, y + si_h + 10, w)
    return si_h + 16

def scribe(x, y, w, h, n):
    for i in range(1, n):
        xx = x + w * i / n
        line(xx, y - 4, xx, y + h + 4, MUTED, 1, "4 3")

def mark(x, y, ok, size=16):
    c = GOOD if ok else BAD
    text(x, y, "✓" if ok else "✕", size, c, "middle", "bold")

def tsv(x, y, w, h, n, pitch):
    for i in range(n):
        rect(x + pitch / 2 + i * pitch - 2, y, 4, h, CU)

# ---------- canvas ----------
add(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">')
add('<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
    'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#1f2430"/></marker></defs>')
rect(0, 0, W, H, "#ffffff")
text(W / 2, 48, "Wafer-to-Wafer vs Chip-to-Wafer 하이브리드 본딩", 30, INK, "middle", "bold")
text(W / 2, 80, "Cu–Cu + SiO₂–SiO₂ 직접 접합(범프 없음) · 단면 공정 흐름", 17, MUTED, "middle")

COLS = [(40, "Wafer-to-Wafer (W2W)", "웨이퍼 전체를 웨이퍼에 한 번에 접합", TOP),
        (820, "Chip-to-Wafer (C2W)", "양품 칩(KGD)을 골라 웨이퍼 위에 하나씩 접합", "#7b4fc9")]
CW = 740
for cx, title, sub, c in COLS:
    rect(cx, 105, CW, 64, c, rx=10)
    text(cx + CW / 2, 136, title, 22, "#fff", "middle", "bold")
    text(cx + CW / 2, 159, sub, 15, "#fff", "middle")

ROW0, RH = 190, 225
def step(cx, i, label):
    y = ROW0 + i * RH
    rect(cx, y, CW, RH - 14, "#f7f8fb", "#e2e5ec", 1, 8)
    add(f'<circle cx="{cx + 22}" cy="{y + 24}" r="13" fill="{INK}"/>')
    text(cx + 22, y + 29, str(i + 1), 14, "#fff", "middle", "bold")
    text(cx + 44, y + 30, label, 17, INK, "start", "bold")
    return y

# ================= W2W =================
L = 40; wx, ww = L + 70, 600
# 1
y = step(L, 0, "상·하부 웨이퍼 준비 (본딩층: 산화막 + Cu 패드)")
die(wx, y + 52, ww, 40, TOP, "down"); text(wx + ww + 10, y + 80, "Wafer A", 14, TOP, weight="bold")
text(wx + ww + 10, y + 97, "(메모리/센서)", 12, MUTED)
line(wx + ww / 2, y + 124, wx + ww / 2, y + 140, INK, 2, arrow=True)
text(wx + ww / 2 + 12, y + 137, "Face-to-Face", 12, MUTED)
die(wx, y + 146, ww, 40, BOT, "up"); text(wx + ww + 10, y + 175, "Wafer B", 14, BOT, weight="bold")
text(wx + ww + 10, y + 192, "(로직)", 12, MUTED)
# 2
y = step(L, 1, "웨이퍼 단위 정렬 → 상온 접합 → 어닐링 (Cu 확산 접합)")
die(wx, y + 52, ww, 40, TOP, "down", bond=True)
die(wx, y + 108, ww, 40, BOT, "up")
rect(wx - 6, y + 99, ww + 12, 18, "none", BAD, 2, 3, 'stroke-dasharray="5 3"')
text(wx + ww / 2, y + 196, "접합 계면: 웨이퍼 전면이 한 번에 결합 (정렬 오차 ≈ 0.1–0.2 µm)", 14, MUTED, "middle")
# 3
y = step(L, 2, "상부 웨이퍼 백그라인딩 → TSV 노출 · 재배선")
rect(wx, y + 70, ww, 14, SI, SI_DARK, 0.8)
rect(wx, y + 84, ww, 10, TOP); bond_layer(wx, y + 94, ww)
die(wx, y + 100, ww, 40, BOT, "up", bond=False)
tsv(wx, y + 70, ww, 24, 20, ww / 20)
rect(wx, y + 64, ww, 6, "#8a94a6")
text(wx + ww + 10, y + 82, "← 박막화", 13, MUTED)
text(wx + ww / 2, y + 190, "상부 Si 두께 수 µm 까지 연삭 (TSV로 신호 인출)", 14, MUTED, "middle")
# 4
y = step(L, 3, "다이싱 → 적층 다이")
n, gw, gap = 8, 64, 10
ok_top = [1, 1, 0, 1, 1, 1, 1, 1]; ok_bot = [1, 1, 1, 1, 0, 1, 1, 1]
for k in range(n):
    x = wx + k * (gw + gap) + 8
    good = ok_top[k] and ok_bot[k]
    rect(x, y + 70, gw, 10, TOP); rect(x, y + 80, gw, 6, OX); rect(x, y + 86, gw, 10, BOT)
    rect(x, y + 96, gw, 30, SI, SI_DARK, 0.8)
    if not ok_top[k]: mark(x + gw / 2, y + 66, False, 14)
    if not ok_bot[k]: mark(x + gw / 2, y + 116, False, 14)
    text(x + gw / 2, y + 150, "양품" if good else "폐기", 13, GOOD if good else BAD, "middle", "bold")
text(wx + ww / 2, y + 190, "한쪽 불량이어도 짝 다이와 함께 폐기 → 수율 = Y(A) × Y(B)", 14, BAD, "middle")

# ================= C2W =================
R = 820; rx_, rw = R + 70, 600
# 1
y = step(R, 0, "상부 웨이퍼 테스트(KGD 선별) → 다이싱")
die(rx_, y + 60, 280, 36, TOP, "up"); scribe(rx_, y + 60, 280, 52, 5)
for k, ok in enumerate([1, 0, 1, 1, 1]): mark(rx_ + 28 + k * 56, y + 136, ok)
line(rx_ + 300, y + 86, rx_ + 350, y + 86, INK, 2, arrow=True)
text(rx_ + 325, y + 76, "다이싱", 12, MUTED, "middle")
for k, ok in enumerate([1, 0, 1, 1, 1]):
    x = rx_ + 365 + k * 48
    die(x, y + 66, 40, 26, TOP, "up"); mark(x + 20, y + 136, ok)
text(rx_ + ww / 2, y + 190, "양품 칩만 사용 (Known Good Die)", 14, GOOD, "middle")
# 2
y = step(R, 1, "KGD 픽앤플레이스 (뒤집어서 칩 단위 정렬·접합)")
die(rx_, y + 124, rw, 40, BOT, "up"); scribe(rx_, y + 124, rw, 56, 6)
cell = rw / 6; cwid = 64
for k in range(3):
    x = rx_ + k * cell + (cell - cwid) / 2
    die(x, y + 88, cwid, 20, TOP, "down")
x = rx_ + 3 * cell + (cell - cwid) / 2
rect(x - 8, y + 40, cwid + 16, 16, "#5b6472", rx=3); text(x + cwid / 2, y + 52, "Bond head", 11, "#fff", "middle")
die(x, y + 56, cwid, 20, TOP, "down")
line(x + cwid / 2, y + 96, x + cwid / 2, y + 116, INK, 2, arrow=True)
text(rx_ + ww / 2, y + 198, "칩마다 개별 정렬 (정렬 오차 ≈ 0.5–1 µm) · 하부 다이보다 작은 칩도 가능", 14, MUTED, "middle")
# 3
y = step(R, 2, "어닐링 → 갭필(산화막/몰드) → 상부 칩 박막화")
die(rx_, y + 110, rw, 40, BOT, "up", bond=False)
rect(rx_, y + 70, rw, 40, GAP)
for k in range(6):
    x = rx_ + k * cell + (cell - cwid) / 2
    rect(x, y + 80, cwid, 14, SI, SI_DARK, 0.8); rect(x, y + 94, cwid, 10, TOP); bond_layer(x, y + 104, cwid, 12)
    tsv(x, y + 80, cwid, 24, 4, cwid / 4)
text(rx_ + rw + 8, y + 92, "갭필", 13, "#7b4fc9", weight="bold")
text(rx_ + ww / 2, y + 190, "칩 사이 빈 공간을 채워 평탄화 후 연삭", 14, MUTED, "middle")
# 4
y = step(R, 3, "다이싱 → 적층 다이")
gw, gap = 88, 14
for k in range(6):
    x = rx_ + k * (gw + gap) + 4
    rect(x, y + 70, gw, 20, GAP); rect(x + 14, y + 72, gw - 28, 10, TOP)
    rect(x, y + 90, gw, 6, OX); rect(x, y + 96, gw, 10, BOT); rect(x, y + 106, gw, 26, SI, SI_DARK, 0.8)
    text(x + gw / 2, y + 156, "양품", 13, GOOD, "middle", "bold")
text(rx_ + ww / 2, y + 190, "양품 칩만 적층 → 수율 ≈ Y(B) · 상·하부 크기·공정 달라도 됨", 14, GOOD, "middle")

# ================= legend =================
ly = ROW0 + 4 * RH + 6
items = [(SI, "Si 기판"), (TOP, "상부 소자층 (메모리/센서)"), (BOT, "하부 소자층 (로직)"),
         (OX, "본딩 산화막 (SiO₂/SiCN)"), (CU, "Cu 패드 / TSV"), (GAP, "갭필")]
x = 60
for c, s in items:
    rect(x, ly, 22, 14, c, SI_DARK, 0.6); text(x + 30, ly + 12, s, 14, INK); x += 30 + len(s) * 13 + 40

# ================= comparison table =================
ty = ly + 40
rows = [("항목", "Wafer-to-Wafer", "Chip-to-Wafer"),
        ("접합 단위", "웨이퍼 ↔ 웨이퍼 (1회)", "칩 ↔ 웨이퍼 (칩 수만큼 반복)"),
        ("정렬 정밀도 / 피치", "≈0.1–0.2 µm / ~1 µm 이하 가능", "≈0.5–1 µm / 수 µm (~3–9 µm)"),
        ("처리량", "높음", "낮음 (집단 접합 D2W로 보완)"),
        ("수율", "Y(A)×Y(B) — KGD 선별 불가", "KGD만 적층 → 높음"),
        ("다이 크기·공정", "상·하부 동일 다이 크기·웨이퍼 크기", "크기·노드·웨이퍼 달라도 됨 (이종 집적)"),
        ("공정 난이도", "웨이퍼 휨(bow)·정렬 관리", "다이싱 파티클·칩 표면 청정도 관리"),
        ("대표 적용", "적층형 CIS, 3D NAND(CMOS 본딩 어레이)", "AMD 3D V-Cache(TSMC SoIC), 차세대 하이브리드 본딩 HBM")]
c0, c1, c2 = 40, 300, 930; rh = 38
for i, (a, b, c) in enumerate(rows):
    yy = ty + i * rh
    head = i == 0
    rect(40, yy, W - 80, rh, "#1f2430" if head else ("#f7f8fb" if i % 2 else "#ffffff"), "#e2e5ec", 1)
    col = "#fff" if head else INK
    text(c0 + 14, yy + 25, a, 15, col, weight="bold")
    text(c1, yy + 25, b, 15, "#fff" if head else INK, weight="bold" if head else "normal")
    text(c2, yy + 25, c, 15, "#fff" if head else INK, weight="bold" if head else "normal")
add("</svg>")

here = pathlib.Path(__file__).parent
svg = "\n".join(out)
(here / "w2w_vs_c2w.svg").write_text(svg, encoding="utf-8")

import subprocess
js = f"""
const {{ chromium }} = require('playwright');
(async () => {{
  const b = await chromium.launch();
  const pg = await b.newPage({{ viewport: {{ width: {W}, height: {H} }}, deviceScaleFactor: 2 }});
  await pg.goto('file://{(here / "w2w_vs_c2w.svg").resolve()}');
  await pg.screenshot({{ path: '{(here / "w2w_vs_c2w.png").resolve()}' }});
  await b.close();
}})();
"""
subprocess.run(["node", "-e", js], check=True)
