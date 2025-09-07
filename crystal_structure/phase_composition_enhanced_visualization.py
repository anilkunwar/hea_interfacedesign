import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import os
import logging
from io import StringIO

# Logging setup
script_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(script_dir, 'visual_app.log'),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Default data (only used as last resort)
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

# Load CSV
@st.cache_data
def load_data(uploaded_file=None, local_path=None, github_url=None):
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            logger.info("Loaded uploaded CSV file")
            return df, "Uploaded CSV"
        if local_path and os.path.exists(local_path):
            df = pd.read_csv(local_path)
            logger.info(f"Loaded local CSV file: {local_path}")
            return df, f"Local file: {local_path}"
        if github_url:
            df = pd.read_csv(github_url)
            logger.info(f"Loaded GitHub CSV file: {github_url}")
            return df, f"GitHub URL: {github_url}"

        # Only use default data if no other source is available
        logger.warning("No valid CSV file provided; using default data")
        df = pd.read_csv(StringIO(default_data))
        return df, "Default data"

    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        logger.exception(f"Failed to load CSV: {e}")
        return None, None

# Validate data
def validate_data(df):
    required_columns = ['mpea', 'structure', 'xAl', 'xNi', 'xCr', 'xCo', 'xFe']
    if not all(col in df.columns for col in required_columns):
        missing = set(required_columns) - set(df.columns)
        st.error(f"CSV missing required columns: {', '.join(missing)}")
        logger.error(f"CSV missing required columns: {', '.join(missing)}")
        return False

    # Ensure numeric values
    for col in ['xAl', 'xNi', 'xCr', 'xCo', 'xFe']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if df[col].isnull().any():
            st.error(f"Column '{col}' contains non-numeric or NaN values")
            logger.error(f"Column '{col}' contains non-numeric or NaN values")
            return False

    # Validate mpea format
    for mpea in df['mpea']:
        try:
            float(mpea.split('Al')[1].split('Co')[0])
        except:
            st.error(f"Invalid alloy name format: {mpea}")
            logger.error(f"Invalid alloy name format: {mpea}")
            return False

    return True

# Assign color values based on structure and y
def get_color_values(df):
    color_values = []
    for _, row in df.iterrows():
        alloy_name = row['mpea']
        structure = row['structure']
        try:
            y = float(alloy_name.split('Al')[1].split('Co')[0])
        except:
            return None  # Error already logged in validate_data
        if structure == 'FCC':
            color_values.append(1.0)
        elif structure == 'BCC':
            color_values.append(0.0)
        else:  # FCC+BCC
            color_values.append(1.0 - (y - 0.5) / 0.5)
    return color_values

# Normalize ternary coordinates
def normalize_ternary(df):
    df_copy = df.copy()
    total = df_copy['xAl'] + df_copy['xCo'] + df_copy['xCr'] + df_copy['xFe'] + df_copy['xNi']
    df_copy['p_Al_norm'] = df_copy['xAl'] / total
    df_copy['p_CoCr_norm'] = (df_copy['xCo'] + df_copy['xCr']) / total
    df_copy['p_FeNi_norm'] = (df_copy['xFe'] + df_copy['xNi']) / total
    return df_copy

# Get colormap options
@st.cache_data
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

# Convert Matplotlib colormap to Plotly colorscale
@st.cache_data
def matplotlib_to_plotly_colormap(cmap_name, n_colors=256):
    try:
        cmap = cm.get_cmap(cmap_name)
        colors = [mcolors.rgb2hex(cmap(i / (n_colors - 1))) for i in range(n_colors)]
        return [[i / (n_colors - 1), color] for i, color in enumerate(colors)]
    except ValueError as e:
        logger.error(f"Invalid colormap: {cmap_name}, {e}")
        return matplotlib_to_plotly_colormap('viridis')

# Create ternary plot
def create_ternary_plot(df, color_values, colormap, marker_size, line_thickness, grid_thickness, show_grid, font_size, al_label, cocr_label, feni_label, axis_color, grid_color, label_color, title_spacing):
    plotly_colorscale = matplotlib_to_plotly_colormap(colormap)
    fig = go.Figure()

    fig.add_trace(
        go.Scatterternary(
            a=df['p_Al_norm'],
            b=df['p_CoCr_norm'],
            c=df['p_FeNi_norm'],
            mode='markers',
            marker=dict(
                size=marker_size,
                color=color_values,
                colorscale=plotly_colorscale,
                showscale=True,
                colorbar=dict(title="Structure<br>(1=FCC, 0=BCC)", thickness=20),
                cmin=0,
                cmax=1
            ),
            text=df['mpea'],
            customdata=df[['structure']].values,
            hovertemplate=(
                "Alloy: %{text}<br>"
                "Phase: %{customdata[0]}<br>"
                "Al: %{a:.3f}<br>"
                "Co+Cr: %{b:.3f}<br>"
                "Fe+Ni: %{c:.3f}"
            )
        )
    )

    fig.update_ternaries(
        sum=1,
        aaxis=dict(
            title=dict(text=al_label, font=dict(size=font_size, color=label_color)),
            tickfont=dict(size=font_size, color=label_color),
            linewidth=line_thickness,
            linecolor=axis_color,
            gridcolor=grid_color if show_grid else None
        ),
        baxis=dict(
            title=dict(text=cocr_label, font=dict(size=font_size, color=label_color)),
            tickfont=dict(size=font_size, color=label_color),
            linewidth=line_thickness,
            linecolor=axis_color,
            gridcolor=grid_color if show_grid else None
        ),
        caxis=dict(
            title=dict(text=feni_label, font=dict(size=font_size, color=label_color)),
            tickfont=dict(size=font_size, color=label_color),
            linewidth=line_thickness,
            linecolor=axis_color,
            gridcolor=grid_color if show_grid else None
        ),
        bgcolor="white"
    )

    fig.update_layout(
        title=dict(
            text="Ternary Diagram of AlyCoCrFeNi Alloy",
            font=dict(size=font_size + 4),
            y=1 - title_spacing / 100
        ),
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50)
    )

    return fig

# Main app
def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with customizable options.")

    # Data source selection
    st.subheader("Data Source")
    data_source = st.radio("Select data source:", ["Upload CSV", "Local File", "GitHub URL", "Default Data"])
    st.write(f"Selected data source: {data_source}")

    df = None
    data_source_info = None
    if data_source == "Upload CSV":
        uploaded_file = st.file_uploader("Upload CSV file", type="csv")
        if uploaded_file:
            df, data_source_info = load_data(uploaded_file=uploaded_file)
    elif data_source == "Local File":
        local_file = st.text_input("Enter local CSV file name (in adjacent directory)", "AlyCoCrFeNi_data.csv")
        local_path = os.path.join(os.path.dirname(__file__), "..", local_file)
        df, data_source_info = load_data(local_path=local_path)
    elif data_source == "GitHub URL":
        github_url = st.text_input("Enter GitHub raw CSV URL", "")
        if github_url:
            df, data_source_info = load_data(github_url=github_url)
    else:
        df, data_source_info = load_data()

    if df is None or not validate_data(df):
        st.error("Failed to load a valid CSV file. Please check the file and try again.")
        st.stop()

    st.success(f"Data loaded from: {data_source_info}")
    st.write("Loaded Data:")
    st.dataframe(df)

    # Normalize ternary coordinates
    df = normalize_ternary(df)

    # Color values
    color_values = get_color_values(df)
    if color_values is None:
        st.error("Failed to process color values due to invalid alloy names.")
        st.stop()

    # Sidebar customization
    st.sidebar.header("Plot Customization")
    colormap = st.sidebar.selectbox("Select Colormap", get_colormap_options(), index=0)
    line_thickness = st.sidebar.slider("Axis Line Thickness", 0.5, 5.0, 2.0, 0.1)
    grid_thickness = st.sidebar.slider("Grid Line Thickness", 0.1, 2.0, 0.5, 0.1)
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    font_size = st.sidebar.slider("Font Size (Labels & Ticks)", 8, 20, 12, 1)
    marker_size = st.sidebar.slider("Marker Size", 4, 20, 8, 1)
    axis_color = st.sidebar.color_picker("Axis Color", "#000000")
    grid_color = st.sidebar.color_picker("Grid Color", "#888888")
    label_color = st.sidebar.color_picker("Label Color", "#000000")
    title_spacing = st.sidebar.slider("Title-Vertex Spacing", 0, 100, 30, 1)
    al_label = st.sidebar.text_input("Al Vertex Label", "Al")
    cocr_label = st.sidebar.text_input("CoCr Vertex Label", "Co+Cr")
    feni_label = st.sidebar.text_input("FeNi Vertex Label", "Fe+Ni")

    # Create and display plot
    fig = create_ternary_plot(
        df, color_values, colormap, marker_size, line_thickness, grid_thickness,
        show_grid, font_size, al_label, cocr_label, feni_label,
        axis_color, grid_color, label_color, title_spacing
    )
    st.plotly_chart(fig, use_container_width=True)

    # Download CSV
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Loaded CSV",
        data=csv,
        file_name="AlyCoCrFeNi_data.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
