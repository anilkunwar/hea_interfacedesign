import streamlit as st
import sqlite3
import io
import numpy as np
from pymatgen.core import Lattice, Structure
from pymatgen.io.cif import CifWriter
from pymatgen.io.lammps.data import LammpsData
import random
import uuid
import os
import tempfile
import pathlib

# Initialize SQLite database
def init_db():
    conn = sqlite3.connect("structures.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS structures
                 (id TEXT, filename TEXT UNIQUE, format TEXT, data BLOB)''')
    conn.commit()
    return conn

# Check if filename exists in database and prompt for a unique name
def get_unique_filename(conn, filename, format):
    base_name = os.path.splitext(filename)[0]
    c = conn.cursor()
    proposed_filename = f"{base_name}.{format.lower()}"
    c.execute("SELECT filename FROM structures WHERE filename = ?", (proposed_filename,))
    
    if c.fetchone():
        st.warning(f"File '{proposed_filename}' already exists.")
        iteration = 0
        while True:
            # Use a unique key for each text_input to avoid duplicate ID error
            new_name = st.text_input(
                f"Enter a new name for {base_name} (without extension):",
                f"{base_name}_new_{iteration}",
                key=f"text_input_{base_name}_{iteration}"
            )
            proposed_filename = f"{new_name}.{format.lower()}"
            c.execute("SELECT filename FROM structures WHERE filename = ?", (proposed_filename,))
            if not c.fetchone():
                return proposed_filename
            st.error(f"Filename '{proposed_filename}' already exists. Please choose a different name.")
            iteration += 1
    return proposed_filename

# Save file to SQLite
def save_to_db(conn, filename, format, data):
    try:
        c = conn.cursor()
        file_id = str(uuid.uuid4())
        c.execute("INSERT INTO structures (id, filename, format, data) VALUES (?, ?, ?, ?)",
                  (file_id, filename, format, data))
        conn.commit()
    except sqlite3.IntegrityError as e:
        st.error(f"Database error: {e}. Try a different filename.")
        raise
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        raise

# Clear database (optional, for testing or resetting)
def clear_database(conn):
    c = conn.cursor()
    c.execute("DELETE FROM structures")
    conn.commit()
    st.success("Database cleared successfully.")

# Display download section in sidebar
def display_download_section():
    st.sidebar.header("Download Files")
    try:
        conn = init_db()  # Create a new connection for the sidebar
        c = conn.cursor()
        c.execute("SELECT filename, format, data FROM structures")
        files = c.fetchall()
        if not files:
            st.sidebar.info("No files available for download.")
        for filename, format, data in files:
            st.sidebar.download_button(
                label=f"Download {filename}",
                data=data,
                file_name=filename,
                mime=f"text/{format.lower()}",
                key=f"download_{filename}"  # Unique key for each download button
            )
        conn.close()
    except Exception as e:
        st.sidebar.error(f"Error retrieving files from database: {e}")

# Streamlit app
st.title("Crystal Structure Generator (Al0.5CoCrFeNi Nanotwin)")

# Option to clear database
if st.button("Clear Database"):
    conn = init_db()
    clear_database(conn)
    conn.close()
    st.experimental_rerun()

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
        try:
            # Step 1: Create FCC Ni unit cell
            lattice = Lattice.cubic(a)
            coords = [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]
            ni_unit = Structure(lattice, ["Ni"] * 4, coords)
            # Reorient to [11-2], [111], [-110] (simplified)
            ni_unit = ni_unit.get_reduced_structure()
            ni_unit_file = "ni_unit.xsf"
            ni_unit_file = get_unique_filename(conn, ni_unit_file, "XSF")
            xsf_str = ni_unit.to(fmt="xsf")
            save_to_db(conn, ni_unit_file, "XSF", xsf_str.encode())
            st.success(f"Created {ni_unit_file}")

            # Step 2: Duplicate to supercell
            ni_super = ni_unit * (nx, ny, nz)
            ni_super_file = "ni_super.xsf"
            ni_super_file = get_unique_filename(conn, ni_super_file, "XSF")
            xsf_str = ni_super.to(fmt="xsf")
            save_to_db(conn, ni_super_file, "XSF", xsf_str.encode())
            st.success(f"Created {ni_super_file}")

            # Step 3: Substitute Ni with Fe
            feni_super = ni_super.copy()
            num_atoms = len(feni_super)
            num_sub = int(num_atoms * m / 100)
            ni_indices = [i for i, site in enumerate(feni_super) if site.species_string == "Ni"]
            if len(ni_indices) < num_sub:
                st.error(f"Not enough Ni atoms for Fe substitution. Required: {num_sub}, Available: {len(ni_indices)}")
                raise ValueError("Insufficient Ni atoms for substitution")
            fe_indices = random.sample(ni_indices, num_sub)
            for idx in fe_indices:
                feni_super[idx] = "Fe"
            feni_super_file = "feni_super.xsf"
            feni_super_file = get_unique_filename(conn, feni_super_file, "XSF")
            xsf_str = feni_super.to(fmt="xsf")
            save_to_db(conn, feni_super_file, "XSF", xsf_str.encode())
            st.success(f"Created {feni_super_file}")

            # Step 4: Substitute Ni with Cr
            crfeni_super = feni_super.copy()
            ni_indices = [i for i, site in enumerate(crfeni_super) if site.species_string == "Ni"]
            if len(ni_indices) < num_sub:
                st.error(f"Not enough Ni atoms for Cr substitution. Required: {num_sub}, Available: {len(ni_indices)}")
                raise ValueError("Insufficient Ni atoms for substitution")
            cr_indices = random.sample(ni_indices, num_sub)
            for idx in cr_indices:
                crfeni_super[idx] = "Cr"
            crfeni_super_file = "crfeni_super.xsf"
            crfeni_super_file = get_unique_filename(conn, crfeni_super_file, "XSF")
            xsf_str = crfeni_super.to(fmt="xsf")
            save_to_db(conn, crfeni_super_file, "XSF", xsf_str.encode())
            st.success(f"Created {crfeni_super_file}")

            # Step 5: Substitute Ni with Co
            cocrfeni_super = crfeni_super.copy()
            ni_indices = [i for i, site in enumerate(cocrfeni_super) if site.species_string == "Ni"]
            if len(ni_indices) < num_sub:
                st.error(f"Not enough Ni atoms for Co substitution. Required: {num_sub}, Available: {len(ni_indices)}")
                raise ValueError("Insufficient Ni atoms for substitution")
            co_indices = random.sample(ni_indices, num_sub)
            for idx in co_indices:
                cocrfeni_super[idx] = "Co"
            cocrfeni_super_file = "cocrfeni_super.xsf"
            cocrfeni_super_file = get_unique_filename(conn, cocrfeni_super_file, "XSF")
            xsf_str = cocrfeni_super.to(fmt="xsf")
            save_to_db(conn, cocrfeni_super_file, "XSF", xsf_str.encode())
            st.success(f"Created {cocrfeni_super_file}")

            # Step 6: Substitute Ni with Al
            al0p5cocrfeni_super = cocrfeni_super.copy()
            ni_indices = [i for i, site in enumerate(al0p5cocrfeni_super) if site.species_string == "Ni"]
            num_al_sub = int(num_atoms * n / 100)
            if len(ni_indices) < num_al_sub:
                st.error(f"Not enough Ni atoms for Al substitution. Required: {num_al_sub}, Available: {len(ni_indices)}")
                raise ValueError("Insufficient Ni atoms for substitution")
            al_indices = random.sample(ni_indices, num_al_sub)
            for idx in al_indices:
                al0p5cocrfeni_super[idx] = "Al"
            al0p5cocrfeni_super_file = "al0p5cocrfeni_super.xsf"
            al0p5cocrfeni_super_file = get_unique_filename(conn, al0p5cocrfeni_super_file, "XSF")
            xsf_str = al0p5cocrfeni_super.to(fmt="xsf")
            save_to_db(conn, al0p5cocrfeni_super_file, "XSF", xsf_str.encode())
            st.success(f"Created {al0p5cocrfeni_super_file}")

            # Step 7: Mirror along Y (fractional coords)
            base = al0p5cocrfeni_super  # Rename for clarity
            base_frac = base.frac_coords.copy()
            mirrored_frac = base_frac.copy()
            mirrored_frac[:, 1] = (-mirrored_frac[:, 1]) % 1.0  # Mirror across y=0, wrap to [0,1)

            # Step 8: Merge into a nanotwin with doubled Y lattice
            super_lat = (base * (1, 2, 1)).lattice  # Doubled-Y lattice
            top_frac = mirrored_frac.copy()
            top_frac[:, 1] = (top_frac[:, 1] + 0.5) % 1.0  # Shift mirrored half to top
            species_combined = list(base.species) + list(base.species)
            coords_combined = np.vstack([base_frac, top_frac])
            merged_structure = Structure(super_lat, species_combined, coords_combined, coords_are_cartesian=False)
            al0p5cocrfeni_nanotwin_file = "al0p5cocrfeni_nanotwin.xsf"
            al0p5cocrfeni_nanotwin_file = get_unique_filename(conn, al0p5cocrfeni_nanotwin_file, "XSF")
            xsf_str = merged_structure.to(fmt="xsf")
            save_to_db(conn, al0p5cocrfeni_nanotwin_file, "XSF", xsf_str.encode())
            st.success(f"Created {al0p5cocrfeni_nanotwin_file}")

            # Save CFG and CIF versions of final structure
            with tempfile.TemporaryDirectory() as td:
                p = pathlib.Path(td) / "tmp.data"
                LammpsData.from_structure(merged_structure).write_file(str(p))
                cfg_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.cfg", "CFG")
                save_to_db(conn, cfg_file, "CFG", p.read_bytes())
                st.success(f"Created {cfg_file}")

            with tempfile.TemporaryDirectory() as td:
                p = pathlib.Path(td) / "tmp.cif"
                CifWriter(merged_structure).write_file(str(p))
                cif_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.cif", "CIF")
                save_to_db(conn, cif_file, "CIF", p.read_bytes())
                st.success(f"Created {cif_file}")

        except Exception as e:
            st.error(f"Error during structure generation: {e}")
            raise

# Display download section in sidebar
display_download_section()
