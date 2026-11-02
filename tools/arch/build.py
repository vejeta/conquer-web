import gen_human as h, gen_elf as e, gen_dwarf as d, gen_orc as o
for m in (h,e,d,o):
    m.column(); m.lintel(); m.sill(); m.corner()
    for f in ("corner_h","capital_h","lintel_h","sill_h","corner_e","lintel_e","sill_e"):
        if hasattr(m,f): getattr(m,f)()
d.corner_b()
if hasattr(d,"corner_b_h"): d.corner_b_h()
