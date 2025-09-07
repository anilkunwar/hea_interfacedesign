import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import os

# Function to load data
@st.cache_data
def load_data(uploaded_file=None, local_file=None):
    try:
        if uploaded_file is not None:
            df = pd.read_csv(uploaded_file)
        elif local_file is not None and os.path.exists(local_file):
            df = pd.read_csv(local_file)
        else:
            st.error("No valid data source found.")
            return None

        # Verify required columns
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
        if row['structure'] == 'FCC':
            color_values.append(1.0)
        elif row['structure'] == 'BCC':
            color_values.append(0.0)
        else:  # FCC+BCC
            color_values.append(0.5)
    return color_values

def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with customizable options.")

    # Data source selection
    source = st.radio("Select data source:", ["Upload CSV", "Local File"])

    uploaded_file = None
    local_file = None
    df = None

    if source == "Upload CSV":
        uploaded_file = st.file_uploader("Upload CSV file", type="csv")
        if uploaded_file:
            df = load_data(uploaded_file=uploaded_file)

    elif source == "Local File":
        filename = st.text_input("Enter local CSV filename:", "AlyCoCrFeNi_data.csv")
        local_file = os.path.join(os.getcwd(), filename)
        if os.path.exists(local_file):
            df = load_data(local_file=local_file)
        else:
            st.warning(f"File not found: {local_file}")

    if df is None:
        st.stop()

    st.write("Loaded Data:")
    st.dataframe(df)

    # Calculate ternary coordinates
    df['p_Al'] = df['xAl']
    df['p_CoCr'] = df['xCo'] + df['xCr']
    df['p_FeNi'] = df['xFe'] + df['xNi']

    # Get colors
    color_values = get_color_values(df)

    # Sidebar customization
    st.sidebar.header("Plot Customization")
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

    # Proper ternary layout update
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
