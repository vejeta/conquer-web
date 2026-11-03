from common import *
A,B_,C='#4a4240','#2b2624','#110f0e'; EM='#e07a5a'; EH='#ffb070'; IR='#6e6b72'; IH='#a8a6b0'; IV='#ded2b0'
def base_defs():
    d=lg('fv',0,0,0,1,[(0,'#6a605d'),(.15,A),(.7,B_),(1,C)],False)+lg('iron',0,0,0,1,[(0,IH),(.3,IR),(1,'#26262a')],False)
    d+=lg('ironh',0,0,1,0,[(0,'#1d1d20'),(.3,IR),(.5,IH),(.75,'#4a4a50'),(1,'#161618')],False)
    d+=shadow('sh',1,1.8,1.5,.8)
    d+=f'<filter id="gl" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.2"/></filter>'
    d+=lg('wall',0,0,0,1,[(0,'#171413'),(1,'#0b0909')],False)
    d+=lg('ivory',0,0,0,1,[(0,'#f2e9cc'),(.5,IV),(1,'#7d7152')],False)
    return d
def rivet(x,y,r=2.2):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#iron)" stroke="#050404" stroke-width=".7"/><circle cx="{x-r*.3:.1f}" cy="{y-r*.3:.1f}" r="{r*.35:.1f}" fill="#d8d8e0" opacity=".8"/>'
def crack(p,w=1.4):
    return f'<path d="{p}" fill="none" stroke="{EM}" stroke-width="{w*3}" opacity=".45" filter="url(#gl)"/><path d="{p}" fill="none" stroke="#080606" stroke-width="{w+1.4}" stroke-linejoin="bevel"/><path d="{p}" fill="none" stroke="{EH}" stroke-width="{w*.55:.2f}" stroke-linejoin="bevel"/>'
def column():
    d=base_defs()
    gf,_=grain('g1',0,64,72,72,11,.5); d+=gf
    b='<rect width="72" height="184" fill="url(#wall)"/>'
    # cap: spiked iron collar
    b+='<g filter="url(#sh)">'
    for x in (8,22,36,50,64):
        h=8 if x in (8,64) else 0
        b+=f'<path d="M{x-6} 34L{x} {2+h*2}L{x+6} 34Z" fill="url(#ironh)" stroke="#050404" stroke-width="1"/>'
    b+='<path d="M0 32H72V58L66 64H6L0 58Z" fill="url(#iron)" stroke="#050404" stroke-width="1.3"/>'
    b+='</g>'
    b+='<path d="M0 38H72" stroke="#d8d8e0" stroke-width="1" opacity=".5"/><path d="M0 56H72" stroke="#000" stroke-width="2" opacity=".5"/>'
    for x in (8,22,36,50,64): b+=rivet(x,46,2.4)
    b+=crack('M20 58L24 62L22 64',1)
    # shaft: cracked black stone, jagged periodic edge
    sx='M10 64L14 70L9 79L13 88L8 100L12 112L9 122L13 130L10 136H62L59 130L64 122L60 112L64 100L59 88L63 79L58 70L62 64Z'
    b+=f'<path d="{sx}" transform="translate(0 0)" fill="url(#fv)" opacity="0"/>'
    b+=f'<path d="M10 64H62V136H10Z" fill="#171413"/>'
    b+=f'<path d="{sx}" fill="url(#ironh)" opacity="0"/>'
    b+='<g><path d="M8 64H64V136H8Z" fill="#241f1e"/><path d="M8 64H22V136H8Z" fill="#37302f"/><path d="M50 64H64V136H50Z" fill="#0f0c0c"/>'
    b+='<path d="M22 64V136M50 64V136" stroke="#000" stroke-width="1.5" opacity=".6"/></g>'
    # block seams
    b+='<path d="M8 82H64M8 108H64" stroke="#050404" stroke-width="2"/><path d="M8 83.5H64M8 109.5H64" stroke="#5a504d" stroke-width=".8" opacity=".5"/>'
    # iron strap + rivets
    b+='<rect x="6" y="90" width="60" height="12" fill="url(#iron)" stroke="#050404" stroke-width="1.2"/><path d="M6 91H66" stroke="#e5e5ee" stroke-width=".8" opacity=".5"/>'
    for x in (13,27,45,59): b+=rivet(x,96,2.4)
    b+=crack('M30 64L34 70L30 76L36 82',1.2)+crack('M44 108L40 116L45 124L41 136',1.2)+crack('M14 114L19 120L16 128',1)
    # chain along left edge
    for k in range(3):
        y=64+k*24
        b+=f'<ellipse cx="14" cy="{y+6}" rx="4.2" ry="6.6" fill="none" stroke="#050404" stroke-width="4"/><ellipse cx="14" cy="{y+6}" rx="4.2" ry="6.6" fill="none" stroke="url(#iron)" stroke-width="2.4"/>'
        b+=f'<rect x="12.6" y="{y+15}" width="2.8" height="9" rx="1.4" fill="url(#iron)" stroke="#050404" stroke-width=".8"/>'
    b+=f'<rect x="8" y="64" width="56" height="72" filter="url(#g1)" opacity=".35"/>'
    # base
    b+='<g filter="url(#sh)"><path d="M2 150L8 140H64L70 150V184H2Z" fill="url(#fv)" stroke="#050404" stroke-width="1.3"/></g>'
    b+='<path d="M2 150H70" stroke="#6a605d" stroke-width="1.4"/><path d="M0 160H72M0 172H72" stroke="#050404" stroke-width="1.6"/>'
    b+='<path d="M12 150V184M36 160V172M58 150V184" stroke="#050404" stroke-width="1.2" opacity=".6"/>'
    b+='<rect x="0" y="136" width="72" height="8" fill="url(#iron)" stroke="#050404"/>'
    for x in (8,24,40,56): b+=rivet(x,140,2)
    b+=crack('M28 160L32 166L28 172L34 178',1.2)+rivet(10,176,2.6)+rivet(62,176,2.6)
    return svg('orc-column.svg',72,184,d,b)

def spikes(x0,w):
    s=''
    for x in range(x0,x0+w,44):
        s+=f'<path d="M{x+6} 30L{x+22} 0L{x+38} 30Z" fill="url(#ironh)" stroke="#050404" stroke-width="1.1"/><path d="M{x+22} 2V30" stroke="#d8d8e0" stroke-width=".6" opacity=".6"/>'
    return s
def lintel():
    d=base_defs()+lg('flame',0,62,0,12,[(0,'#ffc060'),(.45,'#ff8a2a'),(1,'#c8401a')])
    gf,_=grain('g2',0,0,704,88,12,.55); d+=gf
    W=704
    b=f'<rect width="{W}" height="88" fill="url(#wall)"/>'
    b+=spikes(0,W)
    b+=f'<rect y="28" width="{W}" height="10" fill="url(#iron)" stroke="#050404" stroke-width="1"/><path d="M0 29.5H{W}" stroke="#e8e8f0" stroke-width=".8" opacity=".6"/>'
    b+=f'<rect y="38" width="{W}" height="40" fill="#241f1e"/><rect y="38" width="{W}" height="8" fill="#000" opacity=".5"/>'
    b+=f'<path d="M0 62H{W}" stroke="#050404" stroke-width="2"/>'
    for k in range(W//44): b+=rivet(k*44+22,33,2.2)
    for k in range(W//88):
        x=k*88
        b+=crack(f'M{x+14} 40L{x+18} 48L{x+13} 55L{x+20} 62L{x+16} 70',1.2)+crack(f'M{x+60} 78L{x+56} 70L{x+63} 64L{x+58} 56',1)
    b+=f'<rect y="74" width="{W}" height="14" fill="url(#iron)" stroke="#050404" stroke-width="1"/><path d="M0 76H{W}" stroke="#e5e5ee" stroke-width=".8" opacity=".4"/>'
    for k in range(W//44): b+=rivet(k*44+22,81,2)
    cx=308
    # eye plate
    b+=f'<g filter="url(#sh)"><path d="M{cx-112} 52L{cx-88} 38L{cx-60} 32L{cx-30} 14L{cx-12} 22L{cx} 0L{cx+12} 22L{cx+30} 14L{cx+60} 32L{cx+88} 38L{cx+112} 52L{cx+88} 70L{cx+60} 80L{cx} 86L{cx-60} 80L{cx-88} 70Z" fill="url(#iron)" stroke="#050404" stroke-width="1.6"/></g>'
    b+=f'<path d="M{cx-98} 52L{cx-80} 42L{cx-56} 37L{cx-28} 22L{cx} 8L{cx+28} 22L{cx+56} 37L{cx+80} 42L{cx+98} 52L{cx+80} 66L{cx+54} 74L{cx} 79L{cx-54} 74L{cx-80} 66Z" fill="#120c0b" stroke="#050404" stroke-width="2"/>'
    b+=f'<ellipse cx="{cx}" cy="46" rx="70" ry="30" fill="{EM}" opacity=".18" filter="url(#gl)"/>'
    # iron brazier with an emissive fire (replaces the v4 eye)
    b+=f'<ellipse cx="{cx}" cy="44" rx="74" ry="34" fill="{EM}" opacity=".16" filter="url(#gl)"/>'
    fl=lambda p,f: f'<path d="{p}" fill="{f}"/>'
    b+=fl(f'M{cx-26} 62C{cx-34} 48 {cx-22} 40 {cx-20} 28C{cx-14} 36 {cx-12} 40 {cx-10} 46C{cx-8} 34 {cx-10} 24 {cx-4} 12C{cx} 22 {cx+6} 26 {cx+6} 40C{cx+10} 34 {cx+12} 30 {cx+12} 24C{cx+20} 34 {cx+26} 46 {cx+22} 62Z','url(#flame)')
    b+=fl(f'M{cx-12} 62C{cx-18} 52 {cx-8} 46 {cx-6} 36C{cx-2} 44 {cx} 46 {cx+2} 40C{cx+8} 48 {cx+12} 54 {cx+8} 62Z','#ffd890')
    b+=fl(f'M{cx-5} 62C{cx-8} 56 {cx-2} 52 {cx} 46C{cx+3} 52 {cx+6} 56 {cx+4} 62Z','#fff4cc')
    b+=f'<g filter="url(#sh)"><path d="M{cx-38} 58H{cx+38}C{cx+36} 68 {cx+26} 76 {cx+14} 76H{cx-14}C{cx-26} 76 {cx-36} 68 {cx-38} 58Z" fill="url(#iron)" stroke="#050404" stroke-width="1.6"/><rect x="{cx-40}" y="55" width="80" height="6" rx="3" fill="url(#ironh)" stroke="#050404" stroke-width="1.2"/></g>'
    b+=f'<path d="M{cx-26} 66H{cx+26}" stroke="{EM}" stroke-width="1.4" opacity=".7"/>'
    for dx in (-90,90): b+=rivet(cx+dx,52,3)
    b+=f'<rect width="{W}" height="88" filter="url(#g2)" opacity=".25"/>'
    return svg('orc-lintel.svg',W,88,d,b)

def tusk(x,flip=1,h=30):
    # curved ivory tusk rising from y=34, tilting toward centre
    s=flip
    return (f'<path d="M{x-s*8} 36C{x-s*10} 22 {x-s*4} 10 {x+s*9} 3C{x+s*3} 12 {x+s*2} 24 {x+s*7} 36Z" fill="url(#ivory)" stroke="#2a2418" stroke-width="1"/>'
            f'<path d="M{x-s*6} 34C{x-s*7} 22 {x-s*3} 12 {x+s*6} 5" fill="none" stroke="#fff8e0" stroke-width="1" opacity=".7"/>')
def sill():
    d=base_defs()
    gf,_=grain('g3',0,0,672,56,13,.55); d+=gf
    W=672
    b=f'<rect width="{W}" height="56" fill="url(#wall)"/>'
    b+=f'<rect y="34" width="{W}" height="22" fill="url(#fv)"/><rect y="34" width="{W}" height="3" fill="url(#iron)"/><rect y="33" width="{W}" height="1.2" fill="#e5e5ee" opacity=".5"/>'
    b+=f'<rect y="37" width="{W}" height="4" fill="#000" opacity=".5"/>'
    for k in range(W//112):
        x=k*112
        b+=f'<g filter="url(#sh)">'+tusk(x+30,1)+tusk(x+82,-1)+'</g>'
        b+=rivet(x+56,45,2.4)+crack(f'M{x+8} 56L{x+14} 50L{x+10} 46L{x+20} 41',1)+crack(f'M{x+96} 56L{x+90} 49L{x+98} 44',1)
    cx=280
    b+=f'<rect x="{cx-70}" y="0" width="140" height="56" fill="url(#wall)"/><rect x="{cx-70}" y="34" width="140" height="22" fill="url(#fv)"/>'
    b+=f'<g filter="url(#sh)"><circle cx="{cx}" cy="30" r="25" fill="url(#iron)" stroke="#050404" stroke-width="1.4"/><circle cx="{cx}" cy="30" r="19" fill="#120c0b" stroke="#050404" stroke-width="1.6"/></g>'
    # skull small: crossed tusks
    b+=f'<path d="M{cx-18} 44C{cx-16} 26 {cx-6} 14 {cx+12} 10C{cx+2} 20 {cx+4} 32 {cx+2} 44Z" fill="url(#ivory)" stroke="#2a2418"/><path d="M{cx+18} 44C{cx+16} 26 {cx+6} 14 {cx-12} 10C{cx-2} 20 {cx-4} 32 {cx-2} 44Z" fill="url(#ivory)" stroke="#2a2418"/>'
    b+=f'<circle cx="{cx}" cy="30" r="4" fill="{EM}"/><circle cx="{cx}" cy="30" r="2" fill="{EH}"/>'
    for dx in (-30,30): b+=rivet(cx+dx,30,2.4)
    b+=f'<rect width="{W}" height="56" filter="url(#g3)" opacity=".25"/>'
    return svg('orc-sill.svg',W,56,d,b)

def corner():
    d=base_defs()+lg('bone',0,0,1,1,[(0,'#f4ecd2'),(.6,'#c9bd98'),(1,'#7d7152')],False)
    d+=rg('boss',50,50,48,[(0,'#4a484f'),(.7,'#2b2a30'),(1,'#121214')])
    d+=rg('sock',0,0,1,[(0,'#fff0a0'),(.4,EH),(1,'#b83a14')])
    b='<g filter="url(#sh)">'
    import math
    for i in range(12):
        a=math.radians(i*30+15)
        x1,y1=50+36*math.cos(a),50+36*math.sin(a); x2,y2=50+52*math.cos(a),50+52*math.sin(a)
        xa,ya=50+40*math.cos(a+.2),50+40*math.sin(a+.2); xb,yb=50+40*math.cos(a-.2),50+40*math.sin(a-.2)
        b+=f'<path d="M{xa:.1f} {ya:.1f}L{x2:.1f} {y2:.1f}L{xb:.1f} {yb:.1f}Z" fill="url(#ironh)" stroke="#050404" stroke-width=".9"/>'
    b+='<circle cx="50" cy="50" r="42" fill="url(#iron)" stroke="#050404" stroke-width="1.5"/></g>'
    b+='<circle cx="50" cy="50" r="37" fill="url(#boss)" stroke="#050404" stroke-width="2"/>'
    for k in range(8):
        a=math.radians(k*45+22.5); b+=rivet(round(50+39.5*math.cos(a),1),round(50+39.5*math.sin(a),1),1.9)
    # skull
    b+='<g filter="url(#sh)"><path d="M24 48C22 28 36 16 50 16C64 16 78 28 76 48C76 54 72 58 70 60L70 66H30V60C28 58 24 54 24 48Z" fill="url(#bone)" stroke="#2a2418" stroke-width="1.4"/></g>'
    b+='<path d="M30 60C34 62 40 62 50 62C60 62 66 62 70 60" fill="none" stroke="#2a2418" stroke-width="1"/>'
    b+=f'<path d="M29 38C32 33 42 33 46 40C47 48 43 54 37 54C31 54 28 46 29 38Z" fill="#150808" stroke="#050202" stroke-width="1.2"/><path d="M71 38C68 33 58 33 54 40C53 48 57 54 63 54C69 54 72 46 71 38Z" fill="#150808" stroke="#050202" stroke-width="1.2"/>'
    b+=f'<ellipse cx="38" cy="45" rx="4" ry="5" fill="url(#sock)"/><ellipse cx="62" cy="45" rx="4" ry="5" fill="url(#sock)"/><circle cx="38" cy="45" r="8" fill="{EM}" opacity=".3" filter="url(#gl)"/><circle cx="62" cy="45" r="8" fill="{EM}" opacity=".3" filter="url(#gl)"/>'
    b+='<path d="M50 50L45 60H55Z" fill="#150808" stroke="#050202" stroke-width="1"/>'
    b+='<path d="M32 60H68V68H32Z" fill="url(#bone)" stroke="#2a2418" stroke-width="1.2"/><path d="M38 60V68M44 60V68M50 60V68M56 60V68M62 60V68" stroke="#2a2418" stroke-width="1.2"/>'
    b+=f'<path d="M34 66C30 74 32 82 38 82C36 76 38 70 40 66Z" fill="url(#ivory)" stroke="#2a2418" stroke-width="1"/><path d="M66 66C70 74 68 82 62 82C64 76 62 70 60 66Z" fill="url(#ivory)" stroke="#2a2418" stroke-width="1"/>'
    b+=crack('M50 18L46 26L51 30',1)
    return svg('orc-corner.svg',100,100,d,b)

# =============================================================== authored relief (height pass)
def hrivet(x,y,r):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#hrv)"/>'
def _spike_ring(cx,cy,r0,r1,hw,n=12,rot=15):
    s=''
    for i in range(n):
        a=i*360/n+rot
        s+=f'<g transform="rotate({a+90:.1f} {cx} {cy})">{cone(cx,cy-r1,cy-r0,hw,.50,.98)}</g>'
    return s

def capital_h():
    """Spiked collar: five cones, an iron band round in section, rivets, cracks cut into the iron."""
    d=hdome('hrv',.70,1.0)+hcyl('col',0,32,0,64,.46,.92,True,n=10,p=.7)
    b=hrect(0,0,72,64,.08)
    for x in (8,22,36,50,64):
        h=8 if x in (8,64) else 0
        b+=cone(x,2+h*2,34,6.5,.50,.98,n=7)
    b+='<path d="M0 32H72V58L66 64H6L0 58Z" fill="url(#col)"/>'
    b+=hrect(0,37.4,72,1.6,.98)+hrect(0,55,72,2,.46)
    for x in (8,22,36,50,64): b+=hrivet(x,46,2.4)
    b+=f'<path d="M20 58L24 62L22 64" fill="none" stroke="{gv(.36)}" stroke-width="1.6"/>'
    return hsvg('orc-capital.h.svg',72,64,d,b)

def corner_h():
    """Skull on a spiked boss: cranium dome, brow ridges, deep eye sockets and nasal cavity, cheekbones, teeth, round tusks."""
    d=hdome('hrv',.70,1.0)+hdome('cran',.56,.98,.5,.42,r=.62)+hdome('sock',.34,.04,.5,.5,r=.5)
    d+=hdome('boss',.30,.20,.5,.5,r=.5)+hdome('chk',.70,.98)+hcyl('tth',0,60,0,68,.70,.92,True,n=6,p=.8)
    b=hrect(0,0,100,100,.0)
    b+=_spike_ring(50,50,38,53,8.4)
    b+='<circle cx="50" cy="50" r="42.5" fill="'+gv(.58)+'"/>'
    b+=tube('M50 7.5a42.5 42.5 0 1 0 .01 0',5,.54,.92,n=9)
    b+='<circle cx="50" cy="50" r="38" fill="'+gv(.40)+'"/><circle cx="50" cy="50" r="36.6" fill="url(#boss)"/>'
    for k in range(8):
        a=math.radians(k*45+22.5); b+=hrivet(round(50+39.5*math.cos(a),1),round(50+39.5*math.sin(a),1),1.9)
    # cranium and jaw
    b+='<path d="M24 48C22 28 36 16 50 16C64 16 78 28 76 48C76 54 72 58 70 60L70 66H30V60C28 58 24 54 24 48Z" fill="url(#cran)"/>'
    b+=tube('M27 37C31 29 43 30 48 38',3.4,.80,1.0,n=6)+tube('M73 37C69 29 57 30 52 38',3.4,.80,1.0,n=6)    # brow ridges
    b+='<ellipse cx="29" cy="56" rx="5.5" ry="4.5" fill="url(#chk)"/><ellipse cx="71" cy="56" rx="5.5" ry="4.5" fill="url(#chk)"/>'
    for sx in ('M29 38C32 33 42 33 46 40C47 48 43 54 37 54C31 54 28 46 29 38Z','M71 38C68 33 58 33 54 40C53 48 57 54 63 54C69 54 72 46 71 38Z'):
        b+=f'<path d="{sx}" fill="none" stroke="{gv(.50)}" stroke-width="3.2" stroke-linejoin="round"/><path d="{sx}" fill="url(#sock)"/>'
    b+=f'<path d="M50 50L45 60H55Z" fill="{gv(.06)}" stroke="{gv(.34)}" stroke-width="1.6" stroke-linejoin="round"/>'
    b+='<path d="M32 60H68V68H32Z" fill="'+gv(.52)+'"/>'
    for i in range(5):
        x0=32+i*7.2
        b+=f'<rect x="{x0+.5:.1f}" y="60.5" width="6.2" height="7" rx="2.4" fill="url(#tth)"/>'
    for sx in (-1,1):
        x=50+sx*13
        b+=tube(f'M{x} 66C{x-sx*3} 74 {x-sx*1.5} 80 {x-sx*.5} 82',5,.56,.98,n=8)
    b+=f'<path d="M50 18L46 26L51 30" fill="none" stroke="{gv(.40)}" stroke-width="1.4"/>'
    return hsvg('orc-corner.h.svg',100,100,d,b)

def corner_e():
    """Eye-fire: a hot core, a soft edge, slightly brighter toward the lower rim (the glow pools in the bowl of the socket)."""
    d='<filter id="b1" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation=".6"/></filter>'
    d+='<radialGradient id="eg" cx=".5" cy=".58" r=".55"><stop offset="0" stop-color="#fff"/><stop offset=".45" stop-color="#d0d0d0"/><stop offset=".8" stop-color="#7a7a7a"/><stop offset="1" stop-color="#4a4a4a"/></radialGradient>'
    b=''.join(f'<ellipse cx="{x}" cy="45" rx="4.6" ry="5.6" fill="url(#eg)" filter="url(#b1)"/>' for x in (38,62))
    return hsvg('orc-corner.e.svg',100,100,d,b)

def lintel_h():
    """Cones along the top, rounded iron rails with rivets, the brazier: a hemispherical bowl, a round rim, coals and the flames."""
    cx=308; W=704
    d=hdome('hrv',.70,1.0)+hcyl('rail',0,28,0,38,.50,.92,True,n=6,p=.8)+hcyl('rail2',0,74,0,88,.50,.92,True,n=6,p=.8)
    d+=hcyl('bowl',0,58,0,76,.52,.92,True,n=8,p=.7)+hcyl('bowlh',cx-38,0,cx+38,0,.50,.92,True,n=10,p=.6)+hcyl('rim',0,55,0,61,.78,1.0,True,n=6,p=.8)
    d+=hdome('crl',.46,.62)
    b=''
    for x in range(0,W,44):
        b+=cone(x+22,0,30,16,.50,.98,n=8)
    b+=f'<rect y="28" width="{W}" height="10" fill="url(#rail)"/><rect y="74" width="{W}" height="14" fill="url(#rail2)"/>'
    for k in range(W//44):
        b+=hrivet(k*44+22,33,2.2)+hrivet(k*44+22,81,2)
    pl=lambda i,o: f'M{cx-i*112} 52L{cx-i*88} 38L{cx-i*60} 32L{cx-i*30} 14L{cx-i*12} 22L{cx} 0L{cx+i*12} 22L{cx+i*30} 14L{cx+i*60} 32L{cx+i*88} 38L{cx+i*112} 52L{cx+i*88} 70L{cx+i*60} 80L{cx} 86L{cx-i*60} 80L{cx-i*88} 70Z'
    b+=bevel(pl(1,0),.50,.78,4,6)
    rec=f'M{cx-98} 52L{cx-80} 42L{cx-56} 37L{cx-28} 22L{cx} 8L{cx+28} 22L{cx+56} 37L{cx+80} 42L{cx+98} 52L{cx+80} 66L{cx+54} 74L{cx} 79L{cx-54} 74L{cx-80} 66Z'
    b+=f'<path d="{rec}" fill="{gv(.46)}"/><path d="{rec}" fill="{gv(.30)}" transform="translate({cx} 44) scale(.975 .955) translate({-cx} -44)"/><path d="{rec}" fill="{gv(.14)}" transform="translate({cx} 44) scale(.95 .91) translate({-cx} -44)"/>'
    # flames: soft domes, nested, taller in the middle; every tongue is round in section
    b+=f'<ellipse cx="{cx}" cy="58" rx="34" ry="5" fill="url(#crl)"/>'
    fl1=f'M{cx-26} 62C{cx-34} 48 {cx-22} 40 {cx-20} 28C{cx-14} 36 {cx-12} 40 {cx-10} 46C{cx-8} 34 {cx-10} 24 {cx-4} 12C{cx} 22 {cx+6} 26 {cx+6} 40C{cx+10} 34 {cx+12} 30 {cx+12} 24C{cx+20} 34 {cx+26} 46 {cx+22} 62Z'
    fl2=f'M{cx-12} 62C{cx-18} 52 {cx-8} 46 {cx-6} 36C{cx-2} 44 {cx} 46 {cx+2} 40C{cx+8} 48 {cx+12} 54 {cx+8} 62Z'
    fl3=f'M{cx-5} 62C{cx-8} 56 {cx-2} 52 {cx} 46C{cx+3} 52 {cx+6} 56 {cx+4} 62Z'
    b+=f'<path d="{fl1}" fill="{gv(.52)}"/><path d="{fl2}" fill="{gv(.72)}"/><path d="{fl3}" fill="{gv(.90)}"/>'
    b+=f'<path d="M{cx-38} 58H{cx+38}C{cx+36} 68 {cx+26} 76 {cx+14} 76H{cx-14}C{cx-26} 76 {cx-36} 68 {cx-38} 58Z" fill="url(#bowlh)"/>'
    b+=f'<path d="M{cx-36} 61H{cx+36}C{cx+34} 68 {cx+26} 74 {cx+14} 74.4H{cx-14}C{cx-26} 74 {cx-34} 68 {cx-36} 61Z" fill="url(#bowl)" opacity=".7"/>'
    b+=f'<rect x="{cx-40}" y="55" width="80" height="6" rx="3" fill="url(#rim)"/>'
    for dx in (-90,90): b+=hrivet(cx+dx,52,3)
    return hsvg('orc-lintel.h.svg',W,88,d,b)

def lintel_e():
    """Flames: three nested tongues (dim edge -> orange body -> hot core), soft edges, hotter at the coals, plus a glow on the bowl rim."""
    cx=308; W=704
    d='<filter id="b1" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation=".9"/></filter><filter id="b2" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="1.6"/></filter>'
    d+=hlg('f1',0,12,0,62,[(0,.30),(.55,.50),(1,.72)])+hlg('f2',0,34,0,62,[(0,.52),(1,.86)])+hlg('f3',0,44,0,62,[(0,.82),(1,1.0)])
    fl1=f'M{cx-26} 62C{cx-34} 48 {cx-22} 40 {cx-20} 28C{cx-14} 36 {cx-12} 40 {cx-10} 46C{cx-8} 34 {cx-10} 24 {cx-4} 12C{cx} 22 {cx+6} 26 {cx+6} 40C{cx+10} 34 {cx+12} 30 {cx+12} 24C{cx+20} 34 {cx+26} 46 {cx+22} 62Z'
    fl2=f'M{cx-12} 62C{cx-18} 52 {cx-8} 46 {cx-6} 36C{cx-2} 44 {cx} 46 {cx+2} 40C{cx+8} 48 {cx+12} 54 {cx+8} 62Z'
    fl3=f'M{cx-5} 62C{cx-8} 56 {cx-2} 52 {cx} 46C{cx+3} 52 {cx+6} 56 {cx+4} 62Z'
    b=f'<path d="{fl1}" fill="url(#f1)" filter="url(#b1)"/><path d="{fl2}" fill="url(#f2)" filter="url(#b1)"/><path d="{fl3}" fill="url(#f3)" filter="url(#b1)"/>'
    b+=f'<ellipse cx="{cx}" cy="60" rx="30" ry="3" fill="{gv(.62)}" filter="url(#b2)"/><path d="M{cx-26} 66H{cx+26}" stroke="{gv(.45)}" stroke-width="1.4" filter="url(#b1)"/>'
    return hsvg('orc-lintel.e.svg',W,88,d,b)

def sill_h():
    """Iron boss with a round rim, crossed tusks as tapering round rods, an ember eye at the centre, tusk frieze."""
    cx=280; W=672
    d=hdome('hrv',.70,1.0)+hdome('bs',.42,.26)+hdome('emb',.55,.80)
    def tusk(x,s):
        sil=f'M{x-s*8} 36C{x-s*10} 22 {x-s*4} 10 {x+s*9} 3C{x+s*3} 12 {x+s*2} 24 {x+s*7} 36Z'
        cid=f'tc{int(x)}_{s}'
        return f'<clipPath id="{cid}"><path d="{sil}"/></clipPath><g clip-path="url(#{cid})">'+tube(f'M{x-s*.6} 37C{x-s*4} 22 {x} 10 {x+s*9} 2',11,.46,1.0,n=10)+'</g>'
    b=''
    for k in range(W//112):
        x=k*112
        b+=tusk(x+30,1)+tusk(x+82,-1)+hrivet(x+56,45,2.4)
    b+=f'<circle cx="{cx}" cy="30" r="25.5" fill="{gv(.60)}"/>'+tube(f'M{cx-23} 30a23 23 0 1 0 46 0a23 23 0 1 0 -46 0',5.5,.58,.94,n=9)
    b+=f'<circle cx="{cx}" cy="30" r="19.6" fill="{gv(.42)}"/><circle cx="{cx}" cy="30" r="18.4" fill="url(#bs)"/>'
    for sx,x in ((1,cx-18),(-1,cx+18)):
        sil=f'M{x} 44C{x+sx*2} 26 {x+sx*12} 14 {x+sx*30} 10C{x+sx*20} 20 {x+sx*22} 32 {x+sx*20} 44Z'
        b+=f'<clipPath id="cs{sx+1}"><path d="{sil}"/></clipPath><g clip-path="url(#cs{sx+1})">'+tube(f'M{x+sx*9} 45C{x+sx*10} 26 {x+sx*18} 17 {x+sx*30} 9',13,.46,1.0,n=10)+'</g>'
    b+=f'<circle cx="{cx}" cy="30" r="4.4" fill="url(#emb)"/>'
    for dx in (-30,30): b+=hrivet(cx+dx,30,2.4)
    return hsvg('orc-sill.h.svg',W,56,d,b)

def sill_e():
    cx=280
    d='<filter id="b1" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation=".7"/></filter><radialGradient id="eg"><stop offset="0" stop-color="#fff"/><stop offset=".5" stop-color="#e0e0e0"/><stop offset="1" stop-color="#6a6a6a"/></radialGradient>'
    b=f'<circle cx="{cx}" cy="30" r="4.2" fill="url(#eg)" filter="url(#b1)"/>'
    return hsvg('orc-sill.e.svg',672,56,d,b)
