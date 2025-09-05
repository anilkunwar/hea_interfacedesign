import streamlit as st
import sqlite3
import numpy as np
import polars as pl
from atomlib import make, Atoms, AtomCell
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
            return proposed_filename  # Unique filename found
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

def visualize_structure(atoms, format="cif"):
    """
    Visualize an atomlib Atoms object using py3Dmol.
    """
    try:
        with tempfile.TemporaryDirectory() as td:
            temp_file = pathlib.Path(td) / f"temp.{format}"
            if format == "cif":
                atoms.write_cif(temp_file)
            elif format == "xsf":
                atoms.write_xsf(temp_file)
            with open(temp_file, "r") as f:
                data = f.read()
            view = py3Dmol.view(width=600, height=400)
            view.addModel(data, format)
            view.setStyle({"sphere": {"radius": 0.5}})
            view.addUnitCell()
            view.zoomTo()
            st.components.v1.html(view._make_html(), width=600, height=400)
    except Exception as e:
        st.error(f"Error visualizing structure: {e}")

# -------------------- Streamlit UI -------------------- #
st.title("Crystal Structure Generator (Al0.5CoCrFeNi Nanotwin)")

# Clean database at startup to remove empty entries
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
            # Step 1: FCC Ni unit cell with [11-2], [111], [-110] orientation
            try:
                st.write(f"Attempting to create FCC Ni with element 'Ni'")
                ni_unit = make.fcc(a, "Ni")  # Try with "Ni"
            except Exception as e:
                st.warning(f"Failed with 'Ni': {e}. Trying lowercase 'ni'.")
                try:
                    ni_unit = make.fcc(a, "ni")  # Try lowercase
                except Exception as e:
                    st.warning(f"Failed with 'ni': {e}. Trying atomic number 28.")
                    ni_unit = make.fcc(a, 28)  # Try atomic number for Ni

            # Apply orientation transformation: [11-2], [111], [-110]
            orientation_matrix = np.array([
                [1, 1, -2],  # X aligns with [11-2]
                [1, 1, 1],   # Y aligns with [111]
                [-1, 1, 0]   # Z aligns with [-110]
            ])
            new_cell = ni_unit.cell.transform(orientation_matrix)
            ni_unit = AtomCell(ni_unit.atoms, new_cell)
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "ni_unit.xsf"
                ni_unit.write_xsf(temp_file)
                xsf_str = temp_file.read_bytes()
                ni_unit_file = get_unique_filename(conn, "ni_unit.xsf", "XSF")
                save_to_db(conn, ni_unit_file, "XSF", xsf_str)
                st.success(f"Created {ni_unit_file}")

                # Save CFG for ni_unit
                temp_file = pathlib.Path(td) / "ni_unit.cfg"
                ni_unit.write_cfg(temp_file)
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "ni_unit.cfg", "CFG")
                save_to_db(conn, cfg_file, "CFG", data)
                st.success(f"Created {cfg_file}")

            # Step 2: Supercell
            ni_super = ni_unit.replicate((nx, ny, nz))
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "ni_super.xsf"
                ni_super.write_xsf(temp_file)
                xsf_str = temp_file.read_bytes()
                ni_super_file = get_unique_filename(conn, "ni_super.xsf", "XSF")
                save_to_db(conn, ni_super_file, "XSF", xsf_str)
                st.success(f"Created {ni_super_file}")

                # Save CFG
                temp_file = pathlib.Path(td) / "ni_super.cfg"
                ni_super.write_cfg(temp_file)
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "ni_super.cfg", "CFG")
                save_to_db(conn, cfg_file, "CFG", data)
                st.success(f"Created {cfg_file}")

            # Step 3: Substitute Ni → Fe
            feni_super = ni_super.copy()
            num_atoms = len(feni_super.atoms)
            num_sub = int(num_atoms * m / 100)
            ni_indices = feni_super.atoms.filter(pl.col("element") == "Ni").index
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Fe substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices.tolist(), num_sub)
            feni_super.atoms = feni_super.atoms.with_columns(
                pl.when(pl.col("index").is_in(sub_indices))
                .then(pl.lit("Fe"))
                .otherwise(pl.col("element"))
                .alias("element")
            )
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "feni_super.xsf"
                feni_super.write_xsf(temp_file)
                xsf_str = temp_file.read_bytes()
                feni_super_file = get_unique_filename(conn, "feni_super.xsf", "XSF")
                save_to_db(conn, feni_super_file, "XSF", xsf_str)
                st.success(f"Created {feni_super_file}")

                # Save CFG
                temp_file = pathlib.Path(td) / "feni_super.cfg"
                feni_super.write_cfg(temp_file)
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "feni_super.cfg", "CFG")
                save_to_db(conn, cfg_file, "CFG", data)
                st.success(f"Created {cfg_file}")

            # Step 4: Substitute Ni → Cr
            crfeni_super = feni_super.copy()
            ni_indices = crfeni_super.atoms.filter(pl.col("element") == "Ni").index
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Cr substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices.tolist(), num_sub)
            crfeni_super.atoms = crfeni_super.atoms.with_columns(
                pl.when(pl.col("index").is_in(sub_indices))
                .then(pl.lit("Cr"))
                .otherwise(pl.col("element"))
                .alias("element")
            )
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "crfeni_super.xsf"
                crfeni_super.write_xsf(temp_file)
                xsf_str = temp_file.read_bytes()
                crfeni_super_file = get_unique_filename(conn, "crfeni_super.xsf", "XSF")
                save_to_db(conn, crfeni_super_file, "XSF", xsf_str)
                st.success(f"Created {crfeni_super_file}")

                # Save CFG
                temp_file = pathlib.Path(td) / "crfeni_super.cfg"
                crfeni_super.write_cfg(temp_file)
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "crfeni_super.cfg", "CFG")
                save_to_db(conn, cfg_file, "CFG", data)
                st.success(f"Created {cfg_file}")

            # Step 5: Substitute Ni → Co
            cocrfeni_super = crfeni_super.copy()
            ni_indices = cocrfeni_super.atoms.filter(pl.col("element") == "Ni").index
            if len(ni_indices) < num_sub:
                raise ValueError(f"Insufficient Ni atoms for Co substitution. Required: {num_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices.tolist(), num_sub)
            cocrfeni_super.atoms = cocrfeni_super.atoms.with_columns(
                pl.when(pl.col("index").is_in(sub_indices))
                .then(pl.lit("Co"))
                .otherwise(pl.col("element"))
                .alias("element")
            )
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "cocrfeni_super.xsf"
                cocrfeni_super.write_xsf(temp_file)
                xsf_str = temp_file.read_bytes()
                cocrfeni_super_file = get_unique_filename(conn, "cocrfeni_super.xsf", "XSF")
                save_to_db(conn, cocrfeni_super_file, "XSF", xsf_str)
                st.success(f"Created {cocrfeni_super_file}")

                # Save CFG
                temp_file = pathlib.Path(td) / "cocrfeni_super.cfg"
                cocrfeni_super.write_cfg(temp_file)
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "cocrfeni_super.cfg", "CFG")
                save_to_db(conn, cfg_file, "CFG", data)
                st.success(f"Created {cfg_file}")

            # Step 6: Substitute Ni → Al
            al_super = cocrfeni_super.copy()
            ni_indices = al_super.atoms.filter(pl.col("element") == "Ni").index
            num_al_sub = int(num_atoms * n / 100)
            if len(ni_indices) < num_al_sub:
                raise ValueError(f"Insufficient Ni atoms for Al substitution. Required: {num_al_sub}, Available: {len(ni_indices)}")
            sub_indices = random.sample(ni_indices.tolist(), num_al_sub)
            al_super.atoms = al_super.atoms.with_columns(
                pl.when(pl.col("index").is_in(sub_indices))
                .then(pl.lit("Al"))
                .otherwise(pl.col("element"))
                .alias("element")
            )
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "al0p5cocrfeni_super.xsf"
                al_super.write_xsf(temp_file)
                xsf_str = temp_file.read_bytes()
                al_super_file = get_unique_filename(conn, "al0p5cocrfeni_super.xsf", "XSF")
                save_to_db(conn, al_super_file, "XSF", xsf_str)
                st.success(f"Created {al_super_file}")

                # Save CFG
                temp_file = pathlib.Path(td) / "al0p5cocrfeni_super.cfg"
                al_super.write_cfg(temp_file)
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "al0p5cocrfeni_super.cfg", "CFG")
                save_to_db(conn, cfg_file, "CFG", data)
                st.success(f"Created {cfg_file}")

            # Step 7: Mirror across Y=0 with wrapping
            al_mirror = al_super.copy()
            frac_coords = al_mirror.atoms.select(["x", "y", "z"]).to_numpy()
            frac_coords[:, 1] = (-frac_coords[:, 1]) % 1.0  # Mirror across Y=0 and wrap to [0,1)
            al_mirror.atoms = al_mirror.atoms.with_columns(
                pl.DataFrame(frac_coords, schema=["x", "y", "z"])
            )
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "al0p5cocrfeni_mirror.xsf"
                al_mirror.write_xsf(temp_file)
                xsf_str = temp_file.read_bytes()
                mirror_file = get_unique_filename(conn, "al0p5cocrfeni_mirror.xsf", "XSF")
                save_to_db(conn, mirror_file, "XSF", xsf_str)
                st.success(f"Created {mirror_file}")

            # Step 8: Merge original and mirrored structures along Y
            cell_mat = al_super.cell.to_matrix()
            cell_mat[1, :] *= 2  # Double Y lattice vector
            super_cell = al_super.cell.from_matrix(cell_mat)
            base_frac = al_super.atoms.select(["x", "y", "z"]).to_numpy()
            mirrored_frac = al_mirror.atoms.select(["x", "y", "z"]).to_numpy()
            mirrored_frac[:, 1] = (mirrored_frac[:, 1] + 0.5) % 1.0  # Shift to top half
            base_atoms = al_super.atoms.select(["element"])
            mirrored_atoms = al_mirror.atoms.select(["element"])
            combined_coords = np.vstack([base_frac, mirrored_frac])
            combined_elements = pl.concat([
                base_atoms,
                mirrored_atoms
            ])
            merged_atoms = pl.DataFrame({
                "element": combined_elements["element"],
                "x": combined_coords[:, 0],
                "y": combined_coords[:, 1],
                "z": combined_coords[:, 2]
            })
            merged_structure = AtomCell(Atoms(merged_atoms), super_cell)
            with tempfile.TemporaryDirectory() as td:
                temp_file = pathlib.Path(td) / "al0p5cocrfeni_nanotwin.xsf"
                merged_structure.write_xsf(temp_file)
                xsf_str = temp_file.read_bytes()
                nanotwin_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.xsf", "XSF")
                save_to_db(conn, nanotwin_file, "XSF", xsf_str)
                st.success(f"Created {nanotwin_file}")

                # Save CFG for nanotwin
                temp_file = pathlib.Path(td) / "al0p5cocrfeni_nanotwin.cfg"
                merged_structure.write_cfg(temp_file)
                data = temp_file.read_bytes()
                cfg_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.cfg", "CFG")
                save_to_db(conn, cfg_file, "CFG", data)
                st.success(f"Created {cfg_file}")

                # Save CIF for nanotwin
                temp_file = pathlib.Path(td) / "al0p5cocrfeni_nanotwin.cif"
                merged_structure.write_cif(temp_file)
                data = temp_file.read_bytes()
                cif_file = get_unique_filename(conn, "al0p5cocrfeni_nanotwin.cif", "CIF")
                save_to_db(conn, cif_file, "CIF", data)
                st.success(f"Created {cif_file}")

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
        file_options = [filename for filename, format, _ in files if format in ["XSF", "CIF"]]
        selected_file = st.selectbox("Select a structure to visualize", file_options)
        if selected_file:
            with st.spinner("Loading visualization..."):
                # Retrieve the selected file's data
                conn = init_db()
                c = conn.cursor()
                c.execute("SELECT format, data FROM structures WHERE filename = ?", (selected_file,))
                format, data = c.fetchone()
                conn.close()

                # Convert data to atomlib Atoms for visualization
                with tempfile.TemporaryDirectory() as td:
                    temp_file = pathlib.Path(td) / f"temp.{format.lower()}"
                    with open(temp_file, "wb") as f:
                        f.write(data)
                    if format == "CIF":
                        atoms = AtomCell.read_cif(temp_file)
                    elif format == "XSF":
                        atoms = AtomCell.read_xsf(temp_file)
                    visualize_structure(atoms, format=format.lower())

except Exception as e:
    st.error(f"Error loading visualization: {e}")

# -------------------- Downloads -------------------- #
display_download_section()
