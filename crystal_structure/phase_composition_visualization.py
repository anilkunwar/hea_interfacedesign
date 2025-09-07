import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np

# Function to load data from GitHub
@st.cache_data
def load_data(github_url):
    try:
        df = pd.read_csv(github_url)
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
        # Extract y from alloy name (e.g., Al0.300CoCrFeNi -> 0.300)
        y = float(alloy_name.split('Al')[1].split('Co')[0])
        if structure == 'FCC':
            color_values.append(1.0)
        elif structure == 'BCC':
            color_values.append(0.0)
        else:  # FCC+BCC
            # Linear interpolation between 0.5 (1.0) and 1.0 (0.0)
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

def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with customizable options.")

    # Input for GitHub CSV URL
    github_url = st.text_input(
        "Enter GitHub raw CSV URL",
        "https://raw.githubusercontent.com/USER/REPO/main/AlyCoCrFeNi_data.csv"
    )

    # Load data
    df = load_data(github_url)
    if df is None:
        st.stop()

    # Calculate ternary coordinates
    df['p_Al'] = df['xAl']
    df['p_CoCr'] = df['xCo'] + df['xCr']
    df['p_FeNi'] = df['xFe'] + df['xNi']

    # Get color values
    color_values = get_color_values(df)

    # Sidebar for customization
    st.sidebar.header("Plot Customization")
    colormap = st.sidebar.selectbox("Select Colormap", get_colormap_options(), index=0)
    line_thickness = st.sidebar.slider("Ternary Line Thickness", 0.5, 5.0, 2.0, 0.1)
    grid_thickness = st.sidebar.slider("Grid Line Thickness", 0.1, 2.0, 0.5, 0.1)
    show_grid = st.sidebar.checkbox("Show Grid", value=True)
    font_size = st.sidebar.slider("Font Size (Labels & Ticks)", 8, 20, 12, 1)

    # Custom labels
    al_label = st.sidebar.text_input("Al Vertex Label", "Al")
    cocr_label = st.sidebar.text_input("CoCr Vertex Label", "Co+Cr")
    feni_label = st.sidebar.text_input("FeNi Vertex Label", "Fe+Ni")

    # Create ternary plot
    fig = go.Figure()

    # Get colormap
    cmap = cm.get_cmap(colormap)
    colors = [mcolors.rgb2hex(cmap(val)) for val in color_values]

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
                colorscale=colormap,
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

if __name__ == "__main__":
    main()
