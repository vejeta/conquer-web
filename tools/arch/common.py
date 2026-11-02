import os, math
HERE=os.path.dirname(os.path.abspath(__file__))
OUT=os.path.join(HERE,'src')+'/'  # shape sources (colour pass); bake.py derives height/material passes from them
def svg(name, w, h, defs, body):
    s=f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs>{defs}</defs>{body}</svg>'
    open(OUT+name,'w').write(s)
    n=len(s.encode())
    if n>24000: print('TOO BIG',name,n)
    return n
def grain(fid,x,y,w,h,seed=3,freq=.75,a=.9,b=-.28):
    f=f'<filter id="{fid}" filterUnits="userSpaceOnUse" x="{x}" y="{y}" width="{w}" height="{h}"><feTurbulence type="fractalNoise" baseFrequency="{freq}" numOctaves="3" seed="{seed}" stitchTiles="stitch" x="{x}" y="{y}" width="{w}" height="{h}"/><feColorMatrix values="0 0 0 0 0  0 0 0 0 0  0 0 0 0 0  0 0 0 {a} {b}"/></filter>'
    r=f'<rect x="{x}" y="{y}" width="{w}" height="{h}" filter="url(#{fid})" opacity=".55"/>'
    return f,r
def lg(i,x1,y1,x2,y2,stops,user=True):
    s=''.join(f'<stop offset="{o}" stop-color="{c}"'+(f' stop-opacity="{a}"' if a is not None else '')+'/>' for o,c,a in [(t+(None,))[:3] if len(t)==2 else t for t in stops])
    u=' gradientUnits="userSpaceOnUse"' if user else ''
    return f'<linearGradient id="{i}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{u}>{s}</linearGradient>'
def rg(i,cx,cy,r,stops,fx=None,fy=None):
    s=''.join(f'<stop offset="{t[0]}" stop-color="{t[1]}"'+(f' stop-opacity="{t[2]}"' if len(t)>2 else '')+'/>' for t in stops)
    f=f' fx="{fx}" fy="{fy}"' if fx is not None else ''
    return f'<radialGradient id="{i}" cx="{cx}" cy="{cy}" r="{r}"{f} gradientUnits="userSpaceOnUse">{s}</radialGradient>'
def shadow(i,dx=1,dy=1.5,sd=1.2,op=.55,color='#000'):
    return f'<filter id="{i}" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="{dx}" dy="{dy}" stdDeviation="{sd}" flood-color="{color}" flood-opacity="{op}"/></filter>'
def star(cx,cy,r,n=8,inner=.45,rot=-90):
    pts=[]
    for k in range(2*n):
        rr=r if k%2==0 else r*inner
        a=math.radians(rot+k*180/n)
        pts.append(f'{cx+rr*math.cos(a):.1f},{cy+rr*math.sin(a):.1f}')
    return 'M'+'L'.join(pts)+'Z'

# ---------------------------------------------------------------------------
# HEIGHT-pass helpers (design v6).  A height SVG is greyscale: 0 = deepest, 1 = highest.
# Where a piece has an authored height SVG (src/<name>.h.svg), bake.py uses it (alpha = coverage;
# uncovered pixels fall back to the luminance of the colour pass).
def gv(v):
    c = int(round(max(0, min(1, v)) * 255))
    return f'#{c:02x}{c:02x}{c:02x}'
def hsvg(name, w, h, defs, body):
    s = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}"><defs>{defs}</defs>{body}</svg>'
    open(OUT + name, 'w').write(s)
    return len(s.encode())
def round_prof(lo, hi, n=10, p=.5):
    """stops (offset, grey) of a round (cylindrical) cross-section, edge = lo, centre = hi"""
    out = []
    for i in range(n + 1):
        t = i / n; u = 2 * t - 1
        out.append((round(t, 3), lo + (hi - lo) * max(0, 1 - u * u) ** p))
    return out
def hlg(i, x1, y1, x2, y2, stops, user=True):
    s = ''.join(f'<stop offset="{o}" stop-color="{gv(v)}"/>' for o, v in stops)
    u = ' gradientUnits="userSpaceOnUse"' if user else ''
    return f'<linearGradient id="{i}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{u}>{s}</linearGradient>'
def hcyl(i, x1, y1, x2, y2, lo, hi, user=True, n=10, p=.5):
    """linear gradient with a round (cylinder) profile across the axis x1,y1 -> x2,y2"""
    return hlg(i, x1, y1, x2, y2, round_prof(lo, hi, n, p), user)
def hdome(i, lo, hi, cx=.5, cy=.5, r=.5, fx=None, fy=None, n=9, p=.5):
    """radial gradient (bounding-box units) with a spherical profile: centre = hi, rim = lo"""
    stops = ''.join(f'<stop offset="{t/n:.3f}" stop-color="{gv(lo + (hi - lo) * max(0, 1 - (t / n) ** 2) ** p)}"/>' for t in range(n + 1))
    f = f' fx="{fx}" fy="{fy}"' if fx is not None else ''
    return f'<radialGradient id="{i}" cx="{cx}" cy="{cy}" r="{r}"{f}>{stops}</radialGradient>'
def tube(d, w, lo, hi, n=9, cap='round', extra=''):
    """a round rod along path d: stacked strokes, narrower = higher (cylinder section)"""
    s = ''
    for k in range(n):
        r = 1 - k / n; rm = 1 - (k + .5) / n
        v = lo + (hi - lo) * max(0, 1 - rm * rm) ** .5 if k else lo
        s += f'<path d="{d}" fill="none" stroke="{gv(v)}" stroke-width="{w * r:.2f}" stroke-linecap="{cap}" stroke-linejoin="round"{extra}/>'
    return s
def bevel(d, base, top, steps=3, w=3.2, fillv=None, extra=''):
    """a flat-topped block with a chamfered edge: fill = top, edge strokes step down to base"""
    s = f'<path d="{d}" fill="{gv(top)}"{extra}/>'
    for k in range(steps):
        t = (k + .5) / steps
        v = base + (top - base) * t
        s += f'<path d="{d}" fill="none" stroke="{gv(v)}" stroke-width="{w * (1 - k / steps):.2f}" stroke-linejoin="round"/>'
    return s
def flat(d, v, extra=''):
    return f'<path d="{d}" fill="{gv(v)}"{extra}/>'
def hrect(x, y, w, h, fill, rx=0, extra=''):
    f = fill if isinstance(fill, str) else gv(fill)
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{f}"{extra}/>'

def star_facets(cx, cy, r, n=8, inner=.45, rot=-90, lo=.78, hi=.94, boss=.0):
    """a star modelled as 2n triangular facets (left half dark, right half light) meeting at a ridge to the centre"""
    import math
    pts = []
    for k in range(2 * n):
        rr = r if k % 2 == 0 else r * inner
        a = math.radians(rot + k * 180 / n)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    s = ''
    m = 2 * n
    for k in range(0, m, 2):
        t = pts[k]; vl = pts[(k - 1) % m]; vr = pts[(k + 1) % m]
        # light from the top-left: facets that face up/left are lighter
        ang = math.atan2(t[1] - cy, t[0] - cx)
        lit = .5 - .5 * math.cos(ang - math.radians(225))
        v1 = lo + (hi - lo) * max(0, min(1, lit + .18)); v2 = lo + (hi - lo) * max(0, min(1, lit - .18))
        s += f'<path d="M{cx:.1f} {cy:.1f}L{vl[0]:.1f} {vl[1]:.1f}L{t[0]:.1f} {t[1]:.1f}Z" fill="{gv(v1)}"/><path d="M{cx:.1f} {cy:.1f}L{t[0]:.1f} {t[1]:.1f}L{vr[0]:.1f} {vr[1]:.1f}Z" fill="{gv(v2)}"/>'
    return s

def cone(xc, ytip, ybase, halfw, lo, hi, n=7, flat_base=True):
    """a conical spike along the vertical axis x=xc (tip up if ytip<ybase): nested triangles, narrower = higher"""
    s = ''
    for k in range(n):
        hw = halfw * (1 - k / n)
        v = lo + (hi - lo) * (1 - (1 - (k + .5) / n) ** 2) ** .5 if k else lo
        s += f'<path d="M{xc - hw:.2f} {ybase}L{xc} {ytip}L{xc + hw:.2f} {ybase}Z" fill="{gv(v)}"/>'
    return s
