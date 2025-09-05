import streamlit as st
import sqlite3
import numpy as np
from pymatgen.core import Lattice, Structure
import random
import uuid
import os
import tempfile
import pathlib
import py3Dmol

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
    Ensure unique filename in DB by auto-incrementing (_1, _2, ...).
    """
    base_name = os.path.splitext(filename)[0]
    ext = format.lower()
    proposed_filename = f"{base_name}.{ext}"
    c = conn.cursor()

    counter = 1
    while True:
        c.execute("SELECT filename FROM structures WHERE filename = ?", (proposed_filename,))
        if not c.fetchone():
            return proposed_filename
        proposed_filename = f"{base_name}_{counter}.{ext}"
        counter += 1

def save_to_db(conn, filename, format, data):
    """
    Save structure data to database, ensuring data is not empty.
    """
    if not data or len(data) == 0:
        raise ValueError(f"Cannot save empty data for {filename}")
    try:
        c = conn.cursor()
        file_id = str(uuid.uuid4())
        c.execute("INSERT INTO structures (id, filename, format, data) VALUES (?, ?, ?, ?)",
                  (file_id, filename, format, data))
        conn.commit()
    except sqlite3.IntegrityError as e:
        st.error(f"Database error: {e}")
        raise
    except Exception as e:
        st.error(f"Error saving to database: {e}")
        raise

def clear_database(conn):
    """
    Clear all entries from the structures table.
    """
    c = conn.cursor()
    c.execute("DELETE FROM structures")
    conn.commit()
    st.success("Database cleared successfully.")

def clean_database(conn):
    """
    Remove entries with empty or invalid data from the database.
    """
    c = conn.cursor()
    c.execute("DELETE FROM structures WHERE data IS NULL OR length(data) = 0")
    conn.commit()
    st.info("Cleaned database of empty or invalid entries.")

def display_download_section():
    """
    Display download buttons for valid structure files in the sidebar.
    """
    st.sidebar.header("Download Files")
    try:
        conn = init_db()
        c = conn.cursor()
        c.execute("SELECT filename, format, data FROM structures WHERE data IS NOT NULL AND length(data) > 0")
        files = c.fetchall()
        if not files:
            st.sidebar.info("No valid files available for download.")
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

def visualize_structure(structure, format="cif"):
    """
    Visualize a pymatgen Structure object using py3Dmol.
    """
    try:
        with tempfile.TemporaryDirectory() as td:
            temp_file = pathlib.Path(td) / f"temp.{format}"
            structure.to(filename=temp_file, fmt=format)
            with open(temp_file, "r") as f:
                data = f.read()
            view = py3Dmol.view(width=600, height=400)
            view.addModel(data, format)
            view.setStyle({
                "sphere": {
                    "radius": 0.5,
                    "colorscheme": {"Ni": "silver", "Fe": "orange", "Cr": "green", "Co": "blue", "Al": "gray"}
                }
            })
            view.addUnitCell()
            view.zoomTo()
            st.components.v1.html(view._make_html(), width=600, height=400)
    except Exception as e:
        st.error(f"Error visualizing structure: {e}")

# -------------------- Streamlit UI -------------------- #
st.title("Crystal Structure Generator (Al0.5CoCrFeNi Nanotwin)")

# Clean database at startup
conn = init_db()
clean_database(conn)

# Option to clear database
if st.button("Clear Database"):
    clear_database(conn)
    conn.close()
    st.rerun()

a = st.number_input("Lattice constant (Å)", value=3.54, min_value=0.1, format="%.2f")
m = st.number_input("Major element substitution percentage (%)", value=22.22, min_value=0.0, max_value=100.0, format="%.2f")
n = st.number_input("Dopant (Al) substitution percentage (%)", value=11.12, min_value=0.0, max_value=100.0, format="%.2f")
nx, ny, nz = 10, 7, 10  # Supercell dimensions

# -------------------- Structure Generation -------------------- #
if st.button("Generate Structures"):
    with st.spinner("Generating structures..."):
        try:
            # Step 1: FCC Ni unit cell
            lattice = Lattice.cubic(a)
            coords = [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]
            ni_unit = Structure(lattice, ["Ni"] * 4, coords, coords_are_cartesian=False)
            st.write(f"Created FCC Ni unit cell with {len(ni_unit)} atoms")

            # Apply orientation: [11-2], [111], [-110]
            orientation_matrix = np.array([
                [1, 1, -2],  # X aligns with [11-2]
                [1, 1, 1],   # Y aligns with [111]
                [-1, 1, 0]   # Z aligns with [-110]
            ])
            new_lattice = Lattice(np.dot(orientation_matrix, ni_unit.lattice.matrix))
            ni_unit = Structure(new_lattice, ni_unit.species, ni_unit.frac_coords, coords_are_cartesian=False)
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "ni_unit.cif"
                ni_unit.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                ni_unit_file = get_unique_filename(conn, "ni_unit.cif", "CIF")
                save_to_db(conn, ni_unit_file, "CIF", data)
                st.success(f"Created {ni_unit_file}")

                temp_file = pathlib.Path(td) / "ni_unit.xsf"
                ni_unit.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "ni_unit.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 2: Supercell
            ni_super = ni_unit * (nx, ny, nz)
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "ni_super.cif"
                ni_super.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                ni_super_file = get_unique_filename(conn, "ni_super.cif", "CIF")
                save_to_db(conn, ni_super_file, "CIF", data)
                st.success(f"Created {ni_super_file}")

                temp_file = pathlib.Path(td) / "ni_super.xsf"
                ni_super.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "ni_super.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 3: Substitute Ni → Fe
            feni_super = ni_super.copy()
            num_atoms = len(feni_super)
            num_sub = int(num_atoms * m / 100)
            ni_indices = [i for i, s in enumerate(feni_super.species) if s.symbol == "Ni"]
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Fe substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices, num_sub)
            for idx in sub_indices:
                feni_super[idx] = "Fe"
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "feni_super.cif"
                feni_super.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                feni_super_file = get_unique_filename(conn, "feni_super.cif", "CIF")
                save_to_db(conn, feni_super_file, "CIF", data)
                st.success(f"Created {feni_super_file}")

                temp_file = pathlib.Path(td) / "feni_super.xsf"
                feni_super.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "feni_super.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 4: Substitute Ni → Cr
            crfeni_super = feni_super.copy()
            ni_indices = [i for i, s in enumerate(crfeni_super.species) if s.symbol == "Ni"]
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Cr substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices, num_sub)
            for idx in sub_indices:
                crfeni_super[idx] = "Cr"
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "crfeni_super.cif"
                crfeni_super.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                crfeni_super_file = get_unique_filename(conn, "crfeni_super.cif", "CIF")
                save_to_db(conn, crfeni_super_file, "CIF", data)
                st.success(f"Created {crfeni_super_file}")

                temp_file = pathlib.Path(td) / "crfeni_super.xsf"
                crfeni_super.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "crfeni_super.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 5: Substitute Ni → Co
            cocrfeni_super = crfeni_super.copy()
            ni_indices = [i for i, s in enumerate(cocrfeni_super.species) if s.symbol == "Ni"]
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Co substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices, num_sub)
            for idx in sub_indices:
                cocrfeni_super[idx] = "Co"
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "cocrfeni_super.cif"
                cocrfeni_super.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                cocrfeni_super_file = get_unique_filename(conn, "cocrfeni_super.cif", "CIF")
                save_to_db(conn, cocrfeni_super_file, "CIF", data)
                st.success(f"Created {cocrfeni_super_file}")

                temp_file = pathlib.Path(td) / "cocrfeni_super.xsf"
                cocrfeni_super.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "cocrfeni_super.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 6: Substitute Ni → Al
            al_super = cocrfeni_super.copy()
            ni_indices = [i for i, s in enumerate(al_super.species) if s.symbol == "Ni"]
            num_al_sub = int(num_atoms * n / 100)
            if len(ni_indices) < num_al_sub:
                raise ValueError(f"Insufficient Ni atoms for Al substitution. Required: {num_al_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices, num_al_sub)
            for idx in sub_indices:
                al_super[idx] = "Al"
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "al0p5cocrfeni_super.cif"
                al_super.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                al_super_file = get_unique_filename(conn, "al0p5cocrfeni_super.cif", "CIF")
                save_to_db(conn, al_super_file, "CIF", data)
                st.success(f"Created {al_super_file}")

                temp_file = pathlib.Path(td) / "al0p5cocrfeni_super.xsf"
                al_super.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "al0p5cocrfeni_super.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 7: Mirror across Y=0 with wrapping
            al_mirror = al_super.copy()
            frac_coords = al_mirror.frac_coords
            frac_coords[:, 1] = (-frac_coords[:, 1]) % 1.0  # Mirror across Y=0 and wrap
            al_mirror = Structure(al_mirror.lattice, al_mirror.species, frac_coords, coords_are_cartesian=False)
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "al0p5cocrfeni_mirror.cif"
                al_mirror.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                mirror_file = get_unique_filename(conn, "al0p5cocrfeni_mirror.cif", "CIF")
                save_to_db(conn, mirror_file, "CIF", data)
                st.success(f"Created {mirror_file}")

            # Step 8: Merge original and mirrored structures along Y
            cell_mat = al_super.lattice.matrix
            cell_mat[1, :] *= 2  # Double Y lattice vector
            super_lattice = Lattice(cell_mat)
            base_frac = al_super.frac_coords
            mirrored_frac = al_mirror.frac_coords
            mirrored_frac[:, 1] = (mirrored_frac[:, 1] + 0.5) % 1.0  # Shift to top half
            combined_coords = np.vstack([base_frac, mirrored_frac])
            combined_species = al_super.species + al_mirror.species
            merged_structure = Structure(super_lattice, combined_species, combined_coords, coords_are_cartesian=False)
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "al0p5cocrfeni_nanotwin.cif"
                merged_structure.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                nanotwin_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.cif", "CIF")
                save_to_db(conn, nanotwin_file, "CIF", data)
                st.success(f"Created {nanotwin_file}")

                temp_file = pathlib.Path(td) / "al0p5cocrfeni_nanotwin.xsf"
                merged_structure.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

        except Exception as e:
            st.error(f"Error during structure generation: {e}")
            raise
        finally:
            conn.close()

# -------------------- Visualization Section -------------------- #
st.header("Visualize Structure")
try:
    conn = init_db()
    c = conn.cursor()
    c.execute("SELECT filename, format, data FROM structures WHERE data IS NOT NULL AND length(data) > 0")
    files = c.fetchall()
    conn.close()

    if not files:
        st.info("No structures available for visualization.")
    else:
        file_options = [filename for filename, format, _ in files if format in ["CIF", "XSF"]]
        selected_file = st.selectbox("Select a structure to visualize", file_options)
        if selected_file:
            with st.spinner("Loading visualization..."):
                conn = init_db()
                c = conn.cursor()
                c.execute("SELECT format, data FROM structures WHERE filename = ?", (selected_file,))
                format, data = c.fetchone()
                conn.close()

                with tempfile.TemporaryDirectory() as td:
                    temp_file = pathlib.Path(td) / f"temp.{format.lower()}"
                    with open(temp_file, "wb") as f:
                        f.write(data)
                    structure = Structure.from_file(temp_file)
                    visualize_structure(structure, format=format.lower())

except Exception as e:
    st.error(f"Error loading visualization: {e}")

# -------------------- Downloads -------------------- #
display_download_section()
