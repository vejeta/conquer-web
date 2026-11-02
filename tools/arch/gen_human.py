from common import *
L,M,D='#d9d4c7','#9a958a','#4f4b44'; HI='#f6f2e6'; DK='#2a2824'
def pal_defs(p=''):
    return (lg(p+'fv',0,0,0,1,[(0,HI),(.12,L),(.7,M),(1,D)],False)+
            lg(p+'fh',0,0,1,0,[(0,D),(.2,M),(.5,L),(.8,M),(1,D)],False)+
            shadow(p+'sh',1,1.6,1.4,.6))

# ---------------- COLUMN 72x184 : cap 0-64, tile 64-136, base 136-184
def column():
    d=pal_defs()+lg('shaft',12,0,60,0,[(0,'#3b3834'),(.14,M),(.38,HI),(.55,L),(.82,M),(1,'#34312d')])
    d+=lg('flute',0,0,1,0,[(0,'#1f1d1a',.8),(.55,'#2d2a26',.35),(1,HI,.45)],False)
    d+=lg('wall',0,0,72,0,[(0,'#26241f'),(.2,'#3d3a34'),(.8,'#3d3a34'),(1,'#26241f')])
    d+=lg('ech',6,0,66,0,[(0,'#5b574f'),(.3,L),(.5,HI),(.75,L),(1,'#58544c')])
    d+=lg('abv',0,0,0,10,[(0,HI),(.25,L),(1,M)])
    gf,gr=grain('gc',0,64,72,72,4)
    d+=gf
    b=''
    # ---- capital
    b+='<g filter="url(#sh)">'
    b+='<path d="M6 13C6 34 14 44 14 53H58C58 44 66 34 66 13Z" fill="url(#ech)"/>'
    b+='</g>'
    b+='<path d="M6 13C6 34 14 44 14 53" fill="none" stroke="#2a2824" stroke-width="1.2" opacity=".6"/>'
    b+='<path d="M66 13C66 34 58 44 58 53" fill="none" stroke="#2a2824" stroke-width="1.2" opacity=".6"/>'
    # acanthus leaves
    for x in (17,27,36,45,55):
        h=44 if x==36 else 47
        b+=f'<path d="M{x-6} 59Q{x-8} 50 {x-2} {h}Q{x} {h-5} {x+2} {h}Q{x+8} 50 {x+6} 59Z" fill="url(#fv)" stroke="{DK}" stroke-width=".8" opacity=".95"/><path d="M{x} 58V{h+3}" stroke="{D}" stroke-width="1"/>'
    # crown relief
    b+=f'<g filter="url(#sh)"><path d="M25 38V24L31 30L36 20L41 30L47 24V38Z" fill="url(#fv)" stroke="{DK}" stroke-width=".8"/><rect x="25" y="34" width="22" height="5" fill="{L}" stroke="{DK}" stroke-width=".8"/><circle cx="36" cy="36.5" r="1.3" fill="{D}"/><circle cx="36" cy="18.5" r="1.8" fill="{L}" stroke="{DK}" stroke-width=".6"/></g>'
    # volutes
    for cx in (13,59):
        b+=f'<g filter="url(#sh)"><circle cx="{cx}" cy="20" r="8" fill="url(#fv)" stroke="{DK}" stroke-width=".9"/></g><path d="M{cx} 20m0 0a1.5 1.5 0 0 1 3 0a4 4 0 0 1-6 3a6 6 0 0 1 0-9" fill="none" stroke="{D}" stroke-width="1.3" stroke-linecap="round"/>'
    # abacus
    b+='<g filter="url(#sh)"><rect x="1" y="0" width="70" height="11" rx="1.5" fill="url(#abv)"/></g>'
    b+=f'<rect x="1" y="0" width="70" height="1.8" fill="{HI}"/><rect x="1" y="9" width="70" height="2" fill="#000" opacity=".28"/>'
    b+=f'<path d="M3 5H69" stroke="{D}" stroke-width=".8" opacity=".6"/>'
    # astragal ring
    b+=f'<rect x="12" y="58" width="48" height="6" rx="3" fill="url(#fv)" stroke="{DK}" stroke-width=".8"/>'
    # ---- shaft tile
    b+='<rect x="0" y="64" width="72" height="72" fill="url(#wall)"/>'
    b+=f'<rect x="12" y="64" width="48" height="72" fill="url(#shaft)"/>'
    for i in range(5):
        x=12+3.6/2+i*9.6+(0 if False else 0)
        x=14+i*9.6
        b+=f'<rect x="{x:.1f}" y="64" width="6.4" height="72" rx="3.2" fill="url(#flute)" transform="translate(0 0)"/>'
    b+=f'<rect x="12" y="64" width="1.2" height="72" fill="{HI}" opacity=".35"/><rect x="58.8" y="64" width="1.2" height="72" fill="#000" opacity=".4"/>'
    b+=f'<rect x="0" y="64" width="72" height="72" filter="url(#gc)" opacity=".28"/>'
    # ---- base
    gf2,_=grain('gb',0,136,72,48,5); d+=gf2
    b+='<rect x="0" y="136" width="72" height="48" fill="url(#wall)"/>'
    b+='<rect x="12" y="136" width="48" height="8" fill="url(#shaft)"/>'
    b+='<rect x="10" y="143" width="52" height="4" fill="#26231f"/>'
    b+='<g filter="url(#sh)"><rect x="6" y="146" width="60" height="10" rx="5" fill="url(#fv)" stroke="#2a2824" stroke-width=".8"/></g>'
    b+=f'<rect x="8" y="147" width="56" height="1.6" rx=".8" fill="{HI}" opacity=".8"/>'
    b+='<g filter="url(#sh)"><rect x="3" y="156" width="66" height="13" fill="url(#fv)"/><rect x="3" y="156" width="66" height="2.2" fill="'+HI+'"/><rect x="3" y="167" width="66" height="2" fill="#000" opacity=".35"/>'
    b+='<rect x="0" y="169" width="72" height="15" fill="url(#fv)"/><rect x="0" y="169" width="72" height="2.2" fill="'+HI+'"/></g>'
    b+=f'<path d="M36 173V182M12 175V182M60 175V182" stroke="{D}" stroke-width="1" opacity=".5"/>'
    b+=f'<rect x="0" y="136" width="72" height="48" filter="url(#gb)" opacity=".25"/>'
    return svg('human-column.svg',72,184,d,b)

# ---------------- LINTEL 640 emblem + 88 tile = 728 x 88
def courses(x0,w,tile=False):
    """horizontal courses spanning x0..x0+w"""
    b=''
    b+=f'<rect x="{x0}" y="0" width="{w}" height="88" fill="#35322d"/>'
    # cornice
    b+=f'<rect x="{x0}" y="0" width="{w}" height="13" fill="url(#cor)"/><rect x="{x0}" y="0" width="{w}" height="2" fill="{HI}"/><rect x="{x0}" y="6" width="{w}" height="1" fill="{DK}" opacity=".35"/>'
    b+=f'<rect x="{x0}" y="13" width="{w}" height="12" fill="url(#castdn)"/>'
    # frieze face
    b+=f'<rect x="{x0}" y="25" width="{w}" height="44" fill="url(#frz)"/>'
    # lower moulding + soffit
    b+=f'<rect x="{x0}" y="69" width="{w}" height="6" fill="url(#fv)"/><rect x="{x0}" y="69" width="{w}" height="1.4" fill="{HI}" opacity=".9"/>'
    b+=f'<rect x="{x0}" y="75" width="{w}" height="13" fill="url(#soff)"/><rect x="{x0}" y="78" width="{w}" height="1.2" fill="{HI}" opacity=".18"/>'
    return b
def lintel():
    d=pal_defs()+lg('cor',0,0,0,13,[(0,L),(.6,M),(1,'#6e6a60')],True)
    d+=lg('castdn',0,13,0,25,[(0,'#000',.5),(1,'#000',0)])
    d+=lg('frz',0,25,0,69,[(0,'#8d897e'),(.5,'#a9a497'),(1,'#8a8579')])
    d+=lg('soff',0,75,0,88,[(0,'#6c685e'),(1,'#2e2b27')])
    d+=lg('niche',0,12,0,76,[(0,'#171512'),(1,'#3a3732')])
    d+=lg('pan',0,0,0,1,[(0,'#7c786d'),(1,'#908b7f')],False)
    d+=shadow('lsh',.8,1.4,1,.6)
    gf,_=grain('gl',0,0,704,88,7,.7); d+=gf
    b=courses(0,616)+courses(616,88)
    # dentils (tile 640..704 : 8 blocks)  and emblem part
    d+='<pattern id="dent" width="11" height="9" patternUnits="userSpaceOnUse" x="2" y="13"><rect width="7" height="9" fill="url(#fv)"/><rect x="7" y="0" width="1.6" height="9" fill="#000" opacity=".35"/></pattern>'
    b+='<rect x="0" y="13" width="616" height="9" fill="url(#dent)"/><rect x="616" y="13" width="88" height="9" fill="url(#dent)"/>'
    # frieze panels + rosettes
    ros=''.join(f'<ellipse cx="40" cy="39" rx="3.2" ry="6.5" fill="{L}" stroke="{DK}" stroke-width=".7" transform="rotate({k*45} 40 47)"/>' for k in range(8))
    d+=f'<g id="pnl"><rect width="80" height="34" rx="2" fill="#6e6a60"/><rect x="1" y="1" width="78" height="32" rx="1.5" fill="url(#pan)"/><path d="M0 34V0H80" fill="none" stroke="#2a2824" stroke-width="2" opacity=".55"/><path d="M80 0V34H0" fill="none" stroke="{HI}" stroke-width="1.4" opacity=".7"/><g transform="translate(0 -30)" filter="url(#lsh)">{ros}<circle cx="40" cy="47" r="4.2" fill="{HI}" stroke="{DK}" stroke-width=".8"/></g></g>'
    b+='<use href="#pnl" x="620" y="30"/>'
    for i in range(0,616,88):
        if 80<i<480 or i+88>616: continue
        b+=f'<use href="#pnl" x="{i+4}" y="30"/>'
    # central niche
    cx=308
    b+=f'<g filter="url(#lsh)"><path d="M{cx-64} 78V44A64 32 0 0 1 {cx+64} 44V78Z" fill="url(#fv)"/></g>'
    b+=f'<path d="M{cx-58} 76V44A58 29 0 0 1 {cx+58} 44V76Z" fill="url(#niche)" stroke="#1c1a17" stroke-width="2"/>'
    b+=f'<path d="M{cx-58} 76V44A58 29 0 0 1 {cx+58} 44" fill="none" stroke="{HI}" stroke-width="1" opacity=".25" transform="translate(0 1)"/>'
    b+=f'<ellipse cx="{cx}" cy="50" rx="44" ry="26" fill="#8fa" opacity=".05"/>'
    # white tree
    T='#f1ecdc'
    t=f'<g filter="url(#lsh)" fill="none" stroke="{T}" stroke-linecap="round">'
    t+=f'<path d="M{cx-9} 76C{cx-3} 70 {cx-3} 62 {cx-2} 54H{cx+2}C{cx+3} 62 {cx+3} 70 {cx+9} 76Z" fill="{T}" stroke="none"/>'
    br=[(54,[(-9,-4),(-14,-9),(-24,-13)],3.2),(54,[(-2,-9),(-9,-14),(-17,-22)],2.6),(54,[(0,-8),(1,-12),(0,-18)],3),(54,[(2,-9),(9,-14),(17,-22)],2.6),(54,[(9,-4),(14,-9),(24,-13)],3.2),
        (47,[(-6,-3),(-12,-3),(-21,-6)],2),(47,[(6,-3),(12,-3),(21,-6)],2)]
    tips=[]
    for y0,pts,wd in br:
        sx=0
        if y0==47: sx=-3 if pts[0][0]<0 else 3
        x1,y1=cx+sx,y0
        c=[(cx+sx+px,y0+py) for px,py in pts]
        t+=f'<path d="M{x1} {y1}C{c[0][0]} {c[0][1]} {c[1][0]} {c[1][1]} {c[2][0]} {c[2][1]}" stroke-width="{wd}"/>'
        tips.append(c[2])
    t+='</g>'
    t+=f'<g fill="{T}" stroke="#141210" stroke-width=".35" filter="url(#lsh)">'
    for (x,y) in tips:
        for a in (-50,-15,20,55):
            ang=a+(0 if abs(x-cx)<3 else (-20 if x<cx else 20))
            t+=f'<path d="M{x} {y}q-2.6 -5 0 -9q2.6 4 0 9z" transform="rotate({ang} {x} {y})"/>'
    t+='</g>'
    b+=t
    # top star + flanking stars
    def st(x,y,r):
        return f'<g filter="url(#lsh)"><path d="{star(x,y,r,8,.42)}" fill="url(#fv)" stroke="{DK}" stroke-width=".8"/><circle cx="{x}" cy="{y}" r="{r*.22:.1f}" fill="{HI}"/></g>'
    b+=st(cx,20,9)
    for k,(dx,r) in enumerate([(-92,14.4),(-122,12.8),(-150,11.2)]):
        b+=st(cx+dx,47,r)+st(cx-dx,47,r)
    # tile end
    b+=f'<rect x="0" y="0" width="704" height="88" filter="url(#gl)" opacity=".22"/>'
    return svg('human-lintel.svg',704,88,d,b)

# ---------------- SILL: emblem 560 + tile 112 = 672 x 56
def horse(x,y,s=1):
    return (f'<g transform="translate({x} {y}) scale({s})" fill="#e8e3d4">'
    '<path d="M20 15C26 11 44 11 54 14C59 16 59 23 54 26C46 30 28 29 20 25C16 22 16 18 20 15Z"/>'
    '<path d="M21 16C13 12 5 16 1 28C7 21 14 20 20 22Z"/>'
    '<path d="M48 15C52 7 57 3 63 2L71 8C66 13 64 19 58 26Z"/>'
    '<path d="M62 2L64-1L67 1C72 4 77 8 80 14L78 18L72 17L63 10Z"/>'
    '<path d="M54 9C57 4 60 2 63 0" fill="none" stroke="#4f4b44" stroke-width="2"/>'
    '<g fill="none" stroke="#e8e3d4" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"><path d="M52 24L62 28L72 24"/><path d="M47 26L56 33L66 33"/><path d="M27 24L17 30L6 29"/><path d="M33 26L24 34L13 37"/></g>'
    '<circle cx="70" cy="8" r="1.1" fill="#2a2824"/><path d="M28 17C38 14 46 15 54 17" fill="none" stroke="#9a958a" stroke-width="1.3"/></g>')
def sill():
    d=pal_defs()
    d+=lg('rim',0,0,0,12,[(0,HI),(.3,L),(1,M)],True)
    d+=lg('cast',0,0,0,12,[(0,'#000',.6),(1,'#000',0)])
    d+=lg('fz',0,12,0,44,[(0,'#4c4943'),(.5,'#615d54'),(1,'#56524a')])
    d+=lg('base',0,44,0,56,[(0,L),(.3,M),(1,'#34312c')])
    d+=shadow('hsh',1,1.5,1.2,.7)
    gf,_=grain('gs',0,0,672,56,9,.7); d+=gf
    def band(x0,w):
        s=f'<rect x="{x0}" y="0" width="{w}" height="56" fill="#34312c"/>'
        s+=f'<rect x="{x0}" y="0" width="{w}" height="9" fill="url(#rim)"/><rect x="{x0}" y="0" width="{w}" height="1.6" fill="{HI}"/><rect x="{x0}" y="5" width="{w}" height="1" fill="{DK}" opacity=".4"/>'
        s+=f'<rect x="{x0}" y="9" width="{w}" height="3" fill="#201e1b"/>'
        s+=f'<rect x="{x0}" y="12" width="{w}" height="33" fill="url(#fz)"/><rect x="{x0}" y="12" width="{w}" height="9" fill="url(#cast)" opacity=".8"/>'
        s+=f'<rect x="{x0}" y="45" width="{w}" height="11" fill="url(#base)"/><rect x="{x0}" y="45" width="{w}" height="1.6" fill="{HI}"/><rect x="{x0}" y="53" width="{w}" height="3" fill="#000" opacity=".4"/>'
        return s
    b=band(0,560)+band(560,112)
    b+='<g filter="url(#hsh)">'
    for k in range(5):
        if k==2: continue
        b+=horse(6+112*k,11,1.0)
    b+=horse(566,11,1.0)+'</g>'
    # emblem centre: roundel with star on a plinth
    cx=280
    b+=f'<rect x="{cx-70}" y="10" width="140" height="36" fill="url(#fz)"/>'
    b+=f'<g filter="url(#hsh)"><rect x="{cx-66}" y="6" width="132" height="44" rx="3" fill="url(#fv)" stroke="{DK}" stroke-width="1"/><rect x="{cx-60}" y="12" width="120" height="32" rx="2" fill="#2f2d29" stroke="{DK}"/></g>'
    b+=f'<g filter="url(#hsh)"><circle cx="{cx}" cy="28" r="14" fill="url(#fv)" stroke="{DK}" stroke-width="1"/><path d="{star(cx,28,12,8,.45)}" fill="{HI}" stroke="{DK}" stroke-width=".7"/></g>'
    for dx in (-44,44):
        b+=f'<g filter="url(#hsh)"><circle cx="{cx+dx}" cy="28" r="9" fill="url(#fv)" stroke="{DK}" stroke-width=".9"/><circle cx="{cx+dx}" cy="28" r="4" fill="{HI}" stroke="{DK}" stroke-width=".6"/></g>'
    b+=f'<rect x="0" y="0" width="672" height="56" filter="url(#gs)" opacity=".22"/>'
    return svg('human-sill.svg',672,56,d,b)

def corner():
    d=pal_defs()+lg('nb',0,6,0,96,[(0,'#1d1b18'),(1,'#413e38')])
    d+=lg('hf',20,0,80,0,[(0,'#6f6b61'),(.5,L),(1,HI)])
    d+=shadow('ksh',2,2.5,2.2,.7)
    d+=rg('glow',60,45,50,[(0,'#9fb',.16),(1,'#9fb',0)])
    b=''
    # block with stepped frame
    b+='<g filter="url(#ksh)"><path d="M2 2H92L98 8V92L92 98H2Z" fill="url(#fv)" stroke="#2a2824" stroke-width="1.2"/></g>'
    b+=f'<path d="M6 6H90L94 10V90L90 94H6Z" fill="none" stroke="{HI}" stroke-width="1" opacity=".5"/>'
    b+='<path d="M11 11H86V86H11Z" fill="url(#nb)" stroke="#15130f" stroke-width="2"/><rect x="11" y="11" width="75" height="75" fill="url(#glow)"/>'
    b+=f'<path d="M86 11V86H11" fill="none" stroke="{HI}" stroke-width="1.4" opacity=".6"/>'
    # shoulders / mantle
    b+='<path d="M12 86V74C20 66 30 64 40 62L66 62C74 64 82 68 85 74V86Z" fill="#6b675d" stroke="#1b1916" stroke-width="1"/>'
    b+=f'<path d="M12 86V80C26 74 40 76 50 70C60 76 74 74 85 80V86Z" fill="{M}"/>'
    # crown (winged) behind head
    b+='<g filter="url(#sh)">'
    b+=f'<path d="M26 26C20 24 17 18 16 12C22 14 28 16 32 20Z" fill="{L}" stroke="{DK}" stroke-width=".7"/>'  # wing
    b+=f'<path d="M24 31C17 30 13 25 12 19C19 20 26 23 30 27Z" fill="{M}" stroke="{DK}" stroke-width=".7"/>'
    b+='</g>'
    # back of head / hair
    b+=f'<path d="M30 24C26 36 27 50 33 62L48 66L52 42L50 24Z" fill="#59554c" stroke="#1b1916" stroke-width=".8"/>'
    # neck
    b+=f'<path d="M40 56L58 56L62 70L36 70Z" fill="#6b675d"/>'
    # face: front plane light, side plane mid
    b+=f'<g filter="url(#ksh)"><path d="M46 24L62 24L63 30L66 40L64 44L71 54L67 57L68 60L66 63L67 66L65 72L58 70L47 62L44 46Z" fill="url(#hf)" stroke="#1b1916" stroke-width="1"/></g>'
    b+=f'<path d="M46 24L56 24L58 40L66 40L64 44L71 54L67 57L58 56L52 62L47 62L44 46Z" fill="{M}" opacity=".55"/>'
    b+=f'<path d="M56 24L62 24L63 30L66 40L58 40Z" fill="{HI}" opacity=".7"/>'
    b+=f'<path d="M64 44L71 54L67 57L64 52Z" fill="{HI}" opacity=".8"/>'
    # brow and eye
    b+=f'<path d="M54 40L66 40L66 42L55 43Z" fill="#2a2824"/><path d="M56 44L63 44L62 46L57 46Z" fill="#1b1916"/>'
    # mouth
    b+=f'<path d="M62 62L67 62" stroke="#2a2824" stroke-width="1.3"/>'
    # crown band + points (front)
    b+=f'<g filter="url(#ksh)"><path d="M33 26V12L40 19L47 8L54 19L61 8L68 19L70 12V26Z" fill="url(#fv)" stroke="#1b1916" stroke-width="1"/><rect x="33" y="22" width="37" height="7" fill="{L}" stroke="#1b1916" stroke-width=".9"/></g>'
    b+=f'<circle cx="51" cy="25.5" r="1.8" fill="{D}"/><circle cx="42" cy="25.5" r="1.3" fill="{D}"/><circle cx="60" cy="25.5" r="1.3" fill="{D}"/>'
    # beard locks
    b+='<g filter="url(#ksh)">'
    b+=f'<path d="M47 62L58 66L65 72L67 82L62 86L58 78L54 88L48 80L44 86L40 74L40 62Z" fill="url(#hf)" stroke="#1b1916" stroke-width=".9"/>'
    b+='</g>'
    b+=f'<path d="M50 66L52 80M57 70L58 80M45 66L44 78" stroke="#2a2824" stroke-width="1.2"/>'
    b+=f'<path d="M62 70L66 72L66 80L62 84Z" fill="{HI}" opacity=".5"/>'
    return svg('human-corner.svg',100,100,d,b)

# =============================================================== authored relief (height pass)
def corner_h():
    """King in profile, in a stepped block: skull/cheek/brow/nose volumes, beard mass, crown points."""
    d=hdome('skull',.46,.74,.40,.45)+hdome('cheek',.46,.86,.62,.5,r=.62)+hdome('chest',.30,.52,.5,.8,r=.62)
    d+=hdome('nose',.70,.96,.40,.35,r=.6)+hdome('gem',.88,1.0)+hdome('beard',.55,.80,.45,.35,r=.62)
    d+=hcyl('neck',40,0,62,0,.38,.58)+hcyl('band',0,22,0,29,.70,.95)
    d+=hcyl('wingl',12,0,34,0,.28,.40)
    b=''
    b+=hrect(0,0,100,100,.30)
    # stepped block: 5 px of outer chamfer, a step, then the recess
    b+=bevel('M2 2H92L98 8V92L92 98H2Z',.28,.62,4,6)
    b+=flat('M6 6H90L94 10V90L90 94H6Z',.60)
    b+=flat('M11 11H86V86H11Z',.40)+flat('M12.5 12.5H84.5V84.5H12.5Z',.22)+flat('M14 14H83V83H14Z',.12)
    # mantle / shoulders: a broad swelling
    b+='<path d="M12 86V74C20 66 30 64 40 62L66 62C74 64 82 68 85 74V86Z" fill="url(#chest)"/>'
    b+=tube('M16 84C26 74 38 72 50 71C62 72 74 74 82 84',6,.30,.60)
    # wings behind the crown (feather steps)
    b+=flat('M26 26C20 24 17 18 16 12C22 14 28 16 32 20Z',.44)+flat('M24 31C17 30 13 25 12 19C19 20 26 23 30 27Z',.36)
    b+=tube('M26 25C22 22 19 18 17 13',1.5,.44,.54)+tube('M24 30C19 28 15 25 13 20',1.5,.38,.46)
    # back of head / hair
    b+='<path d="M30 24C26 36 27 50 33 62L48 66L52 42L50 24Z" fill="url(#skull)"/>'
    # neck: a short cylinder
    b+='<path d="M40 56L58 56L62 70L36 70Z" fill="url(#neck)"/>'
    # face: a skull-and-cheek mass with a bone structure drawn on top
    face='M46 24L62 24L63 30L66 40L64 44L71 54L67 57L68 60L66 63L67 66L65 72L58 70L47 62L44 46Z'
    b+=f'<path d="{face}" fill="url(#cheek)"/>'
    b+=flat('M52 40L63 40L65 46L62 52L56 56L52 52Z',.74)                       # cheek plane
    b+='<ellipse cx="58.5" cy="49.5" rx="6.5" ry="5" fill="url(#cheek)"/>'      # cheekbone
    b+=tube('M53 40.5C58 39.5 63 40 67 41.5',3.4,.66,.90)                        # brow ridge
    b+='<ellipse cx="59.5" cy="45" rx="4.2" ry="2.3" fill="'+gv(.44)+'"/>'       # eye socket
    b+='<ellipse cx="60.2" cy="45.2" rx="1.7" ry=".9" fill="'+gv(.46)+'"/>'
    b+=tube('M64 41C65.5 47 68 51 70 54.5',3.8,.70,.98)                          # nose bridge + ridge
    b+='<ellipse cx="69.5" cy="54.5" rx="3" ry="2.6" fill="url(#nose)"/>'        # nose tip
    b+='<ellipse cx="66" cy="56.8" rx="1.4" ry=".8" fill="'+gv(.55)+'"/>'        # nostril
    b+=tube('M60 61.5C63 60.5 66 61 68 62.4',2.6,.62,.86)                        # lips
    b+='<path d="M61 62.2L67.5 62.3" stroke="'+gv(.42)+'" stroke-width=".9" fill="none"/>'
    b+=flat('M52 24L56 24L58 40L55 40Z',.60)+tube('M47 26C46 34 46 42 48 52',3,.60,.74)  # temple / hairline
    # crown: a band that is round in section, five points as faceted pyramids, three gems
    b+='<path d="M33 22H70V29H33Z" fill="url(#band)"/>'
    for px,py,vl,vr in ((33,12,33,40),(47,8,40,54),(61,8,54,68),(70,12,68,70)):
        b+=flat(f'M{vl} 24L{vl} 19L{px} {py}L{px} 24Z',.80)+flat(f'M{px} 24L{px} {py}L{vr} 19L{vr} 24Z',.94)
    b+='<path d="M33 22H70V29H33Z" fill="url(#band)"/>'
    for gx,r in ((51,2.2),(42,1.6),(60,1.6)):
        b+=f'<ellipse cx="{gx}" cy="25.5" rx="{r}" ry="{r}" fill="url(#gem)"/>'
    # beard: one heavy mass, locks as round ridges with grooves between
    bd='M47 62L58 66L65 72L67 82L62 86L58 78L54 88L48 80L44 86L40 74L40 62Z'
    b+=f'<path d="{bd}" fill="url(#beard)"/>'
    for p,w in (('M50 65C52 70 52 76 52 82',4.2),('M57 68C58 73 58 77 58 82',3.8),('M44 66C44 71 43 76 43 82',3.6),('M62 72C64 76 64 80 63 84',3.2)):
        b+=tube(p,w,.62,.92)
    b+=tube('M42 60C48 62 56 64 63 70',3,.70,.90)                                  # moustache sweep
    return hsvg('human-corner.h.svg',100,100,d,b)

def capital_h():
    """Ionic capital: abacus slab, echinus bowl, two spiral volutes, five acanthus leaves, crown relief, astragal."""
    d=hcyl('ech',6,0,66,0,.42,.78)+hdome('vol',.62,.95)+hdome('gem',.88,1.0)
    d+=hcyl('astr',0,58,0,64,.36,.84)+hcyl('abv',0,0,0,11,.58,.92,n=6,p=.9)
    d+=hcyl('leaf',0,0,1,0,.52,.88,False)
    b=hrect(0,0,72,64,.12)
    b+='<path d="M6 13C6 34 14 44 14 53H58C58 44 66 34 66 13Z" fill="url(#ech)"/>'
    b+=tube('M10 16C10 32 17 42 18 52',3.5,.62,.80)+tube('M62 16C62 32 55 42 54 52',3.5,.62,.80)
    # acanthus leaves: a rib, two rounded lobes and a curled tip
    for x in (17,27,36,45,55):
        h=44 if x==36 else 47
        lf=f'M{x-6} 59Q{x-8} 50 {x-2} {h}Q{x} {h-5} {x+2} {h}Q{x+8} 50 {x+6} 59Z'
        b+=f'<path d="{lf}" fill="url(#leaf)"/>'
        b+=tube(f'M{x-3.2} 58Q{x-4.4} 51 {x-1.6} {h+3}',2.4,.70,.86)+tube(f'M{x+3.2} 58Q{x+4.4} 51 {x+1.6} {h+3}',2.4,.70,.86)
        b+=tube(f'M{x} 59V{h+2}',1.6,.84,1.0)
    # crown relief on the echinus
    b+=flat('M25 38V24L31 30L36 20L41 30L47 24V38Z',.88)
    b+=flat('M25 38V24L31 30L36 20L36 38Z',.84)+flat('M36 38V20L41 30L47 24V38Z',.93)
    b+='<path d="M25 33H47V39H25Z" fill="'+gv(.95)+'"/>'+f'<circle cx="36" cy="36" r="1.5" fill="url(#gem)"/><circle cx="36" cy="18.8" r="2" fill="url(#gem)"/>'
    # volutes: a disc with a spiral groove
    for cx in (13,59):
        b+=f'<circle cx="{cx}" cy="20" r="8" fill="url(#vol)"/>'
        b+=f'<path d="M{cx} 20m0 0a1.5 1.5 0 0 1 3 0a4 4 0 0 1-6 3a6 6 0 0 1 0-9" fill="none" stroke="{gv(.50)}" stroke-width="1.5" stroke-linecap="round"/>'
        b+=f'<circle cx="{cx}" cy="20" r="1.6" fill="url(#gem)"/>'
    # abacus: a slab with a chamfered top edge and a recessed lower edge
    b+='<rect x="1" y="0" width="70" height="11" rx="1.5" fill="url(#abv)"/>'
    b+=hrect(1,0,70,1.8,.98)+hrect(1,9,70,2,.50)+hrect(3,4.6,66,.9,.66)
    # astragal ring
    b+=f'<rect x="12" y="58" width="48" height="6" rx="3" fill="url(#astr)"/>'
    return hsvg('human-capital.h.svg',72,64,d,b)

def lintel_h():
    """Authored where it is sculptural: the three rosette panels, the arched niche with the white tree, the stars."""
    cx=308
    d=hdome('pet',.50,.88)+hdome('ctr',.62,1.0)+hcyl('trk',cx-9,0,cx+9,0,.28,.64)
    d+=hcyl('arc',0,0,1,0,.55,.80,False)
    b=''
    # rosette panels: a frame, a recessed field, eight domed petals, a domed centre
    pn=''
    pn+=hrect(0,0,80,34,.52,2)+hrect(1.6,1.6,76.8,30.8,.36,1.5)
    for k in range(8):
        pn+=f'<ellipse cx="40" cy="9" rx="3.2" ry="6.5" fill="url(#pet)" transform="rotate({k*45} 40 17)"/>'
    pn+='<circle cx="40" cy="17" r="4.2" fill="url(#ctr)"/>'
    for x in (4,532,620):
        b+=f'<g transform="translate({x} 30)">{pn}</g>'
    # niche: moulded arch frame, a deep recess
    arch=lambda r1,r2,y0,y1: f'M{cx-r1} {y1}V{y0}A{r1} {r2} 0 0 1 {cx+r1} {y0}V{y1}Z'
    b+=flat(arch(64,32,44,78),.70)
    b+=flat(arch(61,30.5,44,77),.78)
    b+=flat(arch(58,29,44,76),.40)+flat(arch(56.6,28.2,44,76),.24)+flat(arch(55.4,27.6,44,76),.13)
    # white tree: round trunk, round branches, leaves
    b+='<path d="M%d 76C%d 70 %d 62 %d 54H%d C%d 62 %d 70 %d 76Z" fill="url(#trk)"/>'%(cx-9,cx-3,cx-3,cx-2,cx+2,cx+3,cx+3,cx+9)
    br=[(54,[(-9,-4),(-14,-9),(-24,-13)],3.2),(54,[(-2,-9),(-9,-14),(-17,-22)],2.6),(54,[(0,-8),(1,-12),(0,-18)],3),(54,[(2,-9),(9,-14),(17,-22)],2.6),(54,[(9,-4),(14,-9),(24,-13)],3.2),
        (47,[(-6,-3),(-12,-3),(-21,-6)],2),(47,[(6,-3),(12,-3),(21,-6)],2)]
    tips=[]
    for y0,pts,wd in br:
        sx=0
        if y0==47: sx=-3 if pts[0][0]<0 else 3
        c=[(cx+sx+px,y0+py) for px,py in pts]
        b+=tube(f'M{cx+sx} {y0}C{c[0][0]} {c[0][1]} {c[1][0]} {c[1][1]} {c[2][0]} {c[2][1]}',wd+.6,.30,.66)
        tips.append(c[2])
    for (x,y) in tips:
        for a in (-50,-15,20,55):
            ang=a+(0 if abs(x-cx)<3 else (-20 if x<cx else 20))
            b+=f'<path d="M{x} {y}q-2.6 -5 0 -9q2.6 4 0 9z" transform="rotate({ang} {x} {y})" fill="{gv(.70)}"/>'
    # stars (enlarged), faceted; a raised boss at the centre
    def st(x,y,r):
        return star_facets(x,y,r,8,.42)+f'<circle cx="{x}" cy="{y}" r="{r*.22:.1f}" fill="{gv(.99)}"/>'
    b+=st(cx,20,9)
    for dx,r in [(-92,14.4),(-122,12.8),(-150,11.2)]:
        b+=st(cx+dx,47,r)+st(cx-dx,47,r)
    return hsvg('human-lintel.h.svg',704,88,d,b)

def sill_h():
    """Horses (body and neck as cylinders, round legs, domed head), the roundel with the star, two discs."""
    d=hcyl('body',0,11,0,30,.50,.96)+hcyl('neck',48,6,66,16,.52,.96)+hdome('head',.52,.98,.5,.5)+hcyl('tail',1,28,20,18,.52,.86)
    d+=hcyl('plin',0,6,0,50,.58,.82,n=6,p=.9)+hdome('rnd',.74,.98)+hdome('dsk',.76,.96)+hdome('ctr',.88,1.0)
    def horse(x,y):
        s=f'<g transform="translate({x} {y})">'
        s+='<path d="M21 16C13 12 5 16 1 28C7 21 14 20 20 22Z" fill="url(#tail)"/>'
        # far legs a little lower than near legs
        s+=tube('M47 26L56 33L66 33',4,.50,.80)+tube('M33 26L24 34L13 37',4,.50,.80)
        s+='<path d="M20 15C26 11 44 11 54 14C59 16 59 23 54 26C46 30 28 29 20 25C16 22 16 18 20 15Z" fill="url(#body)"/>'
        s+='<path d="M48 15C52 7 57 3 63 2L71 8C66 13 64 19 58 26Z" fill="url(#neck)"/>'
        s+=tube('M52 24L62 28L72 24',4,.52,.92)+tube('M27 24L17 30L6 29',4,.52,.92)
        s+=tube('M54 9C57 4 60 2 63 0',2.4,.60,.98)   # mane crest
        s+='<path d="M62 2L64-1L67 1C72 4 77 8 80 14L78 18L72 17L63 10Z" fill="url(#head)"/>'
        s+=f'<circle cx="70" cy="8" r="1.3" fill="{gv(.46)}"/>'
        s+=tube('M28 17C38 14 46 15 54 17',1.2,.80,.94)  # flank line
        return s+'</g>'
    b=''
    for k in range(5):
        if k==2: continue
        b+=horse(6+112*k,11)
    b+=horse(566,11)
    cx=280
    b+=hrect(cx-66,6,132,44,'url(#plin)',3)+hrect(cx-60,12,120,32,.30,2)
    b+=f'<circle cx="{cx}" cy="28" r="14" fill="url(#rnd)"/>'+star_facets(cx,28,12,8,.45,lo=.84,hi=1.0)
    for dx in (-44,44):
        b+=f'<circle cx="{cx+dx}" cy="28" r="9" fill="url(#dsk)"/><circle cx="{cx+dx}" cy="28" r="4" fill="url(#ctr)"/>'
    return hsvg('human-sill.h.svg',672,56,d,b)
