#!/bin/bash

a=3.54 #Angstrom FCC Al0.5CoCrFeNi Ref: Liang et al. Metals 2022, 12 (11).

atomsk --create fcc $a Ni orient [11-2] [111] [-110] ni_unit.xsf cfg
atomsk ni_unit.xsf -duplicate 10 7 10 ni_super.xsf cfg
atomsk ni_super.xsf -select random 22.22% Ni -substitute Ni Fe feni_super.xsf cfg
atomsk feni_super.xsf -select random 22.22% Ni -substitute Ni Cr crfeni_super.xsf cfg
atomsk crfeni_super.xsf -select random 22.22% Ni -substitute Ni Co cocrfeni_super.xsf cfg
atomsk cocrfeni_super.xsf -select random 11.12% Ni -substitute Ni Al al0p5cocrfeni_super.xsf cfg


# Apply mirror symmetry
atomsk al0p5cocrfeni_super.xsf -mirror 0 Y -wrap al0p5cocrfeni_mirror.xsf
# Merge the original super cell with the mirror supercell
atomsk --merge Y 2 al0p5cocrfeni_super.xsf al0p5cocrfeni_mirror.xsf al0p5cocrfeni_nanotwin.xsf cfg
