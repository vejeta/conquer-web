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
