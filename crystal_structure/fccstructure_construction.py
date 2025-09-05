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

# -------------------- Database helpers -------------------- #
def init_db():
    conn = sqlite3.connect("structures.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS structures
                 (id TEXT, filename TEXT UNIQUE, format TEXT, data BLOB)''')
    conn.commit()
    return conn

def get_unique_filename(conn, filename, format):
    """
    Ensure unique filename in DB. If conflict, prompt user with a text_input until a unique name is provided.
    """
    base_name = os.path.splitext(filename)[0]
    c = conn.cursor()
    proposed_filename = f"{base_name}.{format.lower()}"
    c.execute("SELECT filename FROM structures WHERE filename = ?", (proposed_filename,))
    
    if c.fetchone():
        st.warning(f"File '{proposed_filename}' already exists.")
        iteration = 0
        while True:
            new_name = st.text_input(
                f"Enter a new name for {base_name} (without extension):",
                f"{base_name}_new_{iteration}",
                key=f"rename_{base_name}_{format}_{iteration}"  # Unique key to avoid duplicate ID error
            )
            proposed_filename = f"{new_name}.{format.lower()}"
            c.execute("SELECT filename FROM structures WHERE filename = ?", (proposed_filename,))
            if not c.fetchone():
                return proposed_filename
            st.error(f"Filename '{proposed_filename}' already exists. Please choose a different name.")
            iteration += 1
    return proposed_filename

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

def clear_database(conn):
    c = conn.cursor()
    c.execute("DELETE FROM structures")
    conn.commit()
    st.success("Database cleared successfully.")

def display_download_section():
    st.sidebar.header("Download Files")
    try:
        conn = init_db()
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
                key=f"download_{filename}"
            )
        conn.close()
    except Exception as e:
        st.sidebar.error(f"Error retrieving files from database: {e}")

# -------------------- Streamlit UI -------------------- #
st.title("Crystal Structure Generator (Al0.5CoCrFeNi Nanotwin)")

if st.button("Clear Database"):
    conn = init_db()
    clear_database(conn)
    conn.close()
    st.experimental_rerun()

a = st.number_input("Lattice constant (Å)", value=3.54, min_value=0.1, format="%.2f")
m = st.number_input("Major element substitution percentage (%)", value=22.22, min_value=0.0, max_value=100.0, format="%.2f")
n = st.number_input("Dopant (Al) substitution percentage (%)", value=11.12, min_value=0.0, max_value=100.0, format="%.2f")
nx, ny, nz = 10, 7, 10  # Supercell dimensions

conn = init_db()

# -------------------- Structure Generation -------------------- #
if st.button("Generate Structures"):
    with st.spinner("Generating structures..."):
        try:
            # Step 1: FCC Ni unit cell
            lattice = Lattice.cubic(a)
            coords = [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]
            ni_unit = Structure(lattice, ["Ni"] * 4, coords)
            ni_unit = ni_unit.get_reduced_structure()
            ni_unit_file = get_unique_filename(conn, "ni_unit.xsf", "XSF")
            save_to_db(conn, ni_unit_file, "XSF", ni_unit.to(fmt="xsf").encode())
            st.success(f"Created {ni_unit_file}")

            # Step 2: Supercell
            ni_super = ni_unit * (nx, ny, nz)
            ni_super_file = get_unique_filename(conn, "ni_super.xsf", "XSF")
            save_to_db(conn, ni_super_file, "XSF", ni_super.to(fmt="xsf").encode())
            st.success(f"Created {ni_super_file}")

            # Step 3: Substitute Ni → Fe
            feni_super = ni_super.copy()
            num_atoms = len(feni_super)
            num_sub = int(num_atoms * m / 100)
            ni_indices = [i for i, s in enumerate(feni_super) if s.species_string == "Ni"]
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Fe substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            for idx in random.sample(ni_indices, num_sub):
                feni_super[idx] = "Fe"
            feni_super_file = get_unique_filename(conn, "feni_super.xsf", "XSF")
            save_to_db(conn, feni_super_file, "XSF", feni_super.to(fmt="xsf").encode())
            st.success(f"Created {feni_super_file}")

            # Step 4: Substitute Ni → Cr
            crfeni_super = feni_super.copy()
            ni_indices = [i for i, s in enumerate(crfeni_super) if s.species_string == "Ni"]
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Cr substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            for idx in random.sample(ni_indices, num_sub):
                crfeni_super[idx] = "Cr"
            crfeni_super_file = get_unique_filename(conn, "crfeni_super.xsf", "XSF")
            save_to_db(conn, crfeni_super_file, "XSF", crfeni_super.to(fmt="xsf").encode())
            st.success(f"Created {crfeni_super_file}")

            # Step 5: Substitute Ni → Co
            cocrfeni_super = crfeni_super.copy()
            ni_indices = [i for i, s in enumerate(cocrfeni_super) if s.species_string == "Ni"]
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Co substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            for idx in random.sample(ni_indices, num_sub):
                cocrfeni_super[idx] = "Co"
            cocrfeni_super_file = get_unique_filename(conn, "cocrfeni_super.xsf", "XSF")
            save_to_db(conn, cocrfeni_super_file, "XSF", cocrfeni_super.to(fmt="xsf").encode())
            st.success(f"Created {cocrfeni_super_file}")

            # Step 6: Substitute Ni → Al
            al_super = cocrfeni_super.copy()
            ni_indices = [i for i, s in enumerate(al_super) if s.species_string == "Ni"]
            num_al_sub = int(num_atoms * n / 100)
            if len(ni_indices) < num_al_sub:
                raise ValueError(f"Insufficient Ni atoms for Al substitution. Required: {num_al_sub}, Available: {len(ni_indices)}")
            for idx in random.sample(ni_indices, num_al_sub):
                al_super[idx] = "Al"
            al_super_file = get_unique_filename(conn, "al0p5cocrfeni_super.xsf", "XSF")
            save_to_db(conn, al_super_file, "XSF", al_super.to(fmt="xsf").encode())
            st.success(f"Created {al_super_file}")

            # Step 7: Mirror along Y
            base_frac = al_super.frac_coords.copy()
            mirrored_frac = base_frac.copy()
            mirrored_frac[:, 1] = (-mirrored_frac[:, 1]) % 1.0

            # Step 8: Merge into nanotwin (double Y)
            super_lat = (al_super * (1, 2, 1)).lattice
            top_frac = mirrored_frac.copy()
            top_frac[:, 1] = (top_frac[:, 1] + 0.5) % 1.0
            species_combined = list(al_super.species) + list(al_super.species)
            coords_combined = np.vstack([base_frac, top_frac])
            merged_structure = Structure(super_lat, species_combined, coords_combined, coords_are_cartesian=False)

            nanotwin_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.xsf", "XSF")
            save_to_db(conn, nanotwin_file, "XSF", merged_structure.to(fmt="xsf").encode())
            st.success(f"Created {nanotwin_file}")

            # Save CFG
            with tempfile.TemporaryDirectory() as td:
                p = pathlib.Path(td) / "tmp.data"
                LammpsData.from_structure(merged_structure).write_file(str(p))
                cfg_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.cfg", "CFG")
                save_to_db(conn, cfg_file, "CFG", p.read_bytes())
                st.success(f"Created {cfg_file}")

            # Save CIF
            with tempfile.TemporaryDirectory() as td:
                p = pathlib.Path(td) / "tmp.cif"
                CifWriter(merged_structure).write_file(str(p))
                cif_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.cif", "CIF")
                save_to_db(conn, cif_file, "CIF", p.read_bytes())
                st.success(f"Created {cif_file}")

        except Exception as e:
            st.error(f"Error during structure generation: {e}")
            raise
        finally:
            conn.close()

# -------------------- Downloads -------------------- #
display_download_section()
