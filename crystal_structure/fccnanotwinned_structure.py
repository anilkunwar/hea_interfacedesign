import streamlit as st
import sqlite3
import numpy as np
from pymatgen.core import Lattice, Structure
from collections import Counter
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

def visualize_structure(structure, format="cif", mirror_axis="Y"):
    """
    Visualize a pymatgen Structure object using py3Dmol with twin plane.
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
            # Add twin plane at midpoint of selected axis
            lattice = structure.lattice
            if mirror_axis == "X":
                mid = lattice.a / 2
                vertices = [[mid, 0, 0], [mid, lattice.b, 0], [mid, lattice.b, lattice.c], [mid, 0, lattice.c]]
            elif mirror_axis == "Z":
                mid = lattice.c / 2
                vertices = [[0, 0, mid], [lattice.a, 0, mid], [lattice.a, lattice.b, mid], [0, lattice.b, mid]]
            else:  # Y
                mid = lattice.b / 2
                vertices = [[0, mid, 0], [lattice.a, mid, 0], [lattice.a, mid, lattice.c], [0, mid, lattice.c]]
            view.addSurface("VDW", {"color": "yellow", "opacity": 0.3}, {"vertex": vertices})
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

# Crystal Type
st.header("Crystal Type")
crystal_type = st.selectbox("Select crystal type", ["FCC", "BCC", "BCT", "HCP"], index=0)

# Lattice Constants
st.header("Lattice Constants")
col1, col2 = st.columns(2)
with col1:
    a = st.number_input("Lattice constant a (Å)", value=3.54, min_value=0.1, format="%.2f")
with col2:
    if crystal_type in ["BCT", "HCP"]:
        c = st.number_input("Lattice constant c (Å)", value=5.78, min_value=0.1, format="%.2f")
    else:
        c = None

# Orientation Matrix
st.header("Orientation Matrix ([hkl] for X, Y, Z)")
col1, col2, col3 = st.columns(3)
with col1:
    x_h = st.number_input("X [h]", value=1, step=1, format="%d", key="x_h")
    x_k = st.number_input("X [k]", value=1, step=1, format="%d", key="x_k")
    x_l = st.number_input("X [l]", value=-2, step=1, format="%d", key="x_l")
with col2:
    y_h = st.number_input("Y [h]", value=1, step=1, format="%d", key="y_h")
    y_k = st.number_input("Y [k]", value=1, step=1, format="%d", key="y_k")
    y_l = st.number_input("Y [l]", value=1, step=1, format="%d", key="y_l")
with col3:
    z_h = st.number_input("Z [h]", value=-1, step=1, format="%d", key="z_h")
    z_k = st.number_input("Z [k]", value=1, step=1, format="%d", key="z_k")
    z_l = st.number_input("Z [l]", value=0, step=1, format="%d", key="z_l")

# Supercell Multipliers
st.header("Supercell Multipliers")
col1, col2, col3 = st.columns(3)
with col1:
    nx = st.number_input("nx", value=10, min_value=1, step=1, format="%d")
with col2:
    ny = st.number_input("ny", value=7, min_value=1, step=1, format="%d")
with col3:
    nz = st.number_input("nz", value=10, min_value=1, step=1, format="%d")

# Substitution Percentages
st.header("Substitution Percentages")
m = st.number_input("Major element substitution percentage (%) (Fe, Cr, Co)", value=22.22, min_value=0.0, max_value=100.0, format="%.2f")
n = st.number_input("Dopant (Al) substitution percentage (%)", value=11.12, min_value=0.0, max_value=100.0, format="%.2f")

# Mirror Axis
st.header("Mirror Axis")
mirror_axis = st.selectbox("Select mirror axis", ["X", "Y", "Z"], index=1)

# Validate inputs
if (3 * m + n) > 100:
    st.error("Total substitution percentage (3 * m + n) exceeds 100%. Please adjust m and n.")
    st.stop()

orientation_matrix = np.array([
    [x_h, x_k, x_l],
    [y_h, y_k, y_l],
    [z_h, z_k, z_l]
], dtype=float)
if abs(np.linalg.det(orientation_matrix)) < 1e-5:
    st.error("Orientation matrix is not valid (determinant near zero). Please choose orthogonal directions.")
    st.stop()

# -------------------- Structure Generation -------------------- #
if st.button("Generate Structures"):
    with st.spinner("Generating structures..."):
        try:
            # Step 1: Create unit cell based on crystal type
            if crystal_type == "FCC":
                lattice = Lattice.cubic(a)
                coords = [[0, 0, 0], [0.5, 0.5, 0], [0.5, 0, 0.5], [0, 0.5, 0.5]]
                species = ["Ni"] * 4
            elif crystal_type == "BCC":
                lattice = Lattice.cubic(a)
                coords = [[0, 0, 0], [0.5, 0.5, 0.5]]
                species = ["Ni"] * 2
            elif crystal_type == "BCT":
                lattice = Lattice.tetragonal(a, c)
                coords = [[0, 0, 0], [0.5, 0.5, 0.5]]
                species = ["Ni"] * 2
            elif crystal_type == "HCP":
                lattice = Lattice.hexagonal(a, c)
                coords = [[0, 0, 0], [1/3, 2/3, 0.5]]
                species = ["Ni"] * 2

            unit_cell = Structure(lattice, species, coords, coords_are_cartesian=False)
            st.write(f"Created {crystal_type} Ni unit cell with {len(unit_cell)} atoms")

            # Apply orientation
            new_lattice = Lattice(np.dot(orientation_matrix, unit_cell.lattice.matrix))
            unit_cell = Structure(new_lattice, unit_cell.species, unit_cell.frac_coords, coords_are_cartesian=False)
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / f"ni_unit_{crystal_type.lower()}.cif"
                unit_cell.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                unit_file = get_unique_filename(conn, f"ni_unit_{crystal_type.lower()}.cif", "CIF")
                save_to_db(conn, unit_file, "CIF", data)
                st.success(f"Created {unit_file}")

                temp_file = pathlib.Path(td) / f"ni_unit_{crystal_type.lower()}.xsf"
                unit_cell.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, f"ni_unit_{crystal_type.lower()}.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 2: Supercell
            super_cell = unit_cell * (nx, ny, nz)
            atom_counts = Counter(str(s) for s in super_cell.species)
            st.write(f"Supercell atom counts: {atom_counts['Ni']} Ni (Total: {len(super_cell)} atoms)")
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / f"ni_super_{crystal_type.lower()}.cif"
                super_cell.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                super_file = get_unique_filename(conn, f"ni_super_{crystal_type.lower()}.cif", "CIF")
                save_to_db(conn, super_file, "CIF", data)
                st.success(f"Created {super_file}")

                temp_file = pathlib.Path(td) / f"ni_super_{crystal_type.lower()}.xsf"
                super_cell.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, f"ni_super_{crystal_type.lower()}.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 3: Substitute Ni → Fe
            feni_super = super_cell.copy()
            num_atoms = len(feni_super)
            num_sub = int(num_atoms * m / 100)
            ni_indices = [i for i, s in enumerate(feni_super.species) if s.symbol == "Ni"]
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Fe substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices, num_sub)
            for idx in sub_indices:
                feni_super[idx] = "Fe"
            atom_counts = Counter(str(s) for s in feni_super.species)
            st.write(f"Fe substitution atom counts: {atom_counts['Ni']} Ni, {atom_counts['Fe']} Fe (Total: {len(feni_super)} atoms)")
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / f"feni_super_{crystal_type.lower()}.cif"
                feni_super.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                feni_super_file = get_unique_filename(conn, f"feni_super_{crystal_type.lower()}.cif", "CIF")
                save_to_db(conn, feni_super_file, "CIF", data)
                st.success(f"Created {feni_super_file}")

                temp_file = pathlib.Path(td) / f"feni_super_{crystal_type.lower()}.xsf"
                feni_super.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, f"feni_super_{crystal_type.lower()}.xsf", "XSF")
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
            atom_counts = Counter(str(s) for s in crfeni_super.species)
            st.write(f"Cr substitution atom counts: {atom_counts['Ni']} Ni, {atom_counts['Fe']} Fe, {atom_counts['Cr']} Cr (Total: {len(crfeni_super)} atoms)")
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / f"crfeni_super_{crystal_type.lower()}.cif"
                crfeni_super.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                crfeni_super_file = get_unique_filename(conn, f"crfeni_super_{crystal_type.lower()}.cif", "CIF")
                save_to_db(conn, crfeni_super_file, "CIF", data)
                st.success(f"Created {crfeni_super_file}")

                temp_file = pathlib.Path(td) / f"crfeni_super_{crystal_type.lower()}.xsf"
                crfeni_super.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, f"crfeni_super_{crystal_type.lower()}.xsf", "XSF")
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
            atom_counts = Counter(str(s) for s in cocrfeni_super.species)
            st.write(f"Co substitution atom counts: {atom_counts['Ni']} Ni, {atom_counts['Fe']} Fe, {atom_counts['Cr']} Cr, {atom_counts['Co']} Co (Total: {len(cocrfeni_super)} atoms)")
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / f"cocrfeni_super_{crystal_type.lower()}.cif"
                cocrfeni_super.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                cocrfeni_super_file = get_unique_filename(conn, f"cocrfeni_super_{crystal_type.lower()}.cif", "CIF")
                save_to_db(conn, cocrfeni_super_file, "CIF", data)
                st.success(f"Created {cocrfeni_super_file}")

                temp_file = pathlib.Path(td) / f"cocrfeni_super_{crystal_type.lower()}.xsf"
                cocrfeni_super.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, f"cocrfeni_super_{crystal_type.lower()}.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cocrfeni_super_file}")

            # Step 6: Substitute Ni → Al
            al_super = cocrfeni_super.copy()
            ni_indices = [i for i, s in enumerate(al_super.species) if s.symbol == "Ni"]
            num_al_sub = int(num_atoms * n / 100)
            if len(ni_indices) < num_al_sub:
                raise ValueError(f"Insufficient Ni atoms for Al substitution. Required: {num_al_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices, num_al_sub)
            for idx in sub_indices:
                al_super[idx] = "Al"
            atom_counts = Counter(str(s) for s in al_super.species)
            st.write(f"Al substitution atom counts: {atom_counts['Ni']} Ni, {atom_counts['Fe']} Fe, {atom_counts['Cr']} Cr, {atom_counts['Co']} Co, {atom_counts['Al']} Al (Total: {len(al_super)} atoms)")
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / f"al0p5cocrfeni_super_{crystal_type.lower()}.cif"
                al_super.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                al_super_file = get_unique_filename(conn, f"al0p5cocrfeni_super_{crystal_type.lower()}.cif", "CIF")
                save_to_db(conn, al_super_file, "CIF", data)
                st.success(f"Created {al_super_file}")

                temp_file = pathlib.Path(td) / f"al0p5cocrfeni_super_{crystal_type.lower()}.xsf"
                al_super.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, f"al0p5cocrfeni_super_{crystal_type.lower()}.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 7: Mirror across selected axis
            al_mirror = al_super.copy()
            frac_coords = al_mirror.frac_coords.copy()
            axis_idx = {"X": 0, "Y": 1, "Z": 2}[mirror_axis]
            frac_coords[:, axis_idx] = (-frac_coords[:, axis_idx]) % 1.0  # Mirror and wrap
            al_mirror = Structure(al_mirror.lattice, al_mirror.species, frac_coords, coords_are_cartesian=False)
            atom_counts = Counter(str(s) for s in al_mirror.species)
            st.write(f"Mirrored structure atom counts: {atom_counts['Ni']} Ni, {atom_counts['Fe']} Fe, {atom_counts['Cr']} Cr, {atom_counts['Co']} Co, {atom_counts['Al']} Al (Total: {len(al_mirror)} atoms)")
            mirror_coords = al_mirror.frac_coords[:, axis_idx]
            st.write(f"{mirror_axis} fractional coordinates range: min={mirror_coords.min():.3f}, max={mirror_coords.max():.3f}")
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / f"al0p5cocrfeni_mirror_{crystal_type.lower()}.cif"
                al_mirror.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                mirror_file = get_unique_filename(conn, f"al0p5cocrfeni_mirror_{crystal_type.lower()}.cif", "CIF")
                save_to_db(conn, mirror_file, "CIF", data)
                st.success(f"Created {mirror_file}")

                temp_file = pathlib.Path(td) / f"al0p5cocrfeni_mirror_{crystal_type.lower()}.xsf"
                al_mirror.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, f"al0p5cocrfeni_mirror_{crystal_type.lower()}.xsf", "XSF")
                save_to_db(conn, cfg_file, "XSF", data)
                st.success(f"Created {cfg_file}")

            # Step 8: Merge original and mirrored structures along selected axis
            cell_mat = al_super.lattice.matrix.copy()
            cell_mat[axis_idx, :] *= 2
            super_lattice = Lattice(cell_mat)
            base_frac = al_super.frac_coords
            mirrored_frac = al_mirror.frac_coords
            mirrored_frac[:, axis_idx] = (mirrored_frac[:, axis_idx] + 0.5) % 1.0
            combined_coords = np.vstack([base_frac, mirrored_frac])
            combined_species = al_super.species + al_mirror.species
            merged_structure = Structure(super_lattice, combined_species, combined_coords, coords_are_cartesian=False)
            atom_counts = Counter(str(s) for s in merged_structure.species)
            st.write(f"Nanotwin atom counts: {atom_counts['Ni']} Ni, {atom_counts['Fe']} Fe, {atom_counts['Cr']} Cr, {atom_counts['Co']} Co, {atom_counts['Al']} Al (Total: {len(merged_structure)} atoms)")
            nanotwin_coords = merged_structure.frac_coords[:, axis_idx]
            st.write(f"Nanotwin {mirror_axis} fractional coordinates range: min={nanotwin_coords.min():.3f}, max={nanotwin_coords.max():.3f}")
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / f"al0p5cocrfeni_nanotwin_{crystal_type.lower()}.cif"
                merged_structure.to(filename=temp_file, fmt="cif")
                data = temp_file.read_bytes()
                nanotwin_file = get_unique_filename(conn, f"al0p5cocrfeni_nanotwin_{crystal_type.lower()}.cif", "CIF")
                save_to_db(conn, nanotwin_file, "CIF", data)
                st.success(f"Created {nanotwin_file}")

                temp_file = pathlib.Path(td) / f"al0p5cocrfeni_nanotwin_{crystal_type.lower()}.xsf"
                merged_structure.to(filename=temp_file, fmt="xsf")
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, f"al0p5cocrfeni_nanotwin_{crystal_type.lower()}.xsf", "XSF")
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
                    visualize_structure(structure, format=format.lower(), mirror_axis=mirror_axis)

except Exception as e:
    st.error(f"Error loading visualization: {e}")

# -------------------- Downloads -------------------- #
display_download_section()
