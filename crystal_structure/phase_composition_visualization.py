import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import os
from io import StringIO

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
def load_data(uploaded_file=None, local_path=None, github_url=None):
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        elif local_path and os.path.exists(local_path):
            df = pd.read_csv(local_path)
        elif github_url:
            df = pd.read_csv(github_url)
        else:
            df = pd.read_csv(StringIO(default_data))
        
        # Verify required columns
        required_columns = ['mpea', 'structure', 'xAl', 'xNi', 'xCr', 'xCo', 'xFe']
        if not all(col in df.columns for col in required_columns):
            st.error("CSV must contain columns: mpea, structure, xAl, xNi, xCr, xCo, xFe")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None

# Function to assign color values based on structure and y
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
            color_values.append(1.0 - (y - 0.5) / 0.5)
    return color_values

# Function to get colormap options
def get_colormap_options():
    return sorted([
        'viridis', 'plasma', 'inferno', 'magma', 'hot', 'cool', 'rainbow', 'jet',
        'blues', 'greens', 'reds', 'purples', 'oranges', 'greys', 'YlOrRd', 'YlGnBu',
        'RdBu', 'Spectral', 'PiYG', 'PRGn', 'BrBG', 'PuOr', 'RdGy', 'RdYlBu', 'RdYlGn',
        'Accent', 'Dark2', 'Paired', 'Pastel1', 'Pastel2', 'Set1', 'Set2', 'Set3',
        'tab10', 'tab20', 'tab20b', 'tab20c', 'viridis_r', 'plasma_r', 'inferno_r',
        'magma_r', 'hot_r', 'cool_r', 'rainbow_r', 'jet_r', 'blues_r', 'greens_r',
        'reds_r', 'purples_r', 'oranges_r', 'greys_r', 'YlOrRd_r', 'YlGnBu_r', 'RdBu_r'
    ])

# Function to convert Matplotlib colormap to Plotly colorscale
def matplotlib_to_plotly_colormap(cmap_name, n_colors=256):
    cmap = cm.get_cmap(cmap_name)
    colors = [mcolors.rgb2hex(cmap(i / (n_colors - 1))) for i in range(n_colors)]
    return [[i / (n_colors - 1), color] for i, color in enumerate(colors)]

def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with customizable options.")

    # File input options
    st.subheader("Data Source")
    data_source = st.radio("Select data source:", ["Default Data", "Upload CSV", "Local File", "GitHub URL"])

    df = None
    if data_source == "Upload CSV":
        uploaded_file = st.file_uploader("Upload CSV file", type="csv")
        df = load_data(uploaded_file=uploaded_file)
    elif data_source == "Local File":
        local_path = st.text_input("Enter local CSV file name (in adjacent directory)", "AlyCoCrFeNi_data.csv")
        full_path = os.path.join(os.path.dirname(__file__), "..", local_path)
        df = load_data(local_path=full_path)
    elif data_source == "GitHub URL":
        github_url = st.text_input("Enter GitHub raw CSV URL", "")
        df = load_data(github_url=github_url)
    else:
        df = load_data()

    if df is None:
        st.stop()

    # Display data
    st.write("Loaded Data:")
    st.dataframe(df)

    # Calculate ternary coordinates
    df['p_Al'] = df['xAl']
    df['p_CoCr'] = df['xCo'] + df['xCr']
    df['p_FeNi'] = df['xFe'] + df['xNi']

    # Get color values
    color_values = get_color_values(df)
    if color_values is None:
        st.stop()

    # Sidebar for customization
    st.sidebar.header("Plot Customization")
    colormap = st.sidebar.selectbox("Select Colormap", get_colormap_options(), index=0)
    line_thickness = st.sidebar.slider("Ternary Line Thickness", 0.5, 5.0, 2.0, 0.1)
    grid_thickness = st.sidebar.slider("Grid Line Thickness", 0.1, 2.0, 0.5, 0.1)
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    font_size = st.sidebar.slider("Font Size (Labels & Ticks)", 8, 20, 12, 1)
    al_label = st.sidebar.text_input("Al Vertex Label", "Al")
    cocr_label = st.sidebar.text_input("CoCr Vertex Label", "Co+Cr")
    feni_label = st.sidebar.text_input("FeNi Vertex Label", "Fe+Ni")

    # Convert Matplotlib colormap to Plotly colorscale
    plotly_colorscale = matplotlib_to_plotly_colormap(colormap)

    # Create ternary plot
    fig = go.Figure()

    # Add scatter points
    fig.add_trace(
        go.Scatterternary(
            a=df['p_Al'],
            b=df['p_CoCr'],
            c=df['p_FeNi'],
            mode='markers',
            marker=dict(
                size=8,
                color=color_values,
                colorscale=plotly_colorscale,
                showscale=True,
                colorbar=dict(title="Structure<br>(1=FCC, 0=BCC)", thickness=20),
                cmin=0,
                cmax=1
            ),
            text=df['mpea'],
            hovertemplate="Alloy: %{text}<br>Al: %{a:.3f}<br>Co+Cr: %{b:.3f}<br>Fe+Ni: %{c:.3f}"
        )
    )

    # Update layout
    fig.update_ternaries(
        aaxis=dict(
            title=al_label,
            titlefont=dict(size=font_size),
            tickfont=dict(size=font_size),
            linewidth=line_thickness,
            gridwidth=grid_thickness if show_grid else 0
        ),
        baxis=dict(
            title=cocr_label,
            titlefont=dict(size=font_size),
            tickfont=dict(size=font_size),
            linewidth=line_thickness,
            gridwidth=grid_thickness if show_grid else 0
        ),
        caxis=dict(
            title=feni_label,
            titlefont=dict(size=font_size),
            tickfont=dict(size=font_size),
            linewidth=line_thickness,
            gridwidth=grid_thickness if show_grid else 0
        )
    )

    # Update layout for better appearance
    fig.update_layout(
        title="Ternary Diagram of AlyCoCrFeNi Alloy",
        ternary=dict(
            sum=1,
            bgcolor="white"
        ),
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50)
    )

    # Display plot
    st.plotly_chart(fig, use_container_width=True)

    # Provide CSV download
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Loaded CSV",
        data=csv,
        file_name="AlyCoCrFeNi_data.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
