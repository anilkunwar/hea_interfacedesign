import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import logging
import matplotlib.cm as cm
import matplotlib.colors as mcolors

# === Logging setup ===
script_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(script_dir, 'visual_app.log'),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === Load CSV ===
@st.cache_data
def load_data(file_path=None, uploaded_file=None):
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            logger.info("Loaded uploaded CSV file")
        elif file_path is not None and os.path.exists(file_path):
            df = pd.read_csv(file_path)
            logger.info(f"Loaded default CSV file: {file_path}")
        else:
            st.error("No valid data source found. Please upload a CSV file.")
            logger.warning("No CSV file found")
            return None

        required_columns = ['mpea', 'structure', 'xAl', 'xNi', 'xCr', 'xCo', 'xFe']
        if not all(col in df.columns for col in required_columns):
            st.error(f"CSV must contain columns: {', '.join(required_columns)}")
            logger.error("CSV missing required columns")
            return None

        # Ensure numeric values
        for col in ['xAl','xNi','xCr','xCo','xFe']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        if df[['xAl','xNi','xCr','xCo','xFe']].isnull().any().any():
            st.error("CSV contains non-numeric or NaN values")
            logger.error("CSV contains NaN or non-numeric values")
            return None

        return df

    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        logger.exception("Failed to load CSV")
        return None

# === Color values based on structure ===
def get_color_values(df):
    color_values = []
    for _, row in df.iterrows():
        struct = row['structure']
        if struct == 'FCC':
            color_values.append(1.0)
        elif struct == 'BCC':
            color_values.append(0.0)
        else:  # FCC+BCC or other
            color_values.append(0.5)
    return color_values

# === Normalize ternary coordinates ===
def normalize_ternary(df):
    total = df['xAl'] + df['xCo'] + df['xCr'] + df['xFe'] + df['xNi']
    df['p_Al_norm'] = df['xAl'] / total
    df['p_CoCr_norm'] = (df['xCo'] + df['xCr']) / total
    df['p_FeNi_norm'] = (df['xFe'] + df['xNi']) / total
    return df

# === Get colormap options ===
def get_colormap_options():
    cmaps = list(mcolors.CSS4_COLORS.keys()) + [
        'viridis','plasma','inferno','magma','cividis','jet','rainbow','hot','cool','spring','summer','autumn','winter',
        'bone','copper','pink','prism','flag','ocean','gist_earth','terrain','gist_stern','gnuplot','gnuplot2','CMRmap',
        'cubehelix','brg','gist_rainbow','rainbow','jet_r','gist_ncar','nipy_spectral','spectral','viridis_r','plasma_r'
    ]
    return sorted(list(set(cmaps)))

# === Main App ===
def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with customizable options.")

    # --- Data source ---
    uploaded_file = st.file_uploader("Upload CSV file (optional)", type="csv")
    default_file = os.path.join(script_dir, "AlyCoCrFeNi_data.csv")
    df = load_data(file_path=default_file, uploaded_file=uploaded_file)
    if df is None:
        st.stop()

    df = normalize_ternary(df)
    st.write("Loaded Data:")
    st.dataframe(df)

    # --- Color mapping ---
    color_values = get_color_values(df)

    # --- Sidebar customization ---
    st.sidebar.header("Plot Customization")
    line_thickness = float(st.sidebar.slider("Axis Line Thickness", 0.5, 5.0, 2.0, 0.1))
    grid_thickness = float(st.sidebar.slider("Grid Line Thickness", 0.1, 2.0, 0.5, 0.1))
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    font_size = int(st.sidebar.slider("Font Size", 8, 20, 12, 1))
    marker_size = int(st.sidebar.slider("Marker Size", 4, 20, 8, 1))

    al_label = st.sidebar.text_input("Al Vertex Label", "Al")
    cocr_label = st.sidebar.text_input("CoCr Vertex Label", "Co+Cr")
    feni_label = st.sidebar.text_input("FeNi Vertex Label", "Fe+Ni")

    # --- Color and curve customization ---
    colormap = st.sidebar.selectbox("Marker Colormap", get_colormap_options(), index=0)
    axis_color = st.sidebar.color_picker("Axis Color", "#000000")
    grid_color = st.sidebar.color_picker("Grid Color", "#888888")
    label_color = st.sidebar.color_picker("Label Color", "#000000")
    title_spacing = float(st.sidebar.slider("Title-Vertex Spacing", 0, 100, 30, 1))

    # --- Plot ---
    cmap = cm.get_cmap(colormap)
    marker_colors = [mcolors.rgb2hex(cmap(val)) for val in color_values]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterternary(
            a=df['p_Al_norm'],
            b=df['p_CoCr_norm'],
            c=df['p_FeNi_norm'],
            mode="markers",
            marker=dict(
                size=marker_size,
                color=marker_colors,
                showscale=True,
                colorbar=dict(title="Structure (1=FCC,0=BCC)", thickness=20)
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

    fig.update_layout(
        title=dict(
            text="Ternary Diagram of AlyCoCrFeNi Alloy",
            font=dict(size=font_size + 4),
            y=1-title_spacing/100  # Adjust spacing between title and plot
        ),
        ternary=dict(
            sum=1,
            aaxis=dict(
                title=dict(text=al_label, font=dict(size=font_size, color=label_color)),
                tickfont=dict(size=font_size, color=label_color),
                linewidth=line_thickness,
                gridcolor=grid_color if show_grid else None,
                linecolor=axis_color
            ),
            baxis=dict(
                title=dict(text=cocr_label, font=dict(size=font_size, color=label_color)),
                tickfont=dict(size=font_size, color=label_color),
                linewidth=line_thickness,
                gridcolor=grid_color if show_grid else None,
                linecolor=axis_color
            ),
            caxis=dict(
                title=dict(text=feni_label, font=dict(size=font_size, color=label_color)),
                tickfont=dict(size=font_size, color=label_color),
                linewidth=line_thickness,
                gridcolor=grid_color if show_grid else None,
                linecolor=axis_color
            ),
            bgcolor="white"
        ),
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50)
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Download CSV ---
    csv = df.to_csv(index=False)
    st.download_button("Download Loaded CSV", csv, "AlyCoCrFeNi_data.csv", "text/csv")

if __name__ == "__main__":
    main()
