import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os
import logging

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

# === Main App ===
def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with customizable options.")

    # --- Data source ---
    uploaded_file = st.file_uploader("Upload CSV file (optional)", type="csv")

    # Default CSV in the same folder as this script
    default_file = os.path.join(script_dir, "AlyCoCrFeNi_data.csv")

    # Load data
    df = load_data(file_path=default_file, uploaded_file=uploaded_file)
    if df is None:
        st.stop()

    # Normalize ternary coordinates
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

    al_label = st.sidebar.text_input("Al Vertex Label", "Al")
    cocr_label = st.sidebar.text_input("CoCr Vertex Label", "Co+Cr")
    feni_label = st.sidebar.text_input("FeNi Vertex Label", "Fe+Ni")

    # --- Plot ---
    fig = go.Figure()
    fig.add_trace(
        go.Scatterternary(
            a=df['p_Al_norm'],
            b=df['p_CoCr_norm'],
            c=df['p_FeNi_norm'],
            mode="markers",
            marker=dict(
                size=8,
                color=color_values,
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Structure<br>(1=FCC, 0=BCC)", thickness=20),
                cmin=0,
                cmax=1
            ),
            text=df['mpea'],
            customdata=df[['structure']].values,  # phase info
            hovertemplate=(
                "Alloy: %{text}<br>"
                "Phase: %{customdata[0]}<br>"
                "Al: %{a:.3f}<br>"
                "Co+Cr: %{b:.3f}<br>"
                "Fe+Ni: %{c:.3f}"
            )
        )
    )

    # --- Layout ---
    fig.update_layout(
        title=dict(
            text="Ternary Diagram of AlyCoCrFeNi Alloy",
            font=dict(size=font_size + 2)
        ),
        ternary=dict(
            sum=1,
            aaxis=dict(
                title=dict(text=al_label, font=dict(size=font_size)),
                tickfont=dict(size=font_size),
                linewidth=line_thickness,
                gridwidth=grid_thickness if show_grid else 0
            ),
            baxis=dict(
                title=dict(text=cocr_label, font=dict(size=font_size)),
                tickfont=dict(size=font_size),
                linewidth=line_thickness,
                gridwidth=grid_thickness if show_grid else 0
            ),
            caxis=dict(
                title=dict(text=feni_label, font=dict(size=font_size)),
                tickfont=dict(size=font_size),
                linewidth=line_thickness,
                gridwidth=grid_thickness if show_grid else 0
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
