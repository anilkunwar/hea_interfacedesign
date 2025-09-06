#!/bin/bash

a=2.88 #Angstrom BCC Al1.1CoCrFeNi Ref: Custodio et al. Powder Technology 2024, 437: 119556.
m=19.60 # percentage of major elements
n=21.57 #percentage of dopant

atomsk --create bcc $a Ni orient [11-2] [111] [-110] ni_unit.xsf cfg
atomsk ni_unit.xsf -duplicate 10 7 10 ni_super.xsf cfg
atomsk ni_super.xsf -select random $m% Ni -substitute Ni Fe feni_super.xsf cfg
atomsk feni_super.xsf -select random $m% Ni -substitute Ni Cr crfeni_super.xsf cfg
atomsk crfeni_super.xsf -select random $m% Ni -substitute Ni Co cocrfeni_super.xsf cfg
atomsk cocrfeni_super.xsf -select random $n% Ni -substitute Ni Al al1p1cocrfeni_super.xsf cfg


# Apply mirror symmetry
atomsk al1p1cocrfeni_super.xsf -mirror 0 Y -wrap al1p1cocrfeni_mirror.xsf
# Merge the original super cell with the mirror supercell
atomsk --merge Y 2 al1p1cocrfeni_super.xsf al1p1cocrfeni_mirror.xsf al1p1cocrfeni_nanotwin.xsf cfg
