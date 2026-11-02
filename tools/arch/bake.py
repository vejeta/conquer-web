#!/usr/bin/env python3.13
"""Bake the architecture sprites (design v5).

    python3.13 tools/arch/build.py        # shape sources -> tools/arch/src/*.svg
    python3.13 tools/arch/bake.py [race ...] [--only piece-substring]

Needs: numpy, Pillow (with WebP), playwright + a Chrome binary (CHROMIUM env,
default /usr/bin/google-chrome) to rasterise the SVG shapes at 4x.

Passes.  The SVG sources hold the shapes of one piece.  From each source this
script derives, at 4x device pixels,
  * the CLEAN pass: black outlines (dark strokes), film-grain rectangles and
    drop-shadow filters are removed, so only fills remain;
  * the HEIGHT pass: luminance of the clean pass is the relief height
    (background deepest, mouldings and figures higher, highlights highest),
    softened at three radii so rounded forms (shafts, capitals, crowns)
    get soft edges and chiselled steps stay crisp;
  * the MATERIAL pass: colour IDs per pixel (stone / metal / ember / ivory)
    classified from the clean colours with per-race rules.
Then (numpy): normals from the height (central differences), key light from
the top-left (az 315, el 50) + 20% fill from the bottom-right + a cool rim
from the top on silver and iron, Lambert + Blinn-Phong with a per-material
specular, two-radius ambient occlusion from the blurred inverted height,
procedural fractal-noise textures per race and material, a per-race colour
grade, 2% film grain, and (corners) a soft drop shadow baked into a
transparent margin.  Pieces that face the other way (right columns, right
corners) are mirrored BEFORE lighting so the light stays top-left everywhere.
Tiles are baked with wrap-around filters on their repeat axis, so they are
seamless.  The result is downsampled 4x -> 2x and written as lossy WebP.
"""
import os, re, sys, io, math, base64
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')
OUT = os.path.normpath(os.path.join(HERE, '..', '..', 'web', 'arch'))
CHROME = os.environ.get('CHROMIUM', '/usr/bin/google-chrome')
S = 4          # render scale (device px per css px)
F = 2          # delivered scale
PAD = 14       # css px of transparent margin around corner sculptures (baked shadow)

# --------------------------------------------------------------------------
# filters
def _pad(a, p, wx, wy):
    if p <= 0: return a
    a = np.pad(a, ((p, p), (0, 0)) + ((0, 0),) * (a.ndim - 2), mode='wrap' if wy else 'edge')
    a = np.pad(a, ((0, 0), (p, p)) + ((0, 0),) * (a.ndim - 2), mode='wrap' if wx else 'edge')
    return a

def blur(a, sig, wx=False, wy=False):
    """Gaussian blur through the FFT; wrap-around on the axes flagged."""
    if sig < 0.35: return a
    if a.ndim == 3:
        return np.stack([blur(a[..., i], sig, wx, wy) for i in range(a.shape[2])], -1)
    p = int(3 * sig) + 2
    ap = _pad(a, p, wx, wy)
    fy = np.fft.fftfreq(ap.shape[0])[:, None]; fx = np.fft.rfftfreq(ap.shape[1])[None, :]
    g = np.exp(-2 * (math.pi * sig) ** 2 * (fx * fx + fy * fy))
    o = np.fft.irfft2(np.fft.rfft2(ap) * g, s=ap.shape)
    return o[p:-p, p:-p].astype(np.float32)

def grad(h, wx, wy):
    hp = _pad(h, 1, wx, wy)
    gx = (hp[1:-1, 2:] - hp[1:-1, :-2]) * .5
    gy = (hp[2:, 1:-1] - hp[:-2, 1:-1]) * .5
    return gx, gy

def smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def noise(shape, seed, sig):
    """Periodic noise, unit variance, correlation length sig (device px)."""
    r = np.random.default_rng(seed)
    n = blur(r.standard_normal(shape).astype(np.float32), sig, True, True)
    return (n / (n.std() + 1e-6)).astype(np.float32)

def fbm(shape, seed, octs):
    """octs: [(sigma_css, amp)] -> zero-mean sum."""
    o = np.zeros(shape, np.float32)
    for i, (s, a) in enumerate(octs):
        o += a * noise(shape, seed * 31 + i, s * S)
    return o

# --------------------------------------------------------------------------
# rasterising
_pw = None
def browser():
    global _pw
    if _pw is None:
        from playwright.sync_api import sync_playwright
        p = sync_playwright().start()
        _pw = (p, p.chromium.launch(executable_path=CHROME, args=['--no-sandbox']))
    return _pw[1]

def lum_hex(h):
    h = h.lstrip('#')
    if len(h) == 3: h = ''.join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (.299 * r + .587 * g + .114 * b) / 255

def clean_svg(s):
    """CLEAN pass: no dark outlines, no baked grain, no baked drop shadows."""
    def st(m):
        return 'stroke="none"' if lum_hex(m.group(1)) < .33 else m.group(0)
    s = re.sub(r'stroke="(#[0-9a-fA-F]{3,6})"', st, s)
    s = re.sub(r'<rect[^>]*filter="url\(#(?:g\d|gc|gb|gl|gs)\)"[^>]*/>', '', s)
    ids = re.findall(r'<filter id="([^"]+)"[^>]*><feDropShadow', s)
    for i in ids:
        s = s.replace(f' filter="url(#{i})"', '')
    return s

_cache = {}
def render(name):
    """name -> (H, W, 4) float32 straight RGBA at S x"""
    if name in _cache: return _cache[name]
    txt = open(os.path.join(SRC, name + '.svg')).read()
    w, h = map(int, re.search(r'width="(\d+)" height="(\d+)"', txt).groups())
    b64 = base64.b64encode(clean_svg(txt).encode()).decode()
    pg = browser().new_page(viewport={'width': w + 8, 'height': h + 8}, device_scale_factor=S)
    pg.set_content(f'<body style="margin:0;background:transparent"><img id="i" style="display:block" width="{w}" height="{h}" src="data:image/svg+xml;base64,{b64}"></body>')
    pg.wait_for_timeout(150)
    png = pg.locator('#i').screenshot(omit_background=True)
    pg.close()
    im = np.asarray(Image.open(io.BytesIO(png)).convert('RGBA'), np.float32) / 255
    assert im.shape[0] == h * S and im.shape[1] == w * S, (name, im.shape)
    _cache[name] = im
    return im

# --------------------------------------------------------------------------
# per-race look
def hsv(rgb):
    mx = rgb.max(-1); mn = rgb.min(-1); d = mx - mn + 1e-6
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) * 60
    return h, d / (mx + 1e-6), mx

# materials: dict name -> dict(alb, ks (specular), p (shininess), tint (spec tint), rim)
MAT = {
    'human': {
        'stone': dict(alb=(.80, .79, .75), ks=.05, p=18, tint=(1, 1, .95), rim=0),
    },
    'elf': {
        'stone': dict(alb=(.60, .70, .66), ks=.07, p=24, tint=(.9, 1, .96), rim=.0),
        'silver': dict(alb=(.80, .85, .88), ks=1.0, p=110, tint=(.95, 1, 1), rim=.5),
    },
    'dwarf': {
        'stone': dict(alb=(.40, .37, .34), ks=.04, p=14, tint=(1, .95, .9), rim=0),
        'bronze': dict(alb=(.62, .40, .17), ks=.65, p=26, tint=(1, .78, .45), rim=.0),
        'iron': dict(alb=(.60, .64, .70), ks=.28, p=9, tint=(.9, .95, 1), rim=.25),
    },
    'orc': {
        'stone': dict(alb=(.34, .30, .28), ks=.05, p=12, tint=(1, .8, .7), rim=0),
        'iron': dict(alb=(.36, .35, .38), ks=.30, p=9, tint=(.9, .9, 1), rim=.4),
        'ivory': dict(alb=(.90, .84, .68), ks=.22, p=30, tint=(1, .97, .85), rim=0),
        'ember': dict(alb=(.30, .12, .06), ks=0, p=1, tint=(1, 1, 1), rim=0),
    },
}
EMBER = np.array((1.0, .46, .16), np.float32)
GRADE = {   # tint, contrast, exposure, strength of normals (css px of relief for full height)
    'human': dict(tint=(1.00, .995, .975), con=1.10, exp=1.0, A=6.5, seed=11),
    'elf':   dict(tint=(.97, 1.00, 1.01), con=1.05, exp=.94, A=5.2, seed=22),
    'dwarf': dict(tint=(1.02, .995, .965), con=1.14, exp=1.05, A=6.2, seed=33),
    'orc':   dict(tint=(1.03, .975, .955), con=1.10, exp=.98, A=6.8, seed=44),
}

def classify(race, rgb, a):
    h, s, v = hsv(rgb)
    lum = rgb @ np.array((.299, .587, .114), np.float32)
    m = {}
    if race == 'human':
        m['stone'] = np.ones_like(lum)
    elif race == 'elf':
        m['silver'] = smooth(lum, .66, .80) * (1 - smooth(s, .14, .26))
        m['stone'] = 1 - m['silver']
    elif race == 'dwarf':
        br = smooth(s, .30, .45) * ((h > 18) & (h < 58)) * smooth(lum, .18, .30)
        steel = smooth(rgb[..., 2] - rgb[..., 0], .02, .06) * smooth(lum, .30, .42) * (1 - br)
        m['bronze'] = br.astype(np.float32); m['iron'] = steel.astype(np.float32)
        m['stone'] = np.clip(1 - m['bronze'] - m['iron'], 0, 1)
    elif race == 'orc':
        em = smooth(s, .42, .58) * ((h < 52) | (h > 345)) * smooth(rgb[..., 0], .42, .6)
        iv = smooth(s, .10, .18) * (1 - smooth(s, .38, .50)) * ((h > 28) & (h < 62)) * smooth(lum, .50, .62) * (1 - em)
        ir = smooth(lum, .26, .40) * (1 - smooth(s, .16, .28)) * (1 - em) * (1 - iv)
        m['ember'] = em.astype(np.float32); m['ivory'] = iv.astype(np.float32); m['iron'] = ir.astype(np.float32)
        m['stone'] = np.clip(1 - em - iv - ir, 0, 1)
    for k in m:
        m[k] = blur(m[k].astype(np.float32), .7 * S)
    t = sum(m.values()) + 1e-6
    return {k: v / t for k, v in m.items()}, lum

def height_from(lum, a, wx, wy):
    h0 = lum * a
    return (.50 * blur(h0, .55 * S, wx, wy) + .30 * blur(h0, 1.8 * S, wx, wy) + .20 * blur(h0, 5.5 * S, wx, wy)).astype(np.float32)

def bake(race, im, wx=False, wy=False, chamfer=None, shadow=False, seed=0):
    """im: (H,W,4) straight RGBA at S x. returns (H,W,4) float straight RGBA at S x."""
    G = GRADE[race]; mats = MAT[race]
    Hh, Ww = im.shape[:2]; shp = (Hh, Ww)
    a = im[..., 3].astype(np.float32)
    rgb = im[..., :3] * 1.0
    masks, lum = classify(race, rgb, a)
    h = height_from(lum, a, wx, wy)
    if chamfer:   # end bevel of a frieze cap: height falls away over 7 css px at the outer end
        xs = np.arange(Ww, dtype=np.float32)
        d = xs if chamfer == 'l' else (Ww - 1 - xs)
        ramp = smooth(d, 0, 7 * S)
        h = h * (.30 + .70 * ramp)[None, :] * (1 - 0 * a)
    # ---- procedural material textures
    sd = G['seed'] * 100 + seed
    n1 = fbm(shp, sd + 1, [(.5, .6), (1.2, .5), (3, .35), (9, .25)])          # grain, 4 octaves
    n2 = fbm(shp, sd + 2, [(2.2, .6), (6, .4)])
    # stone
    stone_t = 1 + (.12 if race == 'human' else .075) * n1
    if race == 'human':      # granite: pale/dark speckle
        sp = noise(shp, sd + 3, .55 * S)
        stone_t += .24 * (sp > 1.8) - .24 * (sp < -1.8)
        stone_t += .03 * n2
    if race == 'elf':        # green-grey stone with pale veins
        v = noise(shp, sd + 4, 7 * S); v2 = noise(shp, sd + 5, 2.2 * S)
        vein = np.exp(-(v / .13) ** 2) * (.55 + .45 * np.clip(v2, -1, 1))
        stone_t += .22 * vein + .04 * n2
    if race == 'dwarf':      # dark basalt: fine grain, slight bluish pits
        stone_t = 1 + .12 * n1 + .05 * n2
    if race == 'orc':        # scorched: soot mottling and dark cracks
        cr = noise(shp, sd + 6, 4.5 * S)
        crack = np.exp(-(cr / .10) ** 2)
        stone_t = (1 + .10 * n1 + .10 * n2) * (1 - .45 * crack)
    # relief micro-detail on the height itself
    micro = 0.010 * n1
    if race == 'dwarf' and 'bronze' in masks:   # hammered micro-dents
        dents = noise(shp, sd + 7, 2.6 * S)
        micro = micro + .035 * np.clip(dents, -2, 2) * masks['bronze']
    if race == 'orc':
        micro = micro - .02 * crack * masks['stone']
    h = h + micro
    # ---- normals
    gx, gy = grad(h, wx, wy)
    k = G['A'] * S
    nx, ny, nz = -gx * k, -gy * k, np.ones_like(gx)
    inv = 1 / np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx * inv, ny * inv, nz * inv
    el = math.radians(50); az = math.radians(315)
    Lk = np.array((math.sin(az) * math.cos(el), -math.cos(az) * math.cos(el), math.sin(el)), np.float32)
    Lf = np.array((.5, .5, .7), np.float32); Lf /= np.linalg.norm(Lf)
    Lr = np.array((0, -.9, .35), np.float32); Lr /= np.linalg.norm(Lr)
    dk = np.clip(nx * Lk[0] + ny * Lk[1] + nz * Lk[2], 0, 1) / Lk[2]
    df = np.clip(nx * Lf[0] + ny * Lf[1] + nz * Lf[2], 0, 1) / Lf[2]
    # ---- ambient occlusion (two radii, blurred inverted height)
    ao1 = 1 - 1.5 * np.clip(blur(h, 2.2 * S, wx, wy) - h, 0, .4)
    ao2 = 1 - 1.0 * np.clip(blur(h, 9 * S, wx, wy) - h, 0, .5)
    ao = np.clip(ao1 * ao2, .30, 1)
    # ---- albedo + specular per material
    col = np.zeros(shp + (3,), np.float32); ks = np.zeros(shp, np.float32); pw = np.zeros(shp, np.float32)
    spt = np.zeros(shp + (3,), np.float32); rim = np.zeros(shp, np.float32)
    for name, m in masks.items():
        p = mats[name]
        alb = np.array(p['alb'], np.float32)
        t = np.ones(shp, np.float32)
        if name == 'stone': t = stone_t
        if race == 'elf' and name == 'silver': t = 1 + .03 * n1
        if race == 'dwarf' and name == 'bronze': t = 1 + .10 * n2 + .06 * n1
        if race == 'orc' and name == 'iron':    # rusted iron: orange-brown mottling
            rust = smooth(noise(shp, sd + 8, 3.5 * S) + .6 * noise(shp, sd + 9, 1 * S), .7, 2.0)
            alb = alb[None, None, :] * (1 - rust[..., None]) + np.array((.44, .23, .11), np.float32)[None, None, :] * rust[..., None]
            c = alb * (1 + .08 * n1)[..., None]
            col += m[..., None] * c; ks += m * p['ks'] * (1 - .6 * rust); pw += m * p['p']; spt += m[..., None] * np.array(p['tint'], np.float32); rim += m * p['rim']
            continue
        col += m[..., None] * (alb[None, None, :] * t[..., None])
        ks += m * p['ks']; pw += m * p['p']; spt += m[..., None] * np.array(p['tint'], np.float32); rim += m * p['rim']
    # keep the tonal information of the shapes (niches stay dark, inlays stay light)
    ref = {'human': .55, 'elf': .50, 'dwarf': .38, 'orc': .30}[race]
    tone = np.clip(lum / ref, .12, 1.7)
    tone = (.25 + .75 * tone) if race == 'human' else tone
    w = (.45 - .25 * (masks.get('bronze', 0) + masks.get('silver', 0)))[..., None] if race in ('dwarf', 'elf') else .45
    base = col * tone[..., None] * (1 - w) + np.clip(rgb, 0, 1) * w * (1.0 if race != 'orc' else 1.0)
    base = base * (1 - .0)
    # ---- shading
    shade = (.22 + .72 * dk + .14 * df)[..., None] * ao[..., None]
    Hv = Lk + np.array((0, 0, 1), np.float32); Hv /= np.linalg.norm(Hv)
    sp = np.clip(nx * Hv[0] + ny * Hv[1] + nz * Hv[2], 0, 1)
    spec = (ks * sp ** np.maximum(pw, 1))[..., None] * spt * (.4 + .6 * ao[..., None])
    rm = np.clip(nx * Lr[0] + ny * Lr[1] + nz * Lr[2], 0, 1)
    rimc = (rim * rm ** 3)[..., None] * np.array((.55, .75, 1.0), np.float32) * .55
    out = base * shade + spec + rimc
    # ---- ember emission (orc)
    if race == 'orc':
        em = masks['ember']
        glow = blur(em, 1.6 * S) * .9 + blur(em, 7 * S) * .55 + blur(em, 18 * S) * .22
        core = em[..., None] * EMBER[None, None, :] * (.75 + .5 * np.clip(lum, 0, 1)[..., None] * 1.4)
        out = out * (1 - .55 * em[..., None]) + core * 1.0
        out += glow[..., None] * np.array((1.0, .38, .10), np.float32) * .55 * (1 - .5 * em[..., None])
        out = out + .0
    # ---- grade
    out = out * np.array(G['tint'], np.float32)[None, None, :] * G['exp']
    out = np.clip(out, 0, 1.4)
    out = 1 / (1 + np.exp(-(out - .5) * 5.2 * G['con'] / 1.1))  # soft S-curve
    lo, hi = 1 / (1 + np.exp(2.6 * G['con'] / 1.1 * 1.0)), 1 / (1 + np.exp(-2.6 * G['con'] / 1.1 * 1.0))
    out = np.clip(out, 0, 1)
    r = np.random.default_rng(sd + 99)
    out = out + .02 * r.standard_normal(shp).astype(np.float32)[..., None]
    out = np.clip(out, 0, 1)
    A = a
    if shadow:
        P = PAD * S
        out = np.pad(out, ((P, P), (P, P), (0, 0))); A = np.pad(A, ((P, P), (P, P)))
        sh = np.roll(np.roll(blur(A, 5.5 * S), 5 * S, 0), 2 * S, 1) * .40
        oa = A + sh * (1 - A)
        orgb = out * (A / (oa + 1e-6))[..., None]
        return np.concatenate([orgb, oa[..., None]], -1)
    return np.concatenate([out, A[..., None]], -1)

def down(rgba, quality=82, name=None):
    """4x float RGBA -> 2x PIL image (premultiplied-aware)."""
    u8 = (np.clip(rgba, 0, 1) * 255 + .5).astype(np.uint8)
    im = Image.fromarray(u8, 'RGBA')
    sz = (im.width * F // S, im.height * F // S)
    return im.convert('RGBa').resize(sz, Image.LANCZOS).convert('RGBA')

def save(im, name, q=82):
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + '@2x.webp')
    opaque = np.asarray(im)[..., 3].min() == 255
    (im.convert('RGB') if opaque else im).save(path, 'WEBP', quality=q, method=6, alpha_quality=90)
    return os.path.getsize(path)

def crop(im, x, y, w, h):
    return im[int(y * S):int((y + h) * S), int(x * S):int((x + w) * S)]

# --------------------------------------------------------------------------
CAP = 10   # css px width of a frieze end-cap
def pieces(race, only=None):
    res = {}
    def want(n): return only is None or only in n
    # ---- columns (72 x 184: cap 0-64, tile 64-136, base 136-184); right = mirrored shapes
    if any(want(f'{race}-col-{k}-{s}') for k in ('cap', 'tile', 'base') for s in 'lr'):
        col = render(f'{race}-column')
        for sd in 'lr':
            c = col if sd == 'l' else col[:, ::-1]
            for k, (y, h, wy) in {'cap': (0, 64, False), 'tile': (64, 72, True), 'base': (136, 48, False)}.items():
                n = f'{race}-col-{k}-{sd}'
                if want(n):
                    res[n] = (bake(race, crop(c, 0, y, 72, h), wy=wy, seed=1 if sd == 'l' else 2), 82 if k != 'tile' else 86)
    # ---- lintel (704 x 88: emblem 0-616 + tile 616-704) and sill (672 x 56: emblem 0-560 + tile 560-672)
    for nm, emb, tw, hh in (('lintel', 616, 88, 88), ('sill', 560, 112, 56)):
        if not any(want(f'{race}-{nm}-{k}') for k in ('emblem', 'tile', 'cap-l', 'cap-r')): continue
        src = render(f'{race}-{nm}')
        if want(f'{race}-{nm}-emblem'):
            res[f'{race}-{nm}-emblem'] = (bake(race, crop(src, 0, 0, emb, hh), seed=3), 82)
        tile = crop(src, emb, 0, tw, hh)
        if want(f'{race}-{nm}-tile'):
            res[f'{race}-{nm}-tile'] = (bake(race, tile, wx=True, seed=4), 86)
        for sd in 'lr':
            n = f'{race}-{nm}-cap-{sd}'
            if want(n):
                b = bake(race, tile, wx=False, chamfer=sd, seed=4)
                res[n] = (b[:, :CAP * S] if sd == 'l' else b[:, -CAP * S:], 86)
    # ---- corners (100 x 100) + 14 px margin with a baked shadow; right = mirrored shapes
    for nm, srcn in (('cor', f'{race}-corner'),) + ((('corb', 'dwarf-corner-b'),) if race == 'dwarf' else ()):
        if not any(want(f'{race}-{nm}-{s}') for s in 'lr'): continue
        c = render(srcn)
        for sd in 'lr':
            n = f'{race}-{nm}-{sd}'
            if want(n):
                res[n] = (bake(race, c if sd == 'l' else c[:, ::-1], shadow=True, seed=5 if sd == 'l' else 6), 84)
    return res

if __name__ == '__main__':
    args = sys.argv[1:]
    only = None
    if '--only' in args:
        i = args.index('--only'); only = args[i + 1]; del args[i:i + 2]
    races = args or ['human', 'elf', 'dwarf', 'orc']
    tot = 0
    for r in races:
        for n, (arr, q) in pieces(r, only).items():
            sz = save(down(arr), n, q); tot += sz
            print(f'{n:24s} {sz/1024:6.1f} KB')
    print('total', round(tot / 1024), 'KB')
    if _pw: _pw[1].close(); _pw[0].stop()
