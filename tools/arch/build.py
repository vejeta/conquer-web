import gen_human as h, gen_elf as e, gen_dwarf as d, gen_orc as o
for m in (h,e,d,o):
    m.column(); m.lintel(); m.sill(); m.corner()
d.corner_b()
