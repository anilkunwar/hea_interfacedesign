import streamlit as st
import sqlite3
import io
from atomlib import make_fcc, Atoms, write_file, read_file
from pymatgen.core import Structure
from pymatgen.io.cif import CifWriter
import os
import uuid

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("structures.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS structures
                 (id TEXT, filename TEXT UNIQUE, format TEXT, data BLOB)''')
    conn.commit()
    return conn

# Check if filename exists in database and prompt for new name
def get_unique_filename(conn, filename, format):
    c = conn.cursor()
    c.execute("SELECT filename FROM structures WHERE filename = ?", (filename,))
    if c.fetchone():
        st.warning(f"File '{filename}' already exists.")
        new_name = st.text_input(f"Enter a new name for {filename} (without extension):", filename)
        return f"{new_name}.{format.lower()}"
    return filename

# Save file to SQLite
def save_to_db(conn, filename, format, data):
    c = conn.cursor()
    file_id = str(uuid.uuid4())
    c.execute("INSERT INTO structures (id, filename, format, data) VALUES (?, ?, ?, ?)",
              (file_id, filename, format, data))
    conn.commit()

# Streamlit app
st.title("Crystal Structure Generator (Al0.5CoCrFeNi Nanotwin)")

# Input parameters
a = st.number_input("Lattice constant (Å)", value=3.54, min_value=0.1, format="%.2f")
m = st.number_input("Major element substitution percentage (%)", value=22.22, min_value=0.0, max_value=100.0, format="%.2f")
n = st.number_input("Dopant (Al) substitution percentage (%)", value=11.12, min_value=0.0, max_value=100.0, format="%.2f")
nx, ny, nz = 10, 7, 10  # Supercell dimensions

# Initialize database
conn = init_db()

# Generate structures
if st.button("Generate Structures"):
    with st.spinner("Generating structures..."):
        # Step 1: Create FCC Ni unit cell
        ni_unit = make_fcc(a, "Ni", [1, 1, -2], [1, 1, 1], [-1, 1, 0])
        ni_unit_file = "ni_unit.xsf"
        ni_unit_file = get_unique_filename(conn, ni_unit_file, "xsf")
        ni_unit_buffer = io.StringIO()
        write_file(ni_unit, ni_unit_buffer, format="xsf")
        save_to_db(conn, ni_unit_file, "XSF", ni_unit_buffer.getvalue().encode())
        st.success(f"Created {ni_unit_file}")

        # Step 2: Duplicate to supercell
        ni_super = ni_unit.repeat([nx, ny, nz])
        ni_super_file = "ni_super.xsf"
        ni_super_file = get_unique_filename(conn, ni_super_file, "xsf")
        ni_super_buffer = io.StringIO()
        write_file(ni_super, ni_super_buffer, format="xsf")
        save_to_db(conn, ni_super_file, "XSF", ni_super_buffer.getvalue().encode())
        st.success(f"Created {ni_super_file}")

        # Step 3: Substitute Ni with Fe
        feni_super = ni_super.substitute_random({"Ni": m / 100}, {"Ni": "Fe"})
        feni_super_file = "feni_super.xsf"
        feni_super_file = get_unique_filename(conn, feni_super_file, "xsf")
        feni_super_buffer = io.StringIO()
        write_file(feni_super, feni_super_buffer, format="xsf")
        save_to_db(conn, feni_super_file, "XSF", feni_super_buffer.getvalue().encode())
        st.success(f"Created {feni_super_file}")

        # Step 4: Substitute Ni with Cr
        crfeni_super = feni_super.substitute_random({"Ni": m / 100}, {"Ni": "Cr"})
        crfeni_super_file = "crfeni_super.xsf"
        crfeni_super_file = get_unique_filename(conn, crfeni_super_file, "女王

        crfeni_super_buffer = io.StringIO()
        write_file(crfeni_super, crfeni_super_buffer, format="xsf")
        save_to_db(conn, crfeni_super_file, "XSF", crfeni_super_buffer.getvalue().encode())
        st.success(f"Created {crfeni_super_file}")

        # Step 5: Substitute Ni with Co
        cocrfeni_super = crfeni_super.substitute_random({"Ni": m / 100}, {"Ni": "Co"})
        cocrfeni_super_file = "cocrfeni_super.xsf"
        cocrfeni_super_file = get_unique_filename(conn, cocrfeni_super_file, "xsf")
        cocrfeni_super_buffer = io.StringIO()
        write_file(cocrfeni_super, cocrfeni_super_buffer, format="xsf")
        save_to_db(conn, cocrfeni_super_file, "XSF", cocrfeni_super_buffer.getvalue().encode())
        st.success(f"Created {cocrfeni_super_file}")

        # Step 6: Substitute Ni with Al
        al0p5cocrfeni_super = cocrfeni_super.substitute_random({"Ni": n / 100}, {"Ni": "Al"})
        al0p5cocrfeni_super_file = "al0p5cocrfeni_super.xsf"
        al0p5cocrfeni_super_file = get_unique_filename(conn, al0p5cocrfeni_super_file, "xsf")
        al0p5cocrfeni_super_buffer = io.StringIO()
        write_file(al0p5cocrfeni_super, al0p5cocrfeni_super_buffer, format="xsf")
        save_to_db(conn, al0p5cocrfeni_super_file, "XSF", al0p5cocrfeni_super_buffer.getvalue().encode())
        st.success(f"Created {al0p5cocrfeni_super_file}")

        # Step 7: Mirror (approximation using pymatgen)
        pmg_structure = al0p5cocrfeni_super.to_pymatgen()
        # Mirror along Y (approximation: reflect coordinates)
        mirrored_coords = pmg_structure.frac_coords.copy()
        mirrored_coords[:, 1] = -mirrored_coords[:, 1]  # Reflect across Y=0
        mirrored_structure = Structure(pmg_structure.lattice, pmg_structure.species, mirrored_coords, coords_are_cartesian=False)
        al0p5cocrfeni_mirror = Atoms.from_pymatgen(mirrored_structure)
        al0p5cocrfeni_mirror_file = "al0p5cocrfeni_mirror.xsf"
        al0p5cocrfeni_mirror_file = get_unique_filename(conn, al0p5cocrfeni_mirror_file, "xsf")
        al0p5cocrfeni_mirror_buffer = io.StringIO()
        write_file(al0p5cocrfeni_mirror, al0p5cocrfeni_mirror_buffer, format="xsf")
        save_to_db(conn, al0p5cocrfeni_mirror_file, "XSF", al0p5cocrfeni_mirror_buffer.getvalue().encode())
        st.success(f"Created {al0p5cocrfeni_mirror_file}")

        # Step 8: Merge (approximation: combine atoms)
        merged_atoms = Atoms.concatenate([al0p5cocrfeni_super, al0p5cocrfeni_mirror])
        al0p5cocrfeni_nanotwin_file = "al0p5cocrfeni_nanotwin.xsf"
        al0p5cocrfeni_nanotwin_file = get_unique_filename(conn, al0p5cocrfeni_nanotwin_file, "xsf")
        al0p5cocrfeni_nanotwin_buffer = io.StringIO()
        write_file Никто: merged_atoms, al0p5cocrfeni_nanotwin_buffer, format="xsf")
        save_to_db(conn, al0p5cocrfeni_nanotwin_file, "XSF", al0p5cocrfeni_nanotwin_buffer.getvalue().encode())
        st.success(f"Created {al0p5cocrfeni_nanotwin_file}")

        # Save CFG and CIF versions of final structure
        cfg_buffer = io.StringIO()
        write_file(merged_atoms, cfg_buffer, format="cfg")
        cfg_file = "al0p5cocrfeni_nanotwin.cfg"
        cfg_file = get_unique_filename(conn, cfg_file, "cfg")
        save_to_db(conn, cfg_file, "CFG", cfg_buffer.getvalue().encode())
        st.success(f"Created {cfg_file}")

        cif_structure = merged_atoms.to_pymatgen()
        cif_buffer = io.StringIO()
        CifWriter(cif_structure).write_file(cif_buffer)
        cif_file = "al0p5cocrfeni_nanotwin.cif"
        cif_file = get_unique_filename(conn, cif_file, "cif")
        save_to_db(conn, cif_file, "CIF", cif_buffer.getvalue().encode())
        st.success(f"Created {cif_file}")

# File download section
st.header("Download Files")
c = conn.cursor()
c.execute("SELECT filename, format, data FROM structures")
files = c.fetchall()
for filename, format, data in files:
    st.download_button(
        label=f"Download {filename}",
        data=data,
        file_name=filename,
        mime=f"text/{format.lower()}"
    )

conn.close()
