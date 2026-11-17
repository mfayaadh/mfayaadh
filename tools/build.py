#!/usr/bin/env python3
"""Builds the SVG assets for the GitHub profile README.

All artwork is original. Fonts (SIL Open Font License) are fetched from Google
Fonts, subset to the glyphs each SVG uses and embedded as WOFF2, because SVGs
rendered through <img> on GitHub cannot load external fonts.

    python3 -m venv .venv && .venv/bin/pip install fonttools brotli
    .venv/bin/python tools/build.py
"""
import base64, io, json, math, random, re, urllib.request
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools import subset

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / 'assets'
CACHE = ROOT / '.cache' / 'fonts'
ICONS = json.loads((ROOT / 'tools' / 'icons.json').read_text())
PORTRAIT = ROOT / 'tools' / 'portrait.webp'

RED, RED_HOT, RED_D, RED_DD, RED_DDD = '#e3001b', '#ff1f35', '#a50014', '#5c000b', '#2a0006'
INK, PAPER, YELLOW = '#0b0a0c', '#fbf7f0', '#ffe100'

FAMILIES = {
    'Anton': 'Anton',
    'Bowlby': 'Bowlby+One',
    'Marker': 'Permanent+Marker',
    'Abril': 'Abril+Fatface',
    'Barlow': 'Barlow+Condensed:wght@800',
    'Mono': 'JetBrains+Mono:wght@700',
}


# ---------------------------------------------------------------- fonts ----
def font_path(key):
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / f'{key}.ttf'
    if not p.exists():
        req = urllib.request.Request(f'https://fonts.googleapis.com/css2?family={FAMILIES[key]}',
                                     headers={'User-Agent': 'Mozilla/4.0'})
        css = urllib.request.urlopen(req).read().decode()
        url = re.search(r'url\((https://[^)]+\.ttf)\)', css).group(1)
        p.write_bytes(urllib.request.urlopen(url).read())
    return p


_fonts = {}
def tt(key):
    if key not in _fonts:
        _fonts[key] = TTFont(font_path(key))
    return _fonts[key]


def text_w(key, text, size, spacing=0):
    f = tt(key)
    cmap, hmtx, upm = f.getBestCmap(), f['hmtx'], f['head'].unitsPerEm
    w = 0
    for ch in text:
        g = cmap.get(ord(ch)) or cmap.get(ord('?'))
        w += hmtx[g][0]
    return w * size / upm + spacing * max(len(text) - 1, 0)


class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.parts, self.defs, self.used = w, h, [], [], {}

    def font(self, key, text):
        self.used.setdefault(key, set()).update(text)
        return f"F{key}"

    def text(self, x, y, s, key, size, fill, anchor='start', spacing=0, extra=''):
        fam = self.font(key, s)
        esc = s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        ls = f' letter-spacing="{spacing}"' if spacing else ''
        self.parts.append(f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" font-size="{size}" '
                          f'fill="{fill}" text-anchor="{anchor}"{ls} {extra}>{esc}</text>')

    def add(self, s):
        self.parts.append(s)

    def render(self, title):
        faces = []
        for key, chars in sorted(self.used.items()):
            opts = subset.Options(); opts.flavor = 'woff2'; opts.layout_features = ['kern']
            sub = subset.Subsetter(opts)
            font = TTFont(font_path(key))
            sub.populate(text=''.join(sorted(chars)) + ' ')
            sub.subset(font)
            buf = io.BytesIO(); font.flavor = 'woff2'; font.save(buf)
            b64 = base64.b64encode(buf.getvalue()).decode()
            faces.append(f"@font-face{{font-family:F{key};src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
        style = f"<style>{''.join(faces)}</style>"
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" role="img">'
                f'<title>{title}</title>{style}<defs>{"".join(self.defs)}</defs>{"".join(self.parts)}</svg>')


def save(name, svg):
    (ASSETS / name).write_text(svg)
    print(f'  {name:28s} {len(svg) // 1024:>4} KB')


STAR = '50,4 62,36 96,38 69,59 79,94 50,74 21,94 31,59 4,38 38,36'
def star(x, y, size, fill, stroke=None, sw=0, extra=''):
    pts = ' '.join(f'{x + float(a) * size / 100:.1f},{y + float(b) * size / 100:.1f}'
                   for a, b in (p.split(',') for p in STAR.split()))
    st = f' stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"' if stroke else ''
    return f'<polygon points="{pts}" fill="{fill}"{st} {extra}/>'


MAZE = ('<pattern id="maze" width="180" height="180" patternUnits="userSpaceOnUse">'
        '<g fill="none" stroke="#000" stroke-width="6" stroke-linecap="round">'
        '<path d="M8 26q18-22 36 0t36 0"/><path d="M110 14c22 4 24 30 46 30"/>'
        '<path d="M30 84a22 22 0 1 1 30 20"/><path d="M96 78q16 18 32 0t32 0"/>'
        '<path d="M14 146c10-18 30-18 40 0s30 18 40 0"/><path d="M128 128a16 16 0 1 0 22 22"/>'
        '<path d="M150 170q12-14 24 0"/></g></pattern>')
SKYLINE = ('M0,260V170h40v-40h30v-50h46v90h24v-60h38v-30h18v30h22v120h20V110l40-30 40,30v90h26v-70h52v-40h20v-34h12v34h20v40h30v100h22V140h60v-50h36v30h28V60h14V20h6v40h14v60h28v-30h40v110h30v-80h56v40h34V90h18V50h24v40h18v110h26v-70h44V80l30-20 30,20v70h26v-40h50v60h20V70h22V30h8v40h22v130h28v-80h40v-30h52v120h24v-60h50v80h30v-120h44v100h36v80z')


# ------------------------------------------------------------- ransom ----
VARIANTS = [  # bg, fg, font, shadow
    (PAPER, INK, 'Bowlby', INK),
    (INK, PAPER, 'Abril', PAPER),
    (None, PAPER, 'Marker', INK),
    (PAPER, RED, 'Anton', INK),
    (RED, PAPER, 'Anton', INK),
    (INK, PAPER, 'Bowlby', RED),
]

def ransom(svg, x, y, word, size, seed, animate=True, delay=0.0):
    """Draw cut-out letters starting at (x, baseline y). Returns end x."""
    rnd = random.Random(seed)
    prev = -1
    cx = x
    for i, ch in enumerate(word):
        if ch == ' ':
            cx += size * .35
            continue
        v = prev
        while v == prev:
            v = rnd.randrange(len(VARIANTS))
        prev = v
        bg, fg, key, sh = VARIANTS[v]
        s = size * (1.2 if i == 0 else rnd.uniform(.86, 1.06))
        w = text_w(key, ch, s) + s * .16
        h = s * 1.12
        rot = rnd.uniform(-9, 9)
        dy = rnd.uniform(-.06, .06) * size
        top = y - s * .92 + dy
        mid_x, mid_y = cx + w / 2, top + h / 2
        g = [f'<g transform="rotate({rot:.1f} {mid_x:.1f} {mid_y:.1f})">']
        if animate:
            amp = rnd.uniform(2.5, 5) * (1 if i % 2 else -1)
            dur = rnd.uniform(2.2, 3.4)
            g.append(f'<animateTransform attributeName="transform" type="rotate" additive="sum" '
                     f'values="0 {mid_x:.1f} {mid_y:.1f};{amp:.1f} {mid_x:.1f} {mid_y:.1f};0 {mid_x:.1f} {mid_y:.1f}" '
                     f'dur="{dur:.2f}s" begin="{delay + i * .07:.2f}s" repeatCount="indefinite"/>')
        if bg:
            j = [rnd.uniform(0, .07) * w for _ in range(4)]
            poly = f'{cx + j[0]:.1f},{top:.1f} {cx + w:.1f},{top + j[1]:.1f} {cx + w - j[2]:.1f},{top + h:.1f} {cx:.1f},{top + h - j[3]:.1f}'
            g.append(f'<polygon points="{poly}" fill="{sh}" transform="translate(3 3)"/>')
            g.append(f'<polygon points="{poly}" fill="{bg}"/>')
            fam = svg.font(key, ch)
            g.append(f'<text x="{mid_x:.1f}" y="{top + h * .82:.1f}" font-family="{fam}" font-size="{s:.1f}" fill="{fg}" text-anchor="middle">{ch}</text>')
        else:
            fam = svg.font(key, ch)
            g.append(f'<text x="{mid_x + 3:.1f}" y="{top + h * .82 + 3:.1f}" font-family="{fam}" font-size="{s:.1f}" fill="{sh}" text-anchor="middle">{ch}</text>')
            g.append(f'<text x="{mid_x:.1f}" y="{top + h * .82:.1f}" font-family="{fam}" font-size="{s:.1f}" fill="{fg}" text-anchor="middle">{ch}</text>')
        g.append('</g>')
        svg.add(''.join(g))
        cx += w + size * .05
    return cx


# --------------------------------------------------------------- hero ----
def hero():
    W, H = 1280, 470
    s = Svg(W, H)
    s.defs.append(f'<radialGradient id="bg" cx="45%" cy="42%" r="75%"><stop offset="0" stop-color="{RED}"/>'
                  f'<stop offset=".55" stop-color="{RED}"/><stop offset="1" stop-color="{RED_D}"/></radialGradient>')
    s.defs.append(MAZE)
    s.defs.append(f'<clipPath id="frame"><rect width="{W}" height="{H}"/></clipPath>')
    s.add(f'<g clip-path="url(#frame)">')
    s.add(f'<rect width="{W}" height="{H}" fill="url(#bg)"/>')
    s.add(f'<rect width="{W}" height="{H}" fill="url(#maze)" opacity=".13"/>')

    # ring tunnel
    cx, cy = 560, 215
    for i in range(5):
        b = -i * 2.4
        s.add(f'<circle cx="{cx}" cy="{cy}" r="{100 + i * 150}" fill="none" stroke="{RED_DDD}" stroke-width="54" opacity=".8">'
              f'<animate attributeName="r" values="20;820" dur="12s" begin="{b}s" repeatCount="indefinite"/>'
              f'<animate attributeName="opacity" values="0;.95;.7;0" keyTimes="0;.12;.85;1" dur="12s" begin="{b}s" repeatCount="indefinite"/>'
              f'</circle>')

    # shards
    def shard(points, dx, dy, dur, delay):
        s.add(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;0 -10;0 0" '
              f'dur="{dur}s" begin="{delay}s" repeatCount="indefinite"/>'
              f'<polygon points="{points}" fill="{INK}" transform="translate({dx} {dy})"/>'
              f'<polygon points="{points}" fill="{RED_HOT}"/></g>')
    shard('-20,-10 330,-10 250,30 300,58 180,92 222,126 60,250 112,140 40,156 92,92 -20,118', 12, 14, 7, 0)
    shard(f'{W + 20},-10 {W + 20},300 {W - 40},190 {W - 80},245 {W - 88},150 {W - 170},196 {W - 110},104 {W - 220},88 {W - 96},60 {W - 128},-10', 12, 14, 8, -2)

    for (x, y, sz, d) in [(390, 60, 26, 0), (690, 40, 18, -1), (820, 330, 22, -2), (36, 300, 16, -.5)]:
        s.add(f'<g opacity="1">{star(x, y, sz, "none", PAPER, 6)}'
              f'<animate attributeName="opacity" values="1;.35;1" dur="3.2s" begin="{d}s" repeatCount="indefinite"/></g>')

    # skyline
    sx = W / 1440
    s.add(f'<path d="{SKYLINE}" fill="{RED_DD}" transform="translate(0 {H - 150}) scale({sx:.4f} .5)"/>')
    s.add(f'<path d="{SKYLINE}" fill="{INK}" transform="translate({W} {H - 104}) scale({-sx:.4f} .4)"/>')

    # portrait + burst
    px, ph = 1012, 452
    pw = ph * 570 / 1200
    burst = ' '.join(f'{px - 60 + a * (pw + 120) / 100:.0f},{H - 150 + b * 150 / 100:.0f}' for a, b in
                     [(0, 100), (4, 58), (16, 72), (20, 30), (33, 52), (42, 8), (52, 44), (63, 0), (70, 40), (82, 18), (86, 56), (100, 34), (100, 100)])
    s.add(f'<polygon points="{burst}" fill="{INK}" stroke="{PAPER}" stroke-width="5"/>')
    if PORTRAIT.exists():
        b64 = base64.b64encode(PORTRAIT.read_bytes()).decode()
        s.defs.append(f'<image id="portrait" href="data:image/webp;base64,{b64}" width="{pw:.0f}" height="{ph}"/>')
        s.add(f'<use href="#portrait" x="{px + 9}" y="{H - ph + 9}" opacity=".9" style="filter:brightness(0)"/>')
        s.add(f'<use href="#portrait" x="{px}" y="{H - ph}"/>')
    # codename tag
    s.add(f'<g transform="rotate(-8 {px - 40} 120)">'
          f'<rect x="{px - 70}" y="96" width="112" height="22" fill="{PAPER}"/>')
    s.text(px - 62, 113, 'CODENAME', 'Barlow', 15, INK, spacing=3)
    s.add(f'<rect x="{px - 56}" y="122" width="{text_w("Bowlby", "FAYAADH", 30) + 24:.0f}" height="44" fill="{RED_HOT}" transform="translate(5 5)"/>'
          f'<rect x="{px - 56}" y="122" width="{text_w("Bowlby", "FAYAADH", 30) + 24:.0f}" height="44" fill="{INK}"/>')
    s.text(px - 44, 156, 'FAYAADH', 'Bowlby', 30, PAPER)
    s.add('</g>')

    # logo
    lx, ly = 70, 250
    tf = f'transform="skewX(-12) rotate(-4 {lx} {ly})"'
    s.add(f'<g {tf}>')
    for dx, dy, col in [(16, 16, RED_DD), (9, 9, INK)]:
        s.text(lx + 90 + dx, ly + dy, 'MF', 'Anton', 230, col)
    s.text(lx + 90, ly, 'MF', 'Anton', 230, PAPER, extra=f'stroke="{INK}" stroke-width="6" paint-order="stroke"')
    mfw = text_w('Anton', 'MF', 230)
    for dx, dy, col in [(7, 7, INK)]:
        s.text(lx + 100 + mfw + dx, ly - 100 + dy, '26', 'Anton', 110, col)
    s.text(lx + 100 + mfw, ly - 100, '26', 'Anton', 110, PAPER, extra=f'stroke="{INK}" stroke-width="4" paint-order="stroke"')
    s.text(lx + 170 + 5, ly + 62 + 5, 'README', 'Anton', 66, INK, spacing=2)
    s.text(lx + 170, ly + 62, 'README', 'Anton', 66, PAPER, spacing=2, extra=f'stroke="{INK}" stroke-width="3" paint-order="stroke"')
    s.add('</g>')

    # name bar + role
    nb_y = 352
    name = 'MUHAMMAD FAYAADH'
    nw = text_w('Barlow', name, 26, 4) + 36
    s.add(f'<g transform="rotate(-4 {lx} {nb_y})"><polygon points="{lx},{nb_y} {lx + nw},{nb_y - 6} {lx + nw - 8},{nb_y + 36} {lx + 6},{nb_y + 40}" fill="{INK}"/>')
    s.text(lx + 18, nb_y + 28, name, 'Barlow', 26, PAPER, spacing=4)
    s.add('</g>')
    role = 'ASPIRING SOFTWARE ENGINEER · WEB APPS END TO END'
    s.add(f'<g transform="rotate(-4 {lx} {nb_y + 70})">')
    s.text(lx + 22, nb_y + 74, role, 'Barlow', 21, INK, spacing=2)
    s.text(lx + 20, nb_y + 72, role, 'Barlow', 21, PAPER, spacing=2)
    s.add('</g>')

    # ransom tagline
    ransom(s, 636, 298, "LET'S BUILD", 52, 'build', delay=.4)

    s.add('</g>')
    s.add(f'<rect x="2" y="2" width="{W - 4}" height="{H - 4}" fill="none" stroke="{INK}" stroke-width="4"/>')
    save('hero.svg', s.render('Muhammad Fayaadh — aspiring software engineer, web apps end to end'))


# ------------------------------------------------------------- badges ----
ICON_MAIL = '<path d="M2 5h20v14H2z M2 5l10 8 10-8" fill="none" stroke="{c}" stroke-width="2.6" stroke-linejoin="round"/>'
ICON_STAR = '<polygon points="12,1 14.9,8.6 23,9.1 16.6,14.2 18.8,22 12,17.6 5.2,22 7.4,14.2 1,9.1 9.1,8.6" fill="{c}"/>'
ICON_IN = '<rect x="1" y="1" width="22" height="22" rx="3" fill="{c}"/><path d="M5.5 9.5h3v9h-3z M7 4.6a1.7 1.7 0 1 1 0 3.4 1.7 1.7 0 0 1 0-3.4z M10.5 9.5h2.9v1.3c.5-.9 1.6-1.5 2.9-1.5 2.6 0 3.2 1.6 3.2 3.9v5.3h-3v-4.7c0-1.1-.1-2.2-1.4-2.2s-1.6 1-1.6 2.1v4.8h-3z" fill="{bg}"/>'
ICON_CV = '<path d="M12 3v12m0 0-5-5m5 5 5-5M4 19h16" fill="none" stroke="{c}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'

def badge(name, label, icon, accent):
    size = 19
    tw = text_w('Bowlby', label, size)
    W, H = int(44 + 46 + tw + 34), 60
    s = Svg(W, H)
    tail = '0,30 12,18 11,26 24,20 22,28 44,22 44,38 22,32 24,40 11,34 12,42'
    body = f'40,8 {W - 10},4 {W - 16},50 44,54'
    s.add(f'<polygon points="{tail}" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>')
    s.add(f'<polygon points="{body}" fill="{RED}" transform="translate(6 6)"/>')
    s.add(f'<polygon points="{body}" fill="{INK}" stroke="{PAPER}" stroke-width="3"/>')
    s.add(f'<polygon points="52,13 84,12 82,46 54,47" fill="{accent}"/>')
    ic = icon.format(c=INK, bg=accent)
    s.add(f'<g transform="translate(57 17) scale(1.05)">{ic}</g>')
    s.text(96, 38, label, 'Bowlby', size, PAPER)
    save(f'badge-{name}.svg', s.render(label))


# ----------------------------------------------------- section titles ----
def section(name, word, seed):
    size = 40
    # measure with a dry run
    probe = Svg(10, 10)
    end = ransom(probe, 52, 58, word, size, seed, animate=False)
    W, H = int(end + 30), 84
    s = Svg(W, H)
    s.add(f'<g><animateTransform attributeName="transform" type="rotate" values="0 24 42;360 24 42" dur="8s" repeatCount="indefinite"/>{star(4, 22, 40, RED, PAPER, 6)}</g>')
    ransom(s, 52, 58, word, size, seed)
    save(f'sec-{name}.svg', s.render(word))


# ------------------------------------------------------------ arsenal ----
ARSENAL = [
    ('LANGUAGES', [('Go', 'go'), ('TypeScript', 'typescript'), ('JavaScript', 'javascript'), ('SQL', None)]),
    ('FRONTEND', [('React', 'react'), ('Next.js', 'nextdotjs'), ('Svelte', 'svelte'), ('SvelteKit', 'svelte'), ('Vite', 'vite'), ('Tailwind CSS', 'tailwindcss')]),
    ('BACKEND', [('Node.js', 'nodedotjs'), ('Express', 'express'), ('Go net/http', 'go'), ('REST APIs', None), ('WebSocket', None), ('SSE', None)]),
    ('DATA', [('PostgreSQL', 'postgresql'), ('MySQL', 'mysql'), ('MongoDB', 'mongodb'), ('Sanity CMS', 'sanity')]),
    ('SHIP IT', [('Docker', 'docker'), ('Linux', 'linux'), ('Nginx', 'nginx'), ('Cloudflare', 'cloudflare'), ('Git', 'git')]),
    ('AUTOMATION', [('Telegram bots', 'telegram'), ('WhatsApp bots', 'whatsapp')]),
]

def arsenal():
    W = 1280
    pad, row_h, gap = 30, 58, 14
    label_w = 236
    rows_layout = []
    for ri, (label, items) in enumerate(ARSENAL):
        start = label_w + 40 + ri * 18
        x = start
        lines = [[]]
        for name, slug in items:
            w = (32 if slug else 0) + text_w('Barlow', name, 22, .5) + 30
            if x + w > W - pad - 20:
                lines.append([]); x = start
            lines[-1].append((name, slug, x)); x += w
        rows_layout.append((label, lines))
    H = pad * 2 + sum(row_h + (len(l) - 1) * 34 for _, l in rows_layout) + gap * (len(rows_layout) - 1)
    s = Svg(W, H)
    s.add(f'<rect width="{W}" height="{H}" fill="{RED}"/><rect width="{W}" height="{H}" fill="url(#maze)" opacity=".13"/>')
    s.defs.append(MAZE)
    y = pad
    for i, (label, lines) in enumerate(rows_layout):
        h = row_h + (len(lines) - 1) * 34
        off = i * 18
        d = i * .12
        s.add('<g>')
        sk = 14
        x0, x1 = pad + off, W - pad
        s.add(f'<polygon points="{x0 + sk + 6},{y + 6} {x1 + 6},{y + 6} {x1 - sk + 6},{y + h + 6} {x0 + 6},{y + h + 6}" fill="{RED_DDD}"/>')
        s.add(f'<polygon points="{x0 + sk},{y} {x1},{y} {x1 - sk},{y + h} {x0},{y + h}" fill="{INK}"/>')
        s.add(f'<polygon points="{x0 + 18},{y + 16} {x0 + 30},{y + 16} {x0 + 26},{y + 42} {x0 + 14},{y + 42}" fill="{RED_HOT}"/>')
        s.text(x0 + 44, y + 39, label, 'Anton', 27, RED_HOT, spacing=2)
        for li, line in enumerate(lines):
            ly = y + 37 + li * 34
            for name, slug, x in line:
                xx = x
                if slug:
                    ic = ICONS[slug]
                    s.add(f'<g transform="translate({xx:.1f} {ly - 20}) scale(1.0)"><path d="{ic["path"]}" fill="{PAPER}"/></g>')
                    xx += 32
                s.text(xx, ly, name, 'Barlow', 22, PAPER, spacing=.5)
        s.add('</g>')
        y += h + gap
    save('arsenal.svg', s.render('Arsenal: Go, TypeScript, JavaScript, SQL, React, Next.js, Svelte, Node.js, PostgreSQL, MySQL, MongoDB, Docker, Linux and more'))


# ------------------------------------------------------------- ticker ----
def ticker():
    W, H = 1280, 58
    words = ['TYPESCRIPT', 'REACT', 'NEXT.JS', 'NODE.JS', 'GO', 'SVELTE', 'POSTGRESQL', 'MYSQL', 'DOCKER', 'LINUX', 'LET\'S BUILD SOMETHING']
    s = Svg(W, H)
    s.add(f'<rect width="{W}" height="{H}" fill="{INK}"/><rect y="0" width="{W}" height="4" fill="{PAPER}"/><rect y="{H - 4}" width="{W}" height="4" fill="{PAPER}"/>')
    run = []
    x = 0
    for i, w in enumerate(words):
        run.append((x, w, PAPER if i % 2 == 0 else RED_HOT))
        x += text_w('Anton', w, 26, 2) + 22
        run.append((x, '★', YELLOW))
        x += 46
    total = x
    s.add(f'<g><animateTransform attributeName="transform" type="translate" values="0 0;{-total:.0f} 0" dur="{total / 60:.0f}s" repeatCount="indefinite"/>')
    for rep in range(int(W / total) + 2):
        for x0, w, col in run:
            if w == '★':
                s.add(star(x0 + rep * total, 17, 24, YELLOW))
            else:
                s.text(x0 + rep * total, 40, w, 'Anton', 26, col, spacing=2)
    s.add('</g>')
    save('ticker.svg', s.render('Tech ticker'))


if __name__ == '__main__':
    ASSETS.mkdir(exist_ok=True)
    hero()
    badge('linkedin', 'LINKEDIN', ICON_IN, '#4da3ff')
    badge('email', 'EMAIL', ICON_MAIL, YELLOW)
    badge('portfolio', 'PORTFOLIO', ICON_STAR, PAPER)
    badge('cv', 'DOWNLOAD CV', ICON_CV, RED_HOT)
    section('calling-card', 'Calling Card', 'cc')
    section('arsenal', 'Arsenal', 'ars')
    section('missions', 'Missions', 'mis')
    section('now', 'Now', 'now')
    arsenal()
    ticker()
