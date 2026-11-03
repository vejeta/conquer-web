from common import *
L,M,D='#8a8176','#5a534b','#2b2724'; HI='#b8ae9f'; DK='#0f0d0b'
B,BH,BD='#b0803a','#e8c27a','#5e3f14'
def base_defs():
    d=lg('fv',0,0,0,1,[(0,HI),(.12,L),(.6,M),(1,D)],False)+lg('fh',0,0,1,0,[(0,D),(.3,M),(.5,L),(.7,M),(1,D)],False)
    d+=lg('br',0,0,0,1,[(0,BH),(.4,B),(1,BD)],False)+lg('brh',0,0,1,0,[(0,BD),(.4,BH),(1,BD)],False)
    d+=shadow('sh',1,1.6,1.4,.7)+lg('wall',0,0,0,1,[(0,'#26221e'),(1,'#14110f')],False)
    d+=rg('stud',0,0,1,[(0,BH),(.6,B),(1,BD)])
    return d
def stud(x,y,r=3):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#br)" stroke="{DK}" stroke-width=".8"/><circle cx="{x-r*.3:.1f}" cy="{y-r*.3:.1f}" r="{r*.3:.1f}" fill="{BH}"/>'
def column():
    d=base_defs()+lg('pf',12,0,60,0,[(0,'#a39a8d'),(.145,'#8a8176'),(.145,'#6d655b'),(.5,'#7a7166'),(.855,'#5a534b'),(.855,'#2f2a26'),(1,'#201c19')])
    gf,_=grain('g1',0,64,72,72,2,.6); d+=gf
    b=''
    # cap: anvil
    b+='<rect width="72" height="64" fill="url(#wall)"/>'
    b+='<g filter="url(#sh)"><path d="M0 24L16 14H72V28H54V34C54 40 50 44 50 48V52H66V64H6V52H22V48C22 44 18 40 18 34V28H6Z" fill="url(#fv)" stroke="#0f0d0b" stroke-width="1.2"/></g>'
    b+=f'<path d="M16 14H72V17H17Z" fill="{HI}" opacity=".9"/><path d="M0 24L16 14" stroke="{HI}" stroke-width="1.5"/>'
    b+=f'<path d="M20 30H52M24 40H48" stroke="#0f0d0b" stroke-width="1" opacity=".5"/><path d="M6 52H66" stroke="{HI}" stroke-width="1.2" opacity=".5"/>'
    b+=f'<g filter="url(#sh)"><rect x="12" y="6.5" width="34" height="5" rx="1.5" fill="#6a4a2a" stroke="{DK}" stroke-width=".8"/><path d="M42 0H60L62 3V12H40V3Z" fill="url(#br)" stroke="{DK}" stroke-width="1"/></g><path d="M43 1.5H59" stroke="{BH}" stroke-width="1.2"/>'
    b+=stud(10,58,2)+stud(62,58,2)
    # pillar tile
    b+='<rect y="64" width="72" height="72" fill="url(#wall)"/>'
    b+='<rect x="4" y="64" width="64" height="72" fill="url(#fh)" opacity="0"/>'
    b+='<g><rect x="4" y="64" width="8" height="72" fill="#a39a8d"/><rect x="12" y="64" width="48" height="72" fill="#6d655b"/><rect x="60" y="64" width="8" height="72" fill="#2f2a26"/>'
    b+='<path d="M12 64H60V136H12Z" fill="url(#pf)" opacity="0"/></g>'
    b+='<rect x="12" y="64" width="48" height="72" fill="#fff" opacity=".04"/><rect x="12" y="64" width="2" height="72" fill="#000" opacity=".3"/><rect x="58" y="64" width="2" height="72" fill="#000" opacity=".25"/>'
    # chevrons (bronze inlay)
    for y in (70,79,88):
        b+=f'<path d="M17 {y}L36 {y+10}L55 {y}" fill="none" stroke="{DK}" stroke-width="5" stroke-linejoin="miter"/><path d="M17 {y}L36 {y+10}L55 {y}" fill="none" stroke="url(#br)" stroke-width="3" stroke-linejoin="miter"/><path d="M17 {y-1}L36 {y+9}L55 {y-1}" fill="none" stroke="{BH}" stroke-width=".8" opacity=".8"/>'
    # knot diamond
    cx,cy=36,118
    b+=f'<path d="M{cx} {cy-15}L{cx+15} {cy}L{cx} {cy+15}L{cx-15} {cy}Z" fill="#1c1916" stroke="{DK}" stroke-width="5"/>'
    for r,w in ((15,3),(9,2.4)):
        b+=f'<path d="M{cx} {cy-r}L{cx+r} {cy}L{cx} {cy+r}L{cx-r} {cy}Z" fill="none" stroke="url(#br)" stroke-width="{w}"/>'
    b+=f'<path d="M{cx-15} {cy}H{cx+15}M{cx} {cy-15}V{cy+15}" stroke="{B}" stroke-width="2.2"/><path d="M{cx-4} {cy}H{cx+4}" stroke="#1c1916" stroke-width="3"/><circle cx="{cx}" cy="{cy}" r="2.2" fill="{BH}"/>'
    b+=f'<rect x="4" y="64" width="64" height="72" filter="url(#g1)" opacity=".4"/>'
    # base
    b+='<rect y="136" width="72" height="48" fill="url(#wall)"/>'
    b+=f'<path d="M4 136H68V146L72 150V184H0V150L4 146Z" fill="url(#fv)"/>'
    b+='<path d="M4 136H68V146H4Z" fill="url(#pf)" opacity="0"/>'
    b+=f'<rect x="4" y="136" width="8" height="10" fill="#a39a8d"/><rect x="60" y="136" width="8" height="10" fill="#2f2a26"/><rect x="12" y="136" width="48" height="10" fill="#6d655b"/>'
    b+=f'<path d="M4 146L0 152V184H72V152L68 146Z" fill="url(#fv)" stroke="#0f0d0b" stroke-width="1"/><path d="M0 152H72" stroke="{HI}" stroke-width="1.5" opacity=".8"/><path d="M4 146H68" stroke="#000" stroke-width="3" opacity=".4"/>'
    b+=f'<rect x="8" y="164" width="56" height="3" fill="url(#br)"/>'+stud(10,174,3)+stud(62,174,3)+stud(36,174,3)+stud(10,158,2.2)+stud(62,158,2.2)
    b+=f'<rect y="136" width="72" height="48" filter="url(#g1)" opacity=".0"/>'
    return svg('dwarf-column.svg',72,184,d,b)

def lintel():
    d=base_defs()+lg('beam',0,0,0,60,[(0,HI),(.1,L),(.16,'#6d655b'),(.7,'#5a534b'),(.9,'#3d3731'),(1,'#2b2724')],True)
    d+=lg('slot',0,60,0,84,[(0,'#000'),(1,'#16120f')],True)
    d+=rg('plq',308,34,80,[(0,'#2d2a26'),(1,'#161310')])
    gf,_=grain('g2',0,0,704,88,4,.6); d+=gf
    W=704
    b=f'<rect width="{W}" height="88" fill="#14110f"/>'
    b+=f'<rect width="{W}" height="59" fill="url(#beam)"/><rect width="{W}" height="2.2" fill="{HI}"/><rect y="12" width="{W}" height="1.4" fill="#000" opacity=".45"/><rect y="13.4" width="{W}" height="1" fill="{HI}" opacity=".25"/>'
    # zigzag inlay (period 22)
    d2='<pattern id="zz" width="22" height="9" patternUnits="userSpaceOnUse" y="46"><path d="M0 8L11 1L22 8" fill="none" stroke="#0f0d0b" stroke-width="4.4"/><path d="M0 8L11 1L22 8" fill="none" stroke="'+B+'" stroke-width="2.4"/><path d="M0 7L11 0L22 7" fill="none" stroke="'+BH+'" stroke-width=".7"/></pattern>'
    b=f'<defs>{d2}</defs>'+b
    b+=f'<rect y="46" width="{W}" height="9" fill="url(#zz)"/>'
    # rails and slot
    b+=f'<rect y="58" width="{W}" height="4" fill="url(#br)"/><rect y="58" width="{W}" height="1" fill="{BH}"/><rect y="62" width="{W}" height="22" fill="url(#slot)"/><rect y="62" width="{W}" height="3" fill="#000" opacity=".8"/>'
    b+=f'<rect y="82" width="{W}" height="3" fill="url(#br)"/><rect y="85" width="{W}" height="3" fill="#0f0d0b"/><rect y="84" width="{W}" height="1" fill="{BH}" opacity=".7"/>'
    # nails along (tile has one per 88)
    for k in range(W//88):
        b+=stud(k*88+44,28,5)+f'<path d="M{k*88+37} 21H{k*88+51}V35H{k*88+37}Z" fill="none" stroke="{DK}" stroke-width="1.2" opacity=".6"/>'
    # emblem plaque
    cx=308
    b+=f'<g filter="url(#sh)"><path d="M{cx-104} 3H{cx+104}L{cx+118} 14V46L{cx+104} 58H{cx-104}L{cx-118} 46V14Z" fill="url(#fv)" stroke="{DK}" stroke-width="1.4"/></g>'
    b+=f'<path d="M{cx-98} 8H{cx+98}L{cx+110} 17V44L{cx+98} 53H{cx-98}L{cx-110} 44V17Z" fill="url(#plq)" stroke="{BD}" stroke-width="2"/><path d="M{cx-98} 8H{cx+98}L{cx+110} 17" fill="none" stroke="{B}" stroke-width="1.2"/>'
    # seven stars on arc
    for i in range(7):
        x=cx+(i-3)*27; y=14+((i-3)**2)*2.3
        r=7.5 if i==3 else 6.2
        b+=f'<path d="{star(x,y,r,8,.42)}" fill="url(#br)" stroke="{DK}" stroke-width=".7"/><path d="{star(x,y-.4,r*.55,8,.5)}" fill="{BH}" opacity=".7"/>'
    b+=f'<g filter="url(#sh)"><path d="M{cx-4} 36H{cx+4}V55H{cx+3}V57H{cx-3}V55H{cx-4}Z" fill="#7b5a34" stroke="{DK}" stroke-width=".9"/>'
    b+=f'<path d="M{cx-22} 26H{cx+22}L{cx+26} 29V38L{cx+22} 41H{cx-22}L{cx-26} 38V29Z" fill="url(#fv)" stroke="{DK}" stroke-width="1.2"/><path d="M{cx-20} 28H{cx+20}" stroke="{HI}" stroke-width="1.4"/><rect x="{cx-27}" y="26" width="5" height="15" fill="url(#br)" stroke="{DK}" stroke-width=".6"/><rect x="{cx+22}" y="26" width="5" height="15" fill="url(#br)" stroke="{DK}" stroke-width=".6"/></g>'
    b+=f'<path d="M{cx-4} 45H{cx+4}M{cx-4} 50H{cx+4}" stroke="{B}" stroke-width="1.6"/>'
    b+=f'<rect width="{W}" height="88" filter="url(#g2)" opacity=".28"/>'
    return svg('dwarf-lintel.svg',W,88,d,b)

def sill():
    d=base_defs()+lg('top',0,0,0,56,[(0,HI),(.06,L),(.2,'#6d655b'),(.85,'#4a443d'),(1,'#1c1916')],True)
    gf,_=grain('g3',0,0,672,56,6,.6); d+=gf
    d+='<pattern id="kn" width="56" height="26" patternUnits="userSpaceOnUse" x="0" y="14"><path d="M0 13L14 1L28 13L14 25Z" fill="none" stroke="#0f0d0b" stroke-width="4.2"/><path d="M0 13L14 1L28 13L14 25Z" fill="none" stroke="'+B+'" stroke-width="2.2"/><path d="M28 13L42 1L56 13L42 25Z" fill="none" stroke="#0f0d0b" stroke-width="4.2"/><path d="M28 13L42 1L56 13L42 25Z" fill="none" stroke="'+B+'" stroke-width="2.2"/><path d="M0 13L14 1L28 13L42 1L56 13" fill="none" stroke="'+BH+'" stroke-width=".6" opacity=".7"/></pattern>'
    W=672
    b=f'<rect width="{W}" height="56" fill="url(#top)"/><rect width="{W}" height="2.2" fill="{HI}"/>'
    b+=f'<rect y="6" width="{W}" height="2" fill="#000" opacity=".5"/>'
    b+=f'<rect y="10" width="{W}" height="34" fill="#171411"/><rect y="10" width="{W}" height="5" fill="#000" opacity=".6"/>'
    b+=f'<rect y="14" width="{W}" height="26" fill="url(#kn)"/>'
    b+=f'<rect y="8" width="{W}" height="2.5" fill="url(#br)"/><rect y="43" width="{W}" height="2.5" fill="url(#br)"/>'
    b+=f'<rect y="47" width="{W}" height="2" fill="#000" opacity=".5"/>'
    for k in range(W//56): b+=stud(k*56+28,51,1.8) if False else ''
    cx=280
    b+=f'<g filter="url(#sh)"><path d="M{cx-60} 6H{cx+60}L{cx+70} 28L{cx+60} 50H{cx-60}L{cx-70} 28Z" fill="url(#fv)" stroke="{DK}" stroke-width="1.3"/></g><path d="M{cx-52} 11H{cx+52}L{cx+60} 28L{cx+52} 45H{cx-52}L{cx-60} 28Z" fill="#161310" stroke="{BD}" stroke-width="2"/>'
    # anvil on plaque
    b+=f'<path d="M{cx-26} 22L{cx-12} 17H{cx+24}V25H{cx+14}V30C{cx+14} 33 {cx+10} 34 {cx+10} 37V39H{cx+18}V43H{cx-18}V39H{cx-10}V37C{cx-10} 34 {cx-14} 33 {cx-14} 30V25H{cx-20}Z" fill="url(#br)" stroke="{DK}" stroke-width="1"/>'
    for dx in (-52,52): b+=stud(cx+dx*1.0+(-1 if dx<0 else 1)*0,28,2.2) if False else ''
    b+=stud(cx-46,28,3)+stud(cx+46,28,3)
    b+=f'<rect width="{W}" height="56" filter="url(#g3)" opacity=".3"/>'
    return svg('dwarf-sill.svg',W,56,d,b)

def corner():
    # axe-head, top corners
    d=base_defs()+lg('wood',0,0,1,0,[(0,'#3b2814'),(.5,'#7d5a34'),(1,'#33220f')],False)
    d+=lg('steel',0,0,0,1,[(0,'#d5d2cc'),(.5,'#8d8a88'),(1,'#4b4846')],False)
    d+=lg('pl',0,0,100,100,[(0,HI),(.4,M),(1,'#1c1916')])
    b='<g filter="url(#sh)"><path d="M2 2H90L98 10V98H12L2 88Z" fill="url(#pl)" stroke="#0f0d0b" stroke-width="1.3"/></g><path d="M7 7H88L93 12V93H14L7 86Z" fill="none" stroke="'+HI+'" stroke-width="1" opacity=".5"/>'
    b+=f'<path d="M12 12H86V86H12Z" fill="#14110f" stroke="#0a0908" stroke-width="2"/><path d="M12 12H86V86H12Z" fill="none" stroke="{B}" stroke-width="1.2" opacity=".7" transform="translate(1.5 1.5) scale(.96)"/>'
    b+='<g filter="url(#sh)">'
    b+=f'<path d="M33 88V12H41V88Z" fill="url(#wood)" stroke="{DK}" stroke-width="1"/>'
    b+=f'<path d="M24 36H42L66 22C84 36 86 60 66 78L42 64H24Z" fill="url(#steel)" stroke="{DK}" stroke-width="1.4"/>'
    b+=f'<path d="M66 22C86 38 86 62 66 78" fill="none" stroke="#f2efe8" stroke-width="2.4"/>'
    b+=f'<path d="M50 38C62 34 70 40 72 50C70 60 62 66 50 62Z" fill="#403d3b" opacity=".75"/>'
    b+=f'<path d="M24 36H42V64H24Z" fill="url(#br)" stroke="{DK}" stroke-width="1"/>'
    b+='</g>'
    b+=stud(30,41,2.4)+stud(30,59,2.4)+f'<rect x="31" y="20" width="12" height="3.4" fill="url(#br)" stroke="{DK}" stroke-width=".7"/><rect x="31" y="75" width="12" height="3.4" fill="url(#br)" stroke="{DK}" stroke-width=".7"/>'
    return svg('dwarf-corner.svg',100,100,d,b)

def corner_b():
    # bearded dwarf guardian statue in an arched niche
    d=base_defs()+lg('pl',0,0,100,100,[(0,HI),(.4,M),(1,'#1c1916')])
    d+=lg('beard',0,0,1,0,[(0,'#4b453d'),(.35,'#8a8176'),(.5,'#a39a8d'),(.65,'#8a8176'),(1,'#3d3831')],False)
    d+=lg('helm',0,0,1,0,[(0,'#2a2f33'),(.35,'#7c858c'),(.5,'#b4bcc2'),(.7,'#6a737a'),(1,'#22272a')],False)
    d+=lg('niche',0,10,0,92,[(0,'#0e0c0a'),(1,'#25201b')],True)
    b='<g filter="url(#sh)"><path d="M12 2H98V88L88 98H2V12Z" fill="url(#pl)" stroke="#0f0d0b" stroke-width="1.3"/></g><path d="M16 7H93V86L86 93H7V16Z" fill="none" stroke="'+HI+'" stroke-width="1" opacity=".5"/>'
    b+=f'<path d="M12 90V40C12 22 28 10 50 10C72 10 86 22 86 40V90Z" fill="url(#niche)" stroke="#0a0908" stroke-width="2.4"/><path d="M12 90V40C12 22 28 10 50 10C72 10 86 22 86 40" fill="none" stroke="{B}" stroke-width="1.4" opacity=".8" transform="translate(0 -1)"/>'
    b+='<g filter="url(#sh)">'
    # shoulders / pauldrons
    b+=f'<path d="M14 90V78C14 68 24 64 38 62H60C74 64 84 68 84 78V90Z" fill="url(#fv)" stroke="{DK}" stroke-width="1.1"/>'
    b+=f'<path d="M14 80C14 68 24 66 30 68L30 80ZM84 80C84 68 74 66 68 68L68 80Z" fill="url(#br)" stroke="{DK}" stroke-width="1"/>'
    # beard
    b+=f'<path d="M31 50C27 64 30 80 49 92C68 80 71 64 67 50C58 58 40 58 31 50Z" fill="url(#beard)" stroke="{DK}" stroke-width="1.1"/>'
    b+=f'<path d="M44 64L46 86M49 62V90M54 64L52 86" stroke="{DK}" stroke-width="1.2" opacity=".8"/><path d="M40 70L46 74L40 78M58 70L52 74L58 78" fill="none" stroke="{DK}" stroke-width=".9" opacity=".7"/>'
    b+=f'<rect x="38" y="72" width="22" height="4" rx="1.5" fill="url(#br)" stroke="{DK}" stroke-width=".8"/>'
    # face
    b+=f'<path d="M36 44H62V54C60 58 56 60 49 60C42 60 38 58 36 54Z" fill="#9a9084" stroke="{DK}" stroke-width="1"/>'
    b+=f'<path d="M38 49H46M52 49H60" stroke="#0f0d0b" stroke-width="2.4"/><path d="M47 47L45 56L49 58L53 56L51 47" fill="#7a7166" opacity=".8"/>'
    # moustache
    b+=f'<path d="M36 55C42 52 47 56 49 56C51 56 56 52 62 55C58 61 52 60 49 59C46 60 40 61 36 55Z" fill="url(#beard)" stroke="{DK}" stroke-width=".8"/>'
    # helm
    b+=f'<path d="M30 46C28 24 40 14 49 14C58 14 70 24 68 46H62V42H36V46Z" fill="url(#helm)" stroke="{DK}" stroke-width="1.2"/>'
    b+=f'<path d="M46 14H52L53 5H45Z" fill="url(#br)" stroke="{DK}" stroke-width=".9"/>'
    b+=f'<rect x="29" y="35" width="40" height="5" fill="url(#br)" stroke="{DK}" stroke-width=".9"/><path d="M46 40H52V56L49 58L46 56Z" fill="url(#helm)" stroke="{DK}" stroke-width=".9"/>'
    b+=stud(35,37.5,1.6)+stud(63,37.5,1.6)+stud(49,37.5,1.6)
    b+='</g>'
    return svg('dwarf-corner-b.svg',100,100,d,b)

# =============================================================== authored relief (height pass)
def hstud(x,y,r):
    return f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#hst)"/>'
def capital_h():
    """Anvil capital: horned top plate with a chamfered face, a convex waist, a chamfered foot, a hammer lying across."""
    d=hdome('hst',.62,1.0)+hlg('horn',0,0,16,0,[(0,.52),(1,.84)])+hcyl('waist',18,0,54,0,.50,.74)
    d+=hcyl('hdl',0,6.5,0,11.5,.64,.88,True,n=6)+hcyl('hh',0,0,0,12,.80,1.0,True,n=6,p=.8)
    b=hrect(0,0,72,64,.10)
    b+='<path d="M0 24L16 14H72V28H54V34C54 40 50 44 50 48V52H66V64H6V52H22V48C22 44 18 40 18 34V28H6Z" fill="url(#horn)"/>'
    b+=hrect(16,14,56,14,.82)
    b+=hrect(16,14,56,2,.95)+flat('M0 24L16 14V28H6Z',.84)+tube('M0.5 24L16 14.5',2.4,.60,.90,n=4)
    b+=hrect(16,26.5,56,1.5,.62)
    b+='<path d="M18 28H54V34C54 40 50 44 50 48V52H22V48C22 44 18 40 18 34Z" fill="url(#waist)"/>'
    b+=bevel('M6 52H66V64H6Z',.55,.80,3,3.6)+hrect(7,52,58,1.6,.92)
    # hammer: round handle and a chamfered head
    b+=hrect(12,6.5,34,5,'url(#hdl)',1.5)
    b+=flat('M42 0H60L62 3V12H40V3Z',.92)+flat('M43 1.4H59L60.6 3.4V10.6H41.4V3.4Z',.99)+hrect(40,10,22,2,.80)
    b+=hstud(10,58,2)+hstud(62,58,2)
    return hsvg('dwarf-capital.h.svg',72,64,d,b)

def corner_h():
    """Axe on a plate: round haft, a wedge blade thinning to the edge, a chamfered bronze socket, studs."""
    d=hdome('hst',.62,1.0)+hcyl('haft',33,0,41,0,.38,.80)+hlg('blade',42,0,86,0,[(0,.90),(.55,.66),(1,.48)])
    d+=hcyl('sock',0,36,0,64,.74,.96,True,n=7)+hdome('lug',.6,.94)
    b=hrect(0,0,100,100,.30)
    b+=bevel('M2 2H90L98 10V98H12L2 88Z',.26,.62,4,6)
    b+=flat('M7 7H88L93 12V93H14L7 86Z',.60)
    b+=flat('M12 12H86V86H12Z',.38)+flat('M13.5 13.5H84.5V84.5H13.5Z',.20)+flat('M15 15H83V83H15Z',.12)
    b+=hrect(33,12,8,76,'url(#haft)')
    b+='<path d="M24 36H42L66 22C84 36 86 60 66 78L42 64H24Z" fill="url(#blade)"/>'
    b+=tube('M66 22C86 38 86 62 66 78',2.8,.50,.74,n=5)           # honed cutting edge
    b+=flat('M50 38C62 34 70 40 72 50C70 60 62 66 50 62Z',.50)+flat('M52 40C62 37 68 42 70 50C68 58 62 63 52 60Z',.40)   # recessed rune field
    b+=bevel('M24 36H42V64H24Z',.60,.90,3,2.6)+hrect(24,36,18,28,'url(#sock)')
    b+=hstud(30,41,2.4)+hstud(30,59,2.4)
    for y in (20,75): b+=bevel(f'M31 {y}H43V{y+3.4}H31Z',.60,.92,2,1.6)
    return hsvg('dwarf-corner.h.svg',100,100,d,b)

def corner_b_h():
    """Bearded guardian: helmet dome with a brow band and nasal, a heavy beard mass with locks, round shoulders."""
    d=hdome('helm',.50,.98,.5,.55,r=.62)+hdome('fc',.50,.80,.5,.4,r=.66)+hdome('brd',.46,.90,.5,.30,r=.70)+hdome('sh',.34,.62,.5,.7,r=.66)
    d+=hdome('pld',.55,.86)+hcyl('band',0,35,0,40,.82,.97,True,n=6)+hdome('hst',.62,1.0)+hcyl('nas',46,0,52,0,.78,.97)
    b=hrect(0,0,100,100,.30)
    b+=bevel('M12 2H98V88L88 98H2V12Z',.26,.62,4,6)
    b+=flat('M16 7H93V86L86 93H7V16Z',.60)
    b+=flat('M12 90V40C12 22 28 10 50 10C72 10 86 22 86 40V90Z',.42)+flat('M13.5 90V40C13.5 23 29 11.5 50 11.5C71 11.5 84.5 23 84.5 40V90Z',.22)+flat('M15 90V40C15 24 30 13 50 13C70 13 83 24 83 40V90Z',.12)
    b+='<path d="M14 90V78C14 68 24 64 38 62H60C74 64 84 68 84 78V90Z" fill="url(#sh)"/>'
    b+='<path d="M14 80C14 68 24 66 30 68L30 80Z" fill="url(#pld)"/><path d="M84 80C84 68 74 66 68 68L68 80Z" fill="url(#pld)"/>'
    # beard: a mass with grooves between locks, then the moustache over it
    b+='<path d="M31 50C27 64 30 80 49 92C68 80 71 64 67 50C58 58 40 58 31 50Z" fill="url(#brd)"/>'
    for p,w in (('M40 62C39 70 41 80 46 88',5),('M49 62C49 70 49 80 49 90',5),('M58 62C59 70 57 80 52 88',5),('M34 54C32 64 35 74 40 82',4),('M64 54C66 64 63 74 58 82',4)):
        b+=tube(p,w,.60,.90,n=8)
    b+='<path d="M38 72H60V76H38Z" fill="'+gv(.94)+'" rx="1.5"/>'+hrect(38,72,22,1.2,.99)
    # face: a round plane, nose ridge, sunk eyes, moustache
    b+='<path d="M36 44H62V54C60 58 56 60 49 60C42 60 38 58 36 54Z" fill="url(#fc)"/>'
    b+='<path d="M38 49H46M52 49H60" stroke="'+gv(.34)+'" stroke-width="2.4"/>'
    b+=tube('M47.5 46C47 52 46 55 49 57.5C52 55 51 52 50.5 46',3.2,.70,.98,n=6)
    b+=tube('M36 55C42 51.5 47 56 49 56C51 56 56 51.5 62 55C58 61 52 60 49 59C46 60 40 61 36 55Z',2.4,.74,.94,n=5)
    b+=f'<path d="M36 55C42 52 47 56 49 56C51 56 56 52 62 55C58 61 52 60 49 59C46 60 40 61 36 55Z" fill="{gv(.86)}"/>'
    # helm: dome, brow band, nasal, crest
    b+='<path d="M30 46C28 24 40 14 49 14C58 14 70 24 68 46H62V42H36V46Z" fill="url(#helm)"/>'
    b+=tube('M33 30C36 20 44 16 49 16C54 16 62 20 65 30',2.2,.80,.96,n=5)   # helm ridge
    b+='<rect x="29" y="35" width="40" height="5" fill="url(#band)"/>'
    b+='<path d="M46 40H52V56L49 58L46 56Z" fill="url(#nas)"/>'
    b+=flat('M46 14H52L53 5H45Z',.99)+hrect(45,5,8,1.4,1.0)
    for x in (35,49,63): b+=hstud(x,37.5,1.6)
    return hsvg('dwarf-corner-b.h.svg',100,100,d,b)

def lintel_h():
    """Beam with nails and recessed chevron inlay; the plaque with seven faceted stars and a hammer."""
    cx=308; W=704
    d=hdome('hst',.62,1.0)+hcyl('hdl',cx-4,0,cx+4,0,.62,.88)+hcyl('hhd',0,26,0,41,.80,.98,True,n=7)
    d+=hdome('nl',.66,.98)+hcyl('plq',0,3,0,58,.60,.80,True,n=6,p=.9)
    # recessed zig-zag channel: the inlay sits below the beam face
    d+='<pattern id="zzh" width="22" height="9" patternUnits="userSpaceOnUse" y="46"><path d="M0 8L11 1L22 8" fill="none" stroke="'+gv(.30)+'" stroke-width="5.2"/><path d="M0 8L11 1L22 8" fill="none" stroke="'+gv(.44)+'" stroke-width="3"/></pattern>'
    b=f'<rect y="45" width="{W}" height="11" fill="{gv(.64)}"/><rect y="46" width="{W}" height="9" fill="url(#zzh)"/>'
    for k in range(W//88):
        x=k*88
        b+=bevel(f'M{x+37} 21H{x+51}V35H{x+37}Z',.50,.74,2,2)
        b+=f'<circle cx="{x+44}" cy="28" r="5" fill="url(#nl)"/>'
    b+=bevel(f'M{cx-104} 3H{cx+104}L{cx+118} 14V46L{cx+104} 58H{cx-104}L{cx-118} 46V14Z',.50,.78,4,5)
    b+=flat(f'M{cx-98} 8H{cx+98}L{cx+110} 17V44L{cx+98} 53H{cx-98}L{cx-110} 44V17Z',.50)+flat(f'M{cx-96.6} 9.4H{cx+96.6}L{cx+108.6} 18V43L{cx+96.6} 51.6H{cx-96.6}L{cx-108.6} 43V18Z',.30)
    for i in range(7):
        x=cx+(i-3)*27; y=14+((i-3)**2)*2.3
        r=7.5 if i==3 else 6.2
        b+=star_facets(x,y,r,8,.42,lo=.66,hi=.98)
    b+=f'<path d="M{cx-4} 36H{cx+4}V55H{cx+3}V57H{cx-3}V55H{cx-4}Z" fill="url(#hdl)"/>'
    b+=f'<path d="M{cx-22} 26H{cx+22}L{cx+26} 29V38L{cx+22} 41H{cx-22}L{cx-26} 38V29Z" fill="url(#hhd)"/>'
    b+=hrect(cx-20,27.2,40,1.6,1.0)+bevel(f'M{cx-27} 26H{cx-22}V41H{cx-27}Z',.70,.96,2,1.4)+bevel(f'M{cx+22} 26H{cx+27}V41H{cx+22}Z',.70,.96,2,1.4)
    return hsvg('dwarf-lintel.h.svg',W,88,d,b)

def sill_h():
    """Knot-work diamonds as round bronze rods in a recessed band, an octagonal plaque with an anvil and two studs."""
    cx=280; W=672
    d=hdome('hst',.62,1.0)+hcyl('plq',0,6,0,50,.60,.80,True,n=6,p=.9)+hcyl('anv',0,17,0,43,.78,1.0,True,n=6)
    kn=''.join(tube(p,3.2,.30,.62,n=6) for p in ('M0 13L14 1L28 13L14 25Z','M28 13L42 1L56 13L42 25Z'))
    d+=f'<pattern id="knh" width="56" height="26" patternUnits="userSpaceOnUse" x="0" y="14">{kn}</pattern>'
    b=f'<rect y="10" width="{W}" height="34" fill="{gv(.14)}"/><rect y="14" width="{W}" height="26" fill="url(#knh)"/>'
    b+=bevel(f'M{cx-60} 6H{cx+60}L{cx+70} 28L{cx+60} 50H{cx-60}L{cx-70} 28Z',.50,.76,4,5)
    b+=flat(f'M{cx-52} 11H{cx+52}L{cx+60} 28L{cx+52} 45H{cx-52}L{cx-60} 28Z',.50)+flat(f'M{cx-50.6} 12.4H{cx+50.6}L{cx+58.4} 28L{cx+50.6} 43.6H{cx-50.6}L{cx-58.4} 28Z',.26)
    b+=f'<path d="M{cx-26} 22L{cx-12} 17H{cx+24}V25H{cx+14}V30C{cx+14} 33 {cx+10} 34 {cx+10} 37V39H{cx+18}V43H{cx-18}V39H{cx-10}V37C{cx-10} 34 {cx-14} 33 {cx-14} 30V25H{cx-20}Z" fill="url(#anv)"/>'
    b+=hrect(cx-12,17,36,1.6,1.0)+hrect(cx-18,41.4,36,1.6,.74)
    b+=hstud(cx-46,28,3)+hstud(cx+46,28,3)
    return hsvg('dwarf-sill.h.svg',W,56,d,b)
