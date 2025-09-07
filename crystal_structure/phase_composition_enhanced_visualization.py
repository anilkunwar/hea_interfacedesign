import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import os
import logging

# --- Logging setup ---
script_dir = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(
    level=logging.INFO,
    filename=os.path.join(script_dir, 'visual_app.log'),
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Load CSV ---
@st.cache_data
def load_data(uploaded_file=None, local_path=None):
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
            logger.info("Loaded uploaded CSV file")
            return df
        if local_path and os.path.exists(local_path):
            df = pd.read_csv(local_path)
            logger.info(f"Loaded local CSV file: {local_path}")
            return df
        st.error("No valid CSV file provided. Please upload a CSV or ensure the local file exists.")
        logger.warning("No valid CSV file provided")
        return None
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        logger.exception(f"Failed to load CSV: {e}")
        return None

# --- Validate CSV data ---
def validate_data(df):
    required_columns = ['mpea', 'structure', 'xAl', 'xNi', 'xCr', 'xCo', 'xFe']
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        st.error(f"CSV missing required columns: {', '.join(missing)}")
        logger.error(f"CSV missing required columns: {', '.join(missing)}")
        return False

    for col in ['xAl', 'xNi', 'xCr', 'xCo', 'xFe']:
        df[col] = pd.to_numeric(df[col], errors='coerce')
        if df[col].isnull().any():
            st.error(f"Column '{col}' contains non-numeric or NaN values")
            logger.error(f"Column '{col}' contains non-numeric or NaN values")
            return False
    return True

# --- Assign color values based on structure ---
def get_color_values(df):
    color_values = []
    for _, row in df.iterrows():
        structure = row['structure']
        if structure == 'FCC':
            color_values.append(1.0)
        elif structure == 'BCC':
            color_values.append(0.0)
        else:
            color_values.append(0.5)
    return color_values

# --- Normalize ternary coordinates ---
def normalize_ternary(df):
    total = df['xAl'] + df['xCo'] + df['xCr'] + df['xFe'] + df['xNi']
    df['p_Al'] = df['xAl'] / total
    df['p_CoCr'] = (df['xCo'] + df['xCr']) / total
    df['p_FeNi'] = (df['xFe'] + df['xNi']) / total
    return df

# --- Colormap options ---
def get_colormap_options():
    return sorted([
        'viridis','plasma','inferno','magma','hot','cool','rainbow','jet',
        'blues','greens','reds','purples','oranges','greys','YlOrRd','YlGnBu',
        'RdBu','Spectral','PiYG','PRGn','BrBG','PuOr','RdGy','RdYlBu','RdYlGn',
        'Accent','Dark2','Paired','Pastel1','Pastel2','Set1','Set2','Set3',
        'tab10','tab20','tab20b','tab20c','viridis_r','plasma_r','inferno_r',
        'magma_r','hot_r','cool_r','rainbow_r','jet_r','blues_r','greens_r',
        'reds_r','purples_r','oranges_r','greys_r','YlOrRd_r','YlGnBu_r','RdBu_r'
    ])

# --- Convert Matplotlib colormap to Plotly colorscale ---
@st.cache_data
def matplotlib_to_plotly_colormap(cmap_name, n_colors=256):
    try:
        cmap = cm.get_cmap(cmap_name)
        colors = [mcolors.rgb2hex(cmap(i / (n_colors - 1))) for i in range(n_colors)]
        return [[i / (n_colors - 1), color] for i, color in enumerate(colors)]
    except ValueError:
        logger.error(f"Invalid colormap {cmap_name}, fallback to viridis")
        return matplotlib_to_plotly_colormap('viridis')

# --- Create ternary plot ---
def create_ternary_plot(df, color_values, colormap, marker_size, line_thickness, grid_thickness, show_grid, font_size, al_label, cocr_label, feni_label, axis_color, grid_color, label_color, title_spacing, fig_width, fig_height, colorbar_xpad, colorbar_title_font_size):
    colorscale = matplotlib_to_plotly_colormap(colormap)
    fig = go.Figure()

    fig.add_trace(go.Scatterternary(
        a=df['p_Al'],
        b=df['p_CoCr'],
        c=df['p_FeNi'],
        mode='markers',
        marker=dict(
            size=marker_size,
            color=color_values,
            colorscale=colorscale,
            showscale=True,
            colorbar=dict(
                title=dict(
                    text="Structure (1=FCC,0=BCC)",
                    font=dict(size=colorbar_title_font_size)
                ),
                thickness=20,
                xpad=colorbar_xpad,
                tickfont=dict(size=font_size)
            ),
            cmin=0, cmax=1
        ),
        text=df['mpea'],
        customdata=df[['structure']],
        hovertemplate="Alloy: %{text}<br>Phase: %{customdata[0]}<br>Al: %{a:.3f}<br>Co+Cr: %{b:.3f}<br>Fe+Ni: %{c:.3f}"
    ))

    fig.update_ternaries(
        sum=1,
        aaxis=dict(title=dict(text=al_label, font=dict(size=font_size, color=label_color)),
                   tickfont=dict(size=font_size, color=label_color),
                   linewidth=line_thickness, linecolor=axis_color,
                   gridcolor=grid_color if show_grid else None, gridwidth=grid_thickness),
        baxis=dict(title=dict(text=cocr_label, font=dict(size=font_size, color=label_color)),
                   tickfont=dict(size=font_size, color=label_color),
                   linewidth=line_thickness, linecolor=axis_color,
                   gridcolor=grid_color if show_grid else None, gridwidth=grid_thickness),
        caxis=dict(title=dict(text=feni_label, font=dict(size=font_size, color=label_color)),
                   tickfont=dict(size=font_size, color=label_color),
                   linewidth=line_thickness, linecolor=axis_color,
                   gridcolor=grid_color if show_grid else None, gridwidth=grid_thickness),
        bgcolor='white'
    )

    fig.update_layout(
        title=dict(text="Ternary Diagram of AlyCoCrFeNi Alloy", font=dict(size=font_size+4), pad=dict(t=title_spacing)),
        width=fig_width,
        height=fig_height,
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50)
    )

    return fig

# --- Main app ---
def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize AlyCoCrFeNi alloy compositions with customizable ternary plot.")

    # --- Data source ---
    uploaded_file = st.file_uploader("Upload CSV (optional)", type="csv")
    default_file = os.path.join(script_dir, "AlyCoCrFeNi_data.csv")

    # Load priority: uploaded > local
    df = load_data(uploaded_file=uploaded_file, local_path=default_file)
    if df is None or not validate_data(df):
        st.error("Failed to load a valid CSV file. Please provide a valid CSV.")
        st.stop()

    df = normalize_ternary(df)
    color_values = get_color_values(df)

    # --- Sidebar customization ---
    st.sidebar.header("Plot Customization")
    colormap = st.sidebar.selectbox("Select Colormap", get_colormap_options(), index=0)
    line_thickness = st.sidebar.slider("Axis Line Thickness", 0.5, 5.0, 2.0, 0.1)
    grid_thickness = st.sidebar.slider("Grid Line Thickness", 0.1, 5.0, 0.5, 0.1)
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    font_size = st.sidebar.slider("Font Size (Labels & Ticks)", 8, 20, 12, 1)
    colorbar_title_font_size = st.sidebar.slider("Colorbar Title Font Size", 8, 24, 16, 1)
    marker_size = st.sidebar.slider("Marker Size", 4, 20, 8, 1)
    axis_color = st.sidebar.color_picker("Axis Color", "#000000")
    grid_color = st.sidebar.color_picker("Grid Color", "#888888")
    label_color = st.sidebar.color_picker("Label Color", "#000000")
    title_spacing = st.sidebar.slider("Title-Vertex Spacing (px)", 0, 100, 30, 1)
    colorbar_xpad = st.sidebar.slider("Colorbar Padding (px)", 0, 50, 20, 1)
    fig_width = st.sidebar.slider("Figure Width (px)", 400, 1200, 700, 50)
    fig_height = st.sidebar.slider("Figure Height (px)", 400, 1200, 700, 50)
    al_label = st.sidebar.text_input("Al Vertex Label", "Al")
    cocr_label = st.sidebar.text_input("CoCr Vertex Label", "Co+Cr")
    feni_label = st.sidebar.text_input("FeNi Vertex Label", "Fe+Ni")

    # --- Plot ---
    fig = create_ternary_plot(df, color_values, colormap, marker_size, line_thickness, grid_thickness,
                              show_grid, font_size, al_label, cocr_label, feni_label,
                              axis_color, grid_color, label_color, title_spacing,
                              fig_width, fig_height, colorbar_xpad, colorbar_title_font_size)
    st.plotly_chart(fig, use_container_width=True)

    # --- Download CSV ---
    csv = df.to_csv(index=False)
    st.download_button("Download CSV", csv, "AlyCoCrFeNi_data.csv", "text/csv")

if __name__ == "__main__":
    main()
