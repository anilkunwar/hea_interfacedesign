import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# Load CSV
@st.cache_data
def load_data(file_path=None, uploaded_file=None):
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        elif file_path is not None and os.path.exists(file_path):
            df = pd.read_csv(file_path)
        else:
            st.error("No valid data source found.")
            return None

        required_columns = ['mpea', 'structure', 'xAl', 'xNi', 'xCr', 'xCo', 'xFe']
        if not all(col in df.columns for col in required_columns):
            st.error("CSV must contain columns: mpea, structure, xAl, xNi, xCr, xCo, xFe")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading CSV: {e}")
        return None

# Assign color values
def get_color_values(df):
    return [
        1.0 if row['structure'] == 'FCC' else
        0.0 if row['structure'] == 'BCC' else 0.5
        for _, row in df.iterrows()
    ]

def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with customizable options.")

    # === Data source ===
    uploaded_file = st.file_uploader("Upload CSV file (optional)", type="csv")

    # Default local file
    default_file = os.path.join(os.getcwd(), "AlyCoCrFeNi_data.csv")

    # Load priority: uploaded > local
    df = load_data(file_path=default_file, uploaded_file=uploaded_file)
    if df is None:
        st.stop()

    st.write("Loaded Data:")
    st.dataframe(df)

    # === Ternary coordinates ===
    df['p_Al'] = df['xAl']
    df['p_CoCr'] = df['xCo'] + df['xCr']
    df['p_FeNi'] = df['xFe'] + df['xNi']

    # Check for NaN or infinite values in ternary coordinates
    if df[['p_Al', 'p_CoCr', 'p_FeNi']].isnull().any().any() or not df[['p_Al', 'p_CoCr', 'p_FeNi']].applymap(lambda x: pd.notnull(x) and pd.api.types.is_number(x)).all().all():
        st.error("Data contains NaN or non-numeric values in ternary coordinates.")
        st.stop()

    color_values = get_color_values(df)

    # === Sidebar ===
    st.sidebar.header("Plot Customization")
    line_thickness = float(st.sidebar.slider("Axis Line Thickness", 0.5, 5.0, 2.0, 0.1))
    grid_thickness = float(st.sidebar.slider("Grid Line Thickness", 0.1, 2.0, 0.5, 0.1))
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    font_size = int(st.sidebar.slider("Font Size", 8, 20, 12, 1))

    al_label = st.sidebar.text_input("Al Vertex Label", "Al")
    cocr_label = st.sidebar.text_input("CoCr Vertex Label", "Co+Cr")
    feni_label = st.sidebar.text_input("FeNi Vertex Label", "Fe+Ni")

    # === Plot ===
    fig = go.Figure()

    fig.add_trace(
        go.Scatterternary(
            a=df['p_Al'],
            b=df['p_CoCr'],
            c=df['p_FeNi'],
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
            hovertemplate="Alloy: %{text}<br>Al: %{a:.3f}<br>Co+Cr: %{b:.3f}<br>Fe+Ni: %{c:.3f}"
        )
    )

    # Correct ternary layout
    fig.update_layout(
        title=dict(
            text="Ternary Diagram of AlyCoCrFeNi Alloy",
            font=dict(size=font_size+2)
        ),
        ternary=dict(
            sum=1,
            aaxis=dict(
                title=al_label,
                linewidth=line_thickness,
                gridwidth=grid_thickness if show_grid else 0,
                titlefont=dict(size=font_size),
                tickfont=dict(size=font_size)
            ),
            baxis=dict(
                title=cocr_label,
                linewidth=line_thickness,
                gridwidth=grid_thickness if show_grid else 0,
                titlefont=dict(size=font_size),
                tickfont=dict(size=font_size)
            ),
            caxis=dict(
                title=feni_label,
                linewidth=line_thickness,
                gridwidth=grid_thickness if show_grid else 0,
                titlefont=dict(size=font_size),
                tickfont=dict(size=font_size)
            ),
            bgcolor="white"
        ),
        showlegend=False,
        margin=dict(l=50, r=50, t=80, b=50)
    )

    st.plotly_chart(fig, use_container_width=True)

    # CSV download
    csv = df.to_csv(index=False)
    st.download_button("Download Loaded CSV", csv, "AlyCoCrFeNi_data.csv", "text/csv")

if __name__ == "__main__":
    main()
