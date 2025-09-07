import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
from io import StringIO
import os

# Default data
default_data = """mpea,structure,xAl,xNi,xCr,xCo,xFe
Al0.000CoCrFeNi,FCC,0.0,0.25,0.25,0.25,0.25
Al0.100CoCrFeNi,FCC,0.0244,0.2439,0.2439,0.2439,0.2439
Al0.200CoCrFeNi,FCC,0.0476,0.2381,0.2381,0.2381,0.2381
Al0.300CoCrFeNi,FCC,0.0698,0.2326,0.2326,0.2326,0.2326
Al0.400CoCrFeNi,FCC,0.0909,0.2273,0.2273,0.2273,0.2273
Al0.500CoCrFeNi,FCC,0.1111,0.2222,0.2222,0.2222,0.2222
Al0.600CoCrFeNi,FCC+BCC,0.1304,0.2174,0.2174,0.2174,0.2174
Al0.700CoCrFeNi,FCC+BCC,0.1489,0.2128,0.2128,0.2128,0.2128
Al0.800CoCrFeNi,FCC+BCC,0.1667,0.2083,0.2083,0.2083,0.2083
Al0.900CoCrFeNi,FCC+BCC,0.1837,0.2041,0.2041,0.2041,0.2041
Al1.000CoCrFeNi,FCC+BCC,0.2,0.2,0.2,0.2,0.2
Al1.100CoCrFeNi,BCC,0.2157,0.1961,0.1961,0.1961,0.1961
Al1.200CoCrFeNi,BCC,0.2308,0.1923,0.1923,0.1923,0.1923
Al1.300CoCrFeNi,BCC,0.2453,0.1887,0.1887,0.1887,0.1887
Al1.400CoCrFeNi,BCC,0.2593,0.1852,0.1852,0.1852,0.1852
Al1.500CoCrFeNi,BCC,0.2727,0.1818,0.1818,0.1818,0.1818"""

# Function to load data
@st.cache_data
def load_data(source="default", uploaded_file=None, local_file=None, github_url=None):
    try:
        if source == "upload" and uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        elif source == "local" and local_file is not None and os.path.exists(local_file):
            df = pd.read_csv(local_file)
        elif source == "github" and github_url is not None:
            df = pd.read_csv(github_url)
        else:
            df = pd.read_csv(StringIO(default_data))
        
        required_columns = ['mpea', 'structure', 'xAl', 'xNi', 'xCr', 'xCo', 'xFe']
        if not all(col in df.columns for col in required_columns):
            st.error("CSV must contain columns: mpea, structure, xAl, xNi, xCr, xCo, xFe")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None

# Function to assign color values based on structure
def get_color_values(df):
    color_values = []
    for _, row in df.iterrows():
        alloy_name = row['mpea']
        structure = row['structure']
        try:
            y = float(alloy_name.split('Al')[1].split('Co')[0])
        except:
            st.error(f"Invalid alloy name format: {alloy_name}")
            return None
        if structure == 'FCC':
            color_values.append(1.0)
        elif structure == 'BCC':
            color_values.append(0.0)
        else:  # FCC+BCC
            color_values.append(0.5)
    return color_values

def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with customizable options.")

    # Data source selection
    source = st.radio("Select data source:", ["Default Data", "Upload CSV", "Local File", "GitHub URL"])
    uploaded_file = None
    local_file = None
    github_url = None

    if source == "Upload CSV":
        uploaded_file = st.file_uploader("Upload CSV file", type="csv")
        df = load_data("upload", uploaded_file=uploaded_file)
    elif source == "Local File":
        local_file = st.text_input("Enter local CSV filename:", "local_data.csv")
        df = load_data("local", local_file=local_file)
    elif source == "GitHub URL":
        github_url = st.text_input("Enter GitHub raw CSV URL:")
        df = load_data("github", github_url=github_url)
    else:
        df = load_data("default")

    if df is None:
        st.stop()

    st.write("Loaded Data:")
    st.dataframe(df)

    # Compute ternary coordinates
    df['p_Al'] = df['xAl']
    df['p_CoCr'] = df['xCo'] + df['xCr']
    df['p_FeNi'] = df['xFe'] + df['xNi']

    # Get colors
    color_values = get_color_values(df)
    if color_values is None:
        st.stop()

    # Sidebar customization
    st.sidebar.header("Plot Customization")
    colormap = st.sidebar.selectbox("Select Colormap", ['viridis', 'plasma', 'inferno', 'magma', 'rainbow'], index=0)
    line_thickness = st.sidebar.slider("Axis Line Thickness", 0.5, 5.0, 2.0, 0.1)
    grid_thickness = st.sidebar.slider("Grid Line Thickness", 0.1, 2.0, 0.5, 0.1)
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    font_size = st.sidebar.slider("Font Size", 8, 20, 12, 1)

    # Axis labels
    al_label = st.sidebar.text_input("Al Vertex Label", "Al")
    cocr_label = st.sidebar.text_input("CoCr Vertex Label", "Co+Cr")
    feni_label = st.sidebar.text_input("FeNi Vertex Label", "Fe+Ni")

    # Build figure
    fig = go.Figure()

    fig.add_trace(
        go.Scatterternary(
            a=df['p_Al'],
            b=df['p_CoCr'],
            c=df['p_FeNi'],
            mode='markers',
            marker=dict(
                size=8,
                color=color_values,
                colorscale=colormap,
                showscale=True,
                colorbar=dict(title="Structure (1=FCC, 0=BCC)", thickness=20),
                cmin=0,
                cmax=1
            ),
            text=df['mpea'],
            hovertemplate="Alloy: %{text}<br>Al: %{a:.3f}<br>Co+Cr: %{b:.3f}<br>Fe+Ni: %{c:.3f}"
        )
    )

    # Update ternary layout
    fig.update_layout(
        title="Ternary Diagram of AlyCoCrFeNi Alloy",
        ternary=dict(
            sum=1,
            aaxis=dict(title=al_label, linewidth=line_thickness,
                       gridwidth=grid_thickness if show_grid else 0,
                       titlefont=dict(size=font_size), tickfont=dict(size=font_size)),
            baxis=dict(title=cocr_label, linewidth=line_thickness,
                       gridwidth=grid_thickness if show_grid else 0,
                       titlefont=dict(size=font_size), tickfont=dict(size=font_size)),
            caxis=dict(title=feni_label, linewidth=line_thickness,
                       gridwidth=grid_thickness if show_grid else 0,
                       titlefont=dict(size=font_size), tickfont=dict(size=font_size)),
            bgcolor="white"
        ),
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50)
    )

    st.plotly_chart(fig, use_container_width=True)

    # CSV download option
    csv = df.to_csv(index=False)
    st.download_button("Download Loaded CSV", csv, "AlyCoCrFeNi_data.csv", "text/csv")

if __name__ == "__main__":
    main()
