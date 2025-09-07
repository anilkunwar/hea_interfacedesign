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

# === Colormap options ===
def get_colormap_options():
    cmaps = [
        'viridis','plasma','inferno','magma','cividis','jet','rainbow','hot','cool','spring','summer','autumn','winter',
        'bone','copper','pink','prism','flag','ocean','gist_earth','terrain','gnuplot','gnuplot2','CMRmap',
        'cubehelix','brg','gist_rainbow','nipy_spectral','spectral','twilight','twilight_shifted','turbo','mako','rocket',
        'magma_r','viridis_r','plasma_r','inferno_r','cividis_r','cividis','turbo_r','gist_ncar','terrain_r'
    ]
    return sorted(cmaps)

# === Main App ===
def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with enhanced customization options.")

    # --- Data source ---
    uploaded_file = st.file_uploader("Upload CSV file (optional)", type="csv")
    default_file = os.path.join(script_dir, "AlyCoCrFeNi_data.csv")
    df = load_data(file_path=default_file, uploaded_file=uploaded_file)
    if df is None:
        st.stop()

    st.write("Loaded Data:")
    st.dataframe(df)

    # --- Ternary coordinates ---
    df['p_Al'] = df['xAl']
    df['p_CoCr'] = df['xCo'] + df['xCr']
    df['p_FeNi'] = df['xFe'] + df['xNi']

    # --- Color mapping ---
    color_values = get_color_values(df)

    # --- Sidebar customization ---
    st.sidebar.header("Plot Customization")
    line_thickness = float(st.sidebar.slider("Axis Line Thickness", 0.5, 5.0, 2.0, 0.1))
    grid_thickness = float(st.sidebar.slider("Grid Line Thickness", 0.1, 2.0, 0.5, 0.1))
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    font_size = int(st.sidebar.slider("Font Size (Vertices & Ticks)", 8, 100, 40, 1))
    title_font_size = int(st.sidebar.slider("Graph Title Font Size", 10, 30, 16, 1))
    title_label_space = float(st.sidebar.slider("Title to Vertex Label Space", 0.1, 0.5, 0.25, 0.01))

    al_label = st.sidebar.text_input("Al Vertex Label", "Al")
    cocr_label = st.sidebar.text_input("CoCr Vertex Label", "Co+Cr")
    feni_label = st.sidebar.text_input("FeNi Vertex Label", "Fe+Ni")

    label_color = st.sidebar.color_picker("Vertex Label Color", "#000000")
    axis_line_color = st.sidebar.color_picker("Axis Line Color", "#000000")
    curve_color = st.sidebar.color_picker("Curve/Marker Edge Color", "#000000")

    colormap = st.sidebar.selectbox("Select Colormap for Structure", get_colormap_options(), index=0)
    use_colormap = st.sidebar.checkbox("Use Colormap (unchecked uses uniform color)", value=True)
    uniform_color = st.sidebar.color_picker("Uniform Marker Color", "#1f77b4")

    # --- Plot ---
    fig = go.Figure()

    if use_colormap:
        cmap = cm.get_cmap(colormap)
        marker_colors = [mcolors.rgb2hex(cmap(val)) for val in color_values]
    else:
        marker_colors = [uniform_color for _ in color_values]

    fig.add_trace(
        go.Scatterternary(
            a=df['p_Al'],
            b=df['p_CoCr'],
            c=df['p_FeNi'],
            mode="markers",
            marker=dict(
                size=10,
                color=marker_colors,
                line=dict(color=curve_color, width=1),
                showscale=use_colormap,
                colorbar=dict(title="Structure<br>(1=FCC,0=BCC)", thickness=20) if use_colormap else None,
            ),
            text=df.apply(lambda row: f"{row['mpea']} ({row['structure']})", axis=1),
            hovertemplate="Alloy: %{text}<br>Al: %{a:.3f}<br>Co+Cr: %{b:.3f}<br>Fe+Ni: %{c:.3f}"
        )
    )

    fig.update_layout(
        title=dict(
            text="Ternary Diagram of AlyCoCrFeNi Alloy",
            font=dict(size=title_font_size),
            x=0.5,
            xanchor='center',
            yanchor='top'
        ),
        ternary=dict(
            sum=1,
            aaxis=dict(
                title=dict(text=al_label, font=dict(size=font_size, color=label_color)),
                tickfont=dict(size=font_size, color=label_color),
                linewidth=line_thickness,
                linecolor=axis_line_color,
                gridwidth=grid_thickness if show_grid else 0,
                minor=dict(ticklen=2)
            ),
            baxis=dict(
                title=dict(text=cocr_label, font=dict(size=font_size, color=label_color)),
                tickfont=dict(size=font_size, color=label_color),
                linewidth=line_thickness,
                linecolor=axis_line_color,
                gridwidth=grid_thickness if show_grid else 0,
                minor=dict(ticklen=2)
            ),
            caxis=dict(
                title=dict(text=feni_label, font=dict(size=font_size, color=label_color)),
                tickfont=dict(size=font_size, color=label_color),
                linewidth=line_thickness,
                linecolor=axis_line_color,
                gridwidth=grid_thickness if show_grid else 0,
                minor=dict(ticklen=2)
            ),
            bgcolor="white",
        ),
        margin=dict(l=50, r=50, t=int(80 + title_label_space*100), b=50),
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True)

    # --- Download CSV ---
    csv = df.to_csv(index=False)
    st.download_button("Download Loaded CSV", csv, "AlyCoCrFeNi_data.csv", "text/csv")

if __name__ == "__main__":
    main()
