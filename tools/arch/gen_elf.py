from common import *
L,M,D='#cfd8d2','#8c9a94','#46514c'; HI='#f0f7f3'; DK='#18211d'; LF='#bfdcc9'; LFD='#5f8a72'
def base_defs():
    d=lg('fv',0,0,0,1,[(0,HI),(.15,L),(.7,M),(1,D)],False)+lg('fh',0,0,1,0,[(0,D),(.25,M),(.5,HI),(.75,M),(1,D)],False)
    d+=shadow('sh',.8,1.4,1.1,.6)
    d+=lg('wall',0,0,0,1,[(0,'#1d2a30'),(1,'#2b3b41')],False)
    d+=lg('wallh',0,0,1,0,[(0,'#162126'),(.25,'#26353b'),(.75,'#26353b'),(1,'#162126')],False)
    d+=f'<g id="lf"><path d="M0 0C-5 -5 -4 -13 0 -19C4 -13 5 -5 0 0Z" fill="{LF}" stroke="{DK}" stroke-width=".6"/><path d="M0 -1V-16" stroke="{LFD}" stroke-width=".8"/></g>'
    return d
def column():
    d=base_defs()+lg('trunk',22,0,50,0,[(0,'#2d3a35'),(.2,'#5b6b64'),(.45,'#aebdb5'),(.6,'#9aaaa2'),(.85,'#53625b'),(1,'#27322e')])
    gf,_=grain('g1',0,64,72,72,6,.5); d+=gf
    b=''
    # cap: branches
    b+='<rect x="0" y="0" width="72" height="64" fill="url(#wallh)"/>'
    def limb(p,w,col='#8ea299'):
        return f'<path d="{p}" fill="none" stroke="#1a2420" stroke-width="{w+2}" stroke-linecap="round"/><path d="{p}" fill="none" stroke="{col}" stroke-width="{w}" stroke-linecap="round"/><path d="{p}" fill="none" stroke="#d6e4dc" stroke-width="{w*.3:.1f}" stroke-linecap="round" opacity=".6" transform="translate(-.6 0)"/>'
    b+='<g filter="url(#sh)">'
    b+=limb('M30 66C28 52 14 46 8 30C5 20 6 10 6 0',7)
    b+=limb('M42 66C44 52 58 46 64 30C67 20 66 10 66 0',7)
    b+=limb('M36 66C36 50 32 38 34 22C35 12 36 6 36 0',7)
    b+=limb('M20 44C14 42 8 40 2 42',3.5)+limb('M52 44C58 42 64 40 70 42',3.5)
    b+=limb('M34 30C28 26 22 24 20 14',3.2)+limb('M38 30C44 26 50 24 52 14',3.2)
    b+='</g>'
    for (x,y,a) in [(6,2,-10),(6,8,-60),(8,14,-40),(3,28,-70),(2,42,-95),(10,34,55),(20,13,-20),(18,18,-65),(36,3,0),(33,8,-40),(39,8,40),(52,13,20),(54,18,65),(66,2,10),(66,8,60),(64,14,40),(69,28,70),(70,42,95),(62,34,-55),(26,24,-80),(46,24,80),(14,40,-30),(58,40,30)]:
        b+=f'<use href="#lf" transform="translate({x} {y}) rotate({a}) scale(.62)"/>'
    # trunk neck
    b+='<path d="M22 64C24 58 30 54 36 54C42 54 48 58 50 64Z" fill="url(#trunk)"/>'
    # shaft tile
    b+='<rect x="0" y="64" width="72" height="72" fill="url(#wallh)"/>'
    b+='<rect x="22" y="64" width="28" height="72" fill="url(#trunk)"/>'
    for x,ph in [(27,1),(32,-1),(38,1),(44,-1)]:
        b+=f'<path d="M{x} 64q{4*ph} 18 0 36q{-4*ph} 18 0 36" fill="none" stroke="#1b2723" stroke-width="1.5" opacity=".75"/>'
        b+=f'<path d="M{x+1.5} 64q{4*ph} 18 0 36q{-4*ph} 18 0 36" fill="none" stroke="#dbe8e1" stroke-width=".7" opacity=".35"/>'
    b+='<path d="M24 64C54 76 52 94 36 100C20 106 20 124 24 136" fill="none" stroke="#1a2420" stroke-width="4.4" stroke-linecap="round"/><path d="M24 64C54 76 52 94 36 100C20 106 20 124 24 136" fill="none" stroke="#6f9680" stroke-width="2.6" stroke-linecap="round"/>'
    for x,y,a in [(46,76,70),(36,100,-90),(22,114,-80),(44,88,100),(26,124,-100)]:
        b+=f'<use href="#lf" transform="translate({x} {y}) rotate({a}) scale(.5)"/>'
    b+='<ellipse cx="41" cy="118" rx="3.6" ry="5.4" fill="#222d29"/><ellipse cx="41" cy="117" rx="2" ry="3.4" fill="#10171? "/>'.replace('#10171? ','#10171a')
    b+='<rect x="0" y="64" width="72" height="72" filter="url(#g1)" opacity=".2"/>'
    # base: roots
    b+='<rect x="0" y="136" width="72" height="48" fill="url(#wallh)"/>'
    b+='<g filter="url(#sh)"><path d="M0 184V170C10 166 18 160 22 150L22 136H50L50 150C54 160 62 166 72 170V184Z" fill="url(#trunk)"/>'
    b+='<path d="M22 150C20 164 10 172 2 178M50 150C52 164 62 172 70 178M36 148V176" fill="none" stroke="#18211d" stroke-width="1.6" opacity=".7"/></g>'
    b+='<path d="M0 184C6 176 14 174 20 178C28 172 44 172 52 178C58 174 66 176 72 184Z" fill="#33423c" stroke="#18211d" stroke-width=".8"/>'
    b+='<path d="M4 180Q10 176 16 180M54 180Q62 175 68 180" fill="none" stroke="#9ec0ab" stroke-width="1.4" opacity=".7"/>'
    return svg('elf-column.svg',72,184,d,b)

def strand_paths(x0,w,ph=0):
    # two interlaced sine strands, period 88
    A=[];B=[]
    n=int(w//88)
    for k in range(n):
        x=x0+k*88
        A.append(f'M{x} 44C{x+22} 22 {x+22} 22 {x+44} 44S{x+66} 66 {x+88} 44')
        B.append(f'M{x} 44C{x+22} 66 {x+22} 66 {x+44} 44S{x+66} 22 {x+88} 44')
    return ''.join(A),''.join(B)
def lintel():
    d=base_defs()+lg('rail',0,0,0,12,[(0,HI),(.3,L),(1,D)],True)+lg('lip',0,72,0,88,[(0,L),(.4,M),(1,D)],True)
    d+=lg('band',0,14,0,72,[(0,'#18242a'),(.5,'#26363c'),(1,'#1b282e')],True)
    d+=rg('med',308,44,34,[(0,'#2c4a63'),(1,'#101c29')])
    d+=rg('mglow',308,44,60,[(0,'#bcd6e8',.35),(1,'#bcd6e8',0)])
    d+='<pattern id="bead" width="11" height="14" patternUnits="userSpaceOnUse" y="74"><circle cx="5.5" cy="5" r="3.8" fill="url(#fv)" stroke="#18211d" stroke-width=".6"/></pattern>'
    d+='<g id="lf2"><path d="M0 0C-6 -4 -6 -12 0 -17C6 -12 6 -4 0 0Z" fill="#a9cdb7" stroke="#10181a" stroke-width=".6"/><path d="M0 -1V-14" stroke="#4d7a63" stroke-width=".7"/></g>'
    gf,_=grain('g2',0,0,704,88,8,.6); d+=gf
    W=704
    b=f'<rect width="{W}" height="88" fill="#12191c"/>'
    b+=f'<rect y="0" width="{W}" height="13" fill="url(#rail)"/><rect y="0" width="{W}" height="2" fill="{HI}"/><rect y="11" width="{W}" height="3" fill="#000" opacity=".5"/>'
    b+=f'<rect y="14" width="{W}" height="58" fill="url(#band)"/><rect y="14" width="{W}" height="6" fill="#000" opacity=".35"/>'
    b+=f'<rect y="72" width="{W}" height="16" fill="url(#lip)"/><rect y="72" width="{W}" height="1.6" fill="{HI}"/><rect y="74" width="{W}" height="14" fill="url(#bead)"/><rect y="86" width="{W}" height="2" fill="#000" opacity=".5"/>'
    A,B=strand_paths(0,W)
    cl=''.join(f'<rect x="{k*88+34}" y="30" width="20" height="28"/>' for k in range(W//88))
    d2=f'<clipPath id="cx">{cl}</clipPath>'
    b=f'<defs>{d2}</defs>'+b
    for p,c in ((A,'#7fa992'),(B,'#aac8b8')):
        b+=f'<path d="{p}" fill="none" stroke="#0b1210" stroke-width="6.4" stroke-linecap="round"/><path d="{p}" fill="none" stroke="{c}" stroke-width="4" stroke-linecap="round"/><path d="{p}" fill="none" stroke="#e6f2eb" stroke-width="1" opacity=".5" transform="translate(0 -1)"/>'
    b+=f'<g clip-path="url(#cx)"><path d="{A}" fill="none" stroke="#0b1210" stroke-width="6.4" stroke-linecap="round"/><path d="{A}" fill="none" stroke="#7fa992" stroke-width="4" stroke-linecap="round"/></g>'
    for k in range(W//88):
        x=k*88
        b+=f'<use href="#lf2" transform="translate({x+22} 28) rotate(-35)"/><use href="#lf2" transform="translate({x+66} 60) rotate(145)"/><use href="#lf2" transform="translate({x+22} 60) rotate(215)" opacity=".8"/><use href="#lf2" transform="translate({x+66} 28) rotate(35)" opacity=".8"/>'
    # medallion
    cx=308
    b+=f'<circle cx="{cx}" cy="44" r="58" fill="url(#mglow)"/>'
    b+=f'<g filter="url(#sh)"><circle cx="{cx}" cy="44" r="39" fill="url(#fh)"/></g><circle cx="{cx}" cy="44" r="35" fill="url(#fv)" stroke="#18211d"/><circle cx="{cx}" cy="44" r="31" fill="url(#med)" stroke="#0b1210" stroke-width="1.5"/>'
    b+=f'<circle cx="{cx}" cy="44" r="39" fill="none" stroke="{HI}" stroke-width=".8" opacity=".6"/>'
    b+=f'<path d="{star(cx,44,27,8,.3)}" fill="#e9f2f7" stroke="#0b1210" stroke-width=".6"/><path d="{star(cx,44,17,8,.3,-67.5)}" fill="#bcd6e8" opacity=".9"/><circle cx="{cx}" cy="44" r="4" fill="#fff"/>'
    b+=f'<path d="M{cx-26} 28A32 32 0 0 0 {cx-26} 60A24 24 0 0 1 {cx-26} 28Z" fill="#d7e6f0" opacity=".9"/>'
    for sx in (-1,1):
        for dx,dy,a in [(44,-26,-60),(48,-8,-100),(44,20,-140)]:
            b+=f'<use href="#lf2" transform="translate({cx+sx*dx} {44-dy}) rotate({sx*a}) scale(.9)"/>' if False else ''
    b+=f'<rect width="{W}" height="88" filter="url(#g2)" opacity=".16"/>'
    return svg('elf-lintel.svg',W,88,d,b)

def scroll(x0):
    # running flourish, period 112
    return (f'<path d="M{x0} 29C{x0+14} 12 {x0+30} 14 {x0+34} 26C{x0+36} 34 {x0+26} 36 {x0+25} 29C{x0+25} 24 {x0+31} 23 {x0+33} 26" fill="none" stroke="#dbe9e1" stroke-width="1.8" stroke-linecap="round"/>'
            f'<path d="M{x0+34} 29C{x0+50} 42 {x0+66} 40 {x0+72} 28C{x0+76} 20 {x0+68} 15 {x0+64} 21C{x0+62} 26 {x0+68} 28 {x0+70} 25" fill="none" stroke="#dbe9e1" stroke-width="1.8" stroke-linecap="round"/>'
            f'<path d="M{x0+72} 29C{x0+88} 16 {x0+104} 18 {x0+112} 29" fill="none" stroke="#dbe9e1" stroke-width="1.8" stroke-linecap="round"/>'
            f'<use href="#lf3" transform="translate({x0+54} 40) rotate(160)"/><use href="#lf3" transform="translate({x0+16} 24) rotate(-20)"/><use href="#lf3" transform="translate({x0+90} 24) rotate(10)"/>')
def sill():
    d=base_defs()+lg('rim',0,0,0,15,[(0,HI),(.2,L),(.6,M),(1,D)],True)+lg('inner',0,15,0,44,[(0,'#0f181d'),(1,'#273940')],True)
    d+=lg('foot',0,44,0,56,[(0,L),(.5,M),(1,'#2c3834')],True)
    d+='<g id="lf3"><path d="M0 0C-4 -3 -4 -9 0 -12C4 -9 4 -3 0 0Z" fill="#a9cdb7" stroke="#10181a" stroke-width=".5"/></g>'
    d+=rg('sg',280,28,60,[(0,'#bcd6e8',.4),(1,'#bcd6e8',0)])
    gf,_=grain('g3',0,0,672,56,5,.6); d+=gf
    W=672
    b=f'<rect width="{W}" height="56" fill="#12191c"/>'
    b+=f'<g filter="url(#sh)"><rect y="0" width="{W}" height="15" rx="3" fill="url(#rim)"/></g><rect y="1" width="{W}" height="2" fill="{HI}"/><rect y="12" width="{W}" height="3" fill="#000" opacity=".4"/>'
    b+=f'<rect y="15" width="{W}" height="29" fill="url(#inner)"/><rect y="15" width="{W}" height="6" fill="#000" opacity=".4"/>'
    b+=f'<rect y="44" width="{W}" height="12" fill="url(#foot)"/><rect y="44" width="{W}" height="1.4" fill="{HI}"/>'
    for k in range(6):
        b+=f'<path d="M{k*112} 50q14 -5 28 0t28 0t28 0t28 0" fill="none" stroke="#e4eee9" stroke-width="1" opacity=".5"/>'
    b+=f'<path d="M0 53h{W}" stroke="#000" stroke-width="3" opacity=".4"/>'
    for k in range(6): b+=scroll(k*112)
    # centre cartouche (emblem region 0..560, centre 280)
    cx=280
    b+=f'<ellipse cx="{cx}" cy="29" rx="100" ry="26" fill="url(#sg)"/>'
    b+=f'<g filter="url(#sh)"><ellipse cx="{cx}" cy="29" rx="72" ry="24" fill="url(#fh)"/></g><ellipse cx="{cx}" cy="29" rx="68" ry="20" fill="url(#inner)" stroke="#0b1210"/><ellipse cx="{cx}" cy="29" rx="64" ry="17" fill="none" stroke="#e4eee9" stroke-width=".8" opacity=".5"/>'
    b+=f'<path d="{star(cx,29,13,8,.3)}" fill="#e9f2f7"/><circle cx="{cx}" cy="29" r="2.4" fill="#fff"/>'
    for sx in (-1,1):
        b+=f'<path d="M{cx+sx*18} 29C{cx+sx*30} 20 {cx+sx*44} 20 {cx+sx*58} 29C{cx+sx*44} 38 {cx+sx*30} 38 {cx+sx*18} 29Z" fill="none" stroke="#dbe9e1" stroke-width="1.4"/>'
        for k in range(3):
            b+=f'<use href="#lf3" transform="translate({cx+sx*(30+k*10)} {24-k*1}) rotate({sx*70})"/>'
    b+=f'<rect width="{W}" height="56" filter="url(#g3)" opacity=".15"/>'
    return svg('elf-sill.svg',W,56,d,b)

def corner():
    d=base_defs()+rg('mb',50,50,44,[(0,'#2f4a60'),(.7,'#142330'),(1,'#0a1219')])
    d+=lg('wg',0,0,1,1,[(0,'#ffffff'),(1,'#a9bcb4')],False)
    d+=lg('pl',0,0,100,100,[(0,'#dde8e2'),(.5,M),(1,'#3d4a45')])
    d+='<path id="fe" d="M0 0C-3 -8 -2 -24 0 -36C3 -24 4 -8 0 0Z"/>'
    b='<g filter="url(#sh)"><path d="M2 2H88C95 2 98 6 98 12V98H12C6 98 2 94 2 88Z" fill="url(#pl)" stroke="#18211d" stroke-width="1.2"/></g>'
    b+='<path d="M6 6H88C92 6 94 8 94 12V94H12C8 94 6 92 6 88Z" fill="none" stroke="#f0f7f3" stroke-width="1" opacity=".5"/>'
    b+='<circle cx="50" cy="50" r="43" fill="#152331" stroke="#e4eee9" stroke-width="2.5"/><circle cx="50" cy="50" r="40" fill="url(#mb)" stroke="#06090c" stroke-width="1.5"/>'
    b+='<path d="M16 24L18 21L20 24L23 25L20 26L18 29L16 26L13 25ZM80 14L81 12L82 14L84 15L82 16L81 18L80 16L78 15ZM84 40L85 38L86 40L88 41L86 42L85 44L84 42L82 41Z" fill="#cfe2ee"/>'
    # ripples
    b+='<g fill="none" stroke="#bcd6e8" stroke-linecap="round"><ellipse cx="50" cy="84" rx="30" ry="4" stroke-width="1.3" opacity=".8"/><ellipse cx="50" cy="86" rx="38" ry="5" stroke-width=".9" opacity=".5"/></g>'
    # wings
    b+='<g filter="url(#sh)">'
    for i,(a,sc) in enumerate([(-92,1.0),(-76,1.28),(-58,1.5),(-40,1.55),(-22,1.45),(-6,1.2)]):
        b+=f'<use href="#fe" transform="translate(44 68) rotate({a}) scale(2.1 {sc})" fill="#aebfb7" stroke="#18211d" stroke-width=".6"/>'
    for i,(a,sc) in enumerate([(-84,.7),(-66,.95),(-48,1.05),(-30,1.0),(-12,.8)]):
        b+=f'<use href="#fe" transform="translate(44 68) rotate({a}) scale(2.0 {sc})" fill="#f0f7f3" stroke="#18211d" stroke-width=".5"/>'
    b+='</g>'
    # body
    b+='<g filter="url(#sh)"><path d="M20 68C22 66 24 64 28 64C36 58 56 58 68 64C78 68 80 76 70 80C56 86 36 86 26 78C20 74 18 70 20 68Z" fill="url(#wg)" stroke="#18211d" stroke-width="1.1"/></g>'
    b+='<path d="M32 70C40 66 56 66 66 70M30 75C42 72 56 72 68 75" fill="none" stroke="#8c9a94" stroke-width="1.1"/>'
    # neck
    nk='M64 66C78 60 80 46 68 40C58 35 62 24 70 22'
    b+=f'<path d="{nk}" fill="none" stroke="#18211d" stroke-width="10.5" stroke-linecap="round"/><path d="{nk}" fill="none" stroke="#f0f7f3" stroke-width="8" stroke-linecap="round"/><path d="{nk}" fill="none" stroke="#9fb0a8" stroke-width="2" stroke-linecap="round" transform="translate(2.5 1)" opacity=".7"/>'
    b+='<path d="M69 18C74 15 80 18 79 23L84 25L78 27C73 29 68 25 69 18Z" fill="#f0f7f3" stroke="#18211d" stroke-width="1"/><path d="M79 23L90 26L78 28Z" fill="#6c4a3a" stroke="#18211d" stroke-width=".8"/><circle cx="76" cy="21.5" r="1.2" fill="#10181a"/>'
    return svg('elf-corner.svg',100,100,d,b)

# =============================================================== authored relief (height pass)
def corner_h():
    """Swan on the moonlit water: round neck tube, two stepped rows of wing feathers, body cylinder, round head."""
    d=hdome('dish',.34,.12,.5,.5,r=.5)+hcyl('body',0,58,0,86,.40,.80)+hdome('hd',.60,.96)
    d+=hcyl('fe1',0,0,1,0,.30,.50,False,n=8,p=.6)+hcyl('fe2',0,0,1,0,.46,.68,False,n=8,p=.6)
    d+='<path id="fh1" d="M0 0C-3 -8 -2 -24 0 -36C3 -24 4 -8 0 0Z"/>'
    b=hrect(0,0,100,100,.30)
    b+=bevel('M2 2H88C95 2 98 6 98 12V98H12C6 98 2 94 2 88Z',.28,.62,4,6)
    b+=flat('M6 6H88C92 6 94 8 94 12V94H12C8 94 6 92 6 88Z',.60)
    b+=f'<circle cx="50" cy="50" r="43" fill="{gv(.70)}"/><circle cx="50" cy="50" r="41.4" fill="{gv(.76)}"/><circle cx="50" cy="50" r="40" fill="{gv(.36)}"/><circle cx="50" cy="50" r="39" fill="url(#dish)"/>'
    b+=f'<ellipse cx="50" cy="84" rx="30" ry="4" fill="none" stroke="{gv(.40)}" stroke-width="1.4"/><ellipse cx="50" cy="86" rx="38" ry="5" fill="none" stroke="{gv(.36)}" stroke-width="1"/>'
    # wings: outer row then inner row on top, every feather round in section
    for a,sc in [(-92,1.0),(-76,1.28),(-58,1.5),(-40,1.55),(-22,1.45),(-6,1.2)]:
        b+=f'<use href="#fh1" transform="translate(44 68) rotate({a}) scale(2.1 {sc})" fill="url(#fe1)"/>'
    for a,sc in [(-84,.7),(-66,.95),(-48,1.05),(-30,1.0),(-12,.8)]:
        b+=f'<use href="#fh1" transform="translate(44 68) rotate({a}) scale(2.0 {sc})" fill="url(#fe2)"/>'
    # body and feather grooves
    b+='<path d="M20 68C22 66 24 64 28 64C36 58 56 58 68 64C78 68 80 76 70 80C56 86 36 86 26 78C20 74 18 70 20 68Z" fill="url(#body)"/>'
    b+=f'<path d="M32 70C40 66 56 66 66 70M30 75C42 72 56 72 68 75" fill="none" stroke="{gv(.50)}" stroke-width="1.1"/>'
    # neck: a long round tube
    nk='M64 66C78 60 80 46 68 40C58 35 62 24 70 22'
    b+=tube(nk,10.5,.40,.94,n=14)
    b+='<path d="M69 18C74 15 80 18 79 23L84 25L78 27C73 29 68 25 69 18Z" fill="url(#hd)"/>'
    b+=flat('M79 23L90 26L78 28Z',.70)+tube('M79 25.2L88.5 26.3',1.4,.72,.84)+f'<circle cx="76" cy="21.5" r="1.2" fill="{gv(.50)}"/>'
    return hsvg('elf-corner.h.svg',100,100,d,b)

def capital_h():
    """Branching capital: three round limbs and four boughs, leaves as little domes, a swelling trunk neck."""
    d=hcyl('trkn',22,0,50,0,.40,.78)+hdome('lf',.50,.80)
    d+='<path id="lfh" d="M0 0C-5 -5 -4 -13 0 -19C4 -13 5 -5 0 0Z"/>'
    b=hrect(0,0,72,64,.10)
    for p,w in (('M30 66C28 52 14 46 8 30C5 20 6 10 6 0',7),('M42 66C44 52 58 46 64 30C67 20 66 10 66 0',7),('M36 66C36 50 32 38 34 22C35 12 36 6 36 0',7)):
        b+=tube(p,w,.30,.74,n=10)
    for p,w in (('M20 44C14 42 8 40 2 42',3.5),('M52 44C58 42 64 40 70 42',3.5),('M34 30C28 26 22 24 20 14',3.2),('M38 30C44 26 50 24 52 14',3.2)):
        b+=tube(p,w,.34,.72,n=8)
    for (x,y,a) in [(6,2,-10),(6,8,-60),(8,14,-40),(3,28,-70),(2,42,-95),(10,34,55),(20,13,-20),(18,18,-65),(36,3,0),(33,8,-40),(39,8,40),(52,13,20),(54,18,65),(66,2,10),(66,8,60),(64,14,40),(69,28,70),(70,42,95),(62,34,-55),(26,24,-80),(46,24,80),(14,40,-30),(58,40,30)]:
        b+=f'<g transform="translate({x} {y}) rotate({a}) scale(.62)"><path d="M0 0C-5 -5 -4 -13 0 -19C4 -13 5 -5 0 0Z" fill="url(#lf)"/><path d="M0 -1V-16" stroke="{gv(.88)}" stroke-width="1.1"/></g>'
    b+='<path d="M22 64C24 58 30 54 36 54C42 54 48 58 50 64Z" fill="url(#trkn)"/>'
    return hsvg('elf-capital.h.svg',72,64,d,b)

def lintel_h():
    """Vine stems as round tubes, interlaced; leaves with ribs; the medallion as a dished mirror in a moulded ring."""
    cx=308
    d=hdome('mir',.42,.20,.5,.5)+hdome('lf',.50,.78)+hdome('ctr',.9,1)
    W=704
    b=hrect(0,14,W,58,.26)
    A,B=strand_paths(0,W)
    b+=tube(A,6.8,.34,.70,n=10)+tube(B,6.8,.38,.76,n=10)
    cl=''.join(f'<rect x="{k*88+34}" y="30" width="20" height="28"/>' for k in range(W//88))
    d+=f'<clipPath id="cx">{cl}</clipPath>'
    b+=f'<g clip-path="url(#cx)">{tube(A,6.8,.34,.70,n=10)}</g>'
    for k in range(W//88):
        x=k*88
        for tr in (f'translate({x+22} 28) rotate(-35)',f'translate({x+66} 60) rotate(145)',f'translate({x+22} 60) rotate(215)',f'translate({x+66} 28) rotate(35)'):
            b+=f'<g transform="{tr}"><path d="M0 0C-6 -4 -6 -12 0 -17C6 -12 6 -4 0 0Z" fill="url(#lf)"/><path d="M0 -1V-14" stroke="{gv(.86)}" stroke-width="1"/></g>'
    # medallion: moulded ring, dished field, star facets
    b+=f'<circle cx="{cx}" cy="44" r="39.5" fill="{gv(.66)}"/>'
    b+=tube(f'M{cx-37} 44a37 37 0 1 0 74 0a37 37 0 1 0 -74 0',5,.62,.92,n=9)
    b+=f'<circle cx="{cx}" cy="44" r="31.5" fill="{gv(.50)}"/><circle cx="{cx}" cy="44" r="30.5" fill="url(#mir)"/>'
    b+=star_facets(cx,44,27,8,.3,lo=.52,hi=.82)+star_facets(cx,44,17,8,.3,-67.5,lo=.78,hi=.99)+f'<circle cx="{cx}" cy="44" r="4" fill="url(#ctr)"/>'
    b+=flat(f'M{cx-26} 28A32 32 0 0 0 {cx-26} 60A24 24 0 0 1 {cx-26} 28Z',.64)
    return hsvg('elf-lintel.h.svg',W,88,d,b)

def sill_h():
    """Scrolls as round stems with leaves; a cartouche with a faceted star; almond petals."""
    cx=280; W=672
    d=hdome('lf',.46,.74)+hdome('ctr',.9,1.0)+hcyl('car',0,5,0,53,.54,.80,n=6,p=.9)
    b=hrect(0,15,W,29,.20)
    for k in range(6):
        x0=k*112
        for p in (f'M{x0} 29C{x0+14} 12 {x0+30} 14 {x0+34} 26C{x0+36} 34 {x0+26} 36 {x0+25} 29C{x0+25} 24 {x0+31} 23 {x0+33} 26',
                  f'M{x0+34} 29C{x0+50} 42 {x0+66} 40 {x0+72} 28C{x0+76} 20 {x0+68} 15 {x0+64} 21C{x0+62} 26 {x0+68} 28 {x0+70} 25',
                  f'M{x0+72} 29C{x0+88} 16 {x0+104} 18 {x0+112} 29'):
            b+=tube(p,2.8,.34,.64,n=6)
        for tr in (f'translate({x0+54} 40) rotate(160)',f'translate({x0+16} 24) rotate(-20)',f'translate({x0+90} 24) rotate(10)'):
            b+=f'<g transform="{tr}"><path d="M0 0C-4 -3 -4 -9 0 -12C4 -9 4 -3 0 0Z" fill="url(#lf)"/></g>'
    b+=f'<ellipse cx="{cx}" cy="29" rx="72" ry="24" fill="url(#car)"/><ellipse cx="{cx}" cy="29" rx="68" ry="20" fill="{gv(.22)}"/><ellipse cx="{cx}" cy="29" rx="64" ry="17" fill="none" stroke="{gv(.34)}" stroke-width="1"/>'
    b+=star_facets(cx,29,13,8,.3,lo=.66,hi=.96)+f'<circle cx="{cx}" cy="29" r="2.4" fill="url(#ctr)"/>'
    for sx in (-1,1):
        b+=tube(f'M{cx+sx*18} 29C{cx+sx*30} 20 {cx+sx*44} 20 {cx+sx*58} 29C{cx+sx*44} 38 {cx+sx*30} 38 {cx+sx*18} 29Z',2.2,.34,.62,n=6)
        for k in range(3):
            b+=f'<g transform="translate({cx+sx*(30+k*10)} {24-k}) rotate({sx*70})"><path d="M0 0C-4 -3 -4 -9 0 -12C4 -9 4 -3 0 0Z" fill="url(#lf)"/></g>'
    return hsvg('elf-sill.h.svg',W,56,d,b)
