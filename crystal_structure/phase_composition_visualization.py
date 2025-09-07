import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import matplotlib.cm as cm
import matplotlib.colors as mcolors
import numpy as np
import os

# Function to generate alloy data
def generate_hea_data(delta_y):
    y_values = np.arange(0, 1.51, delta_y)
    data = {
        'mpea': [],
        'structure': [],
        'xAl': [],
        'xNi': [],
        'xCr': [],
        'xCo': [],
        'xFe': []
    }
    
    for y in y_values:
        alloy_name = f"Al{y:.3f}CoCrFeNi"
        if y <= 0.5:
            structure = 'FCC'
        elif 0.5 < y <= 1.0:
            structure = 'FCC+BCC'
        else:
            structure = 'BCC'
        
        xAl = y / (y + 4)
        x_other = (1 - xAl) / 4
        
        data['mpea'].append(alloy_name)
        data['structure'].append(structure)
        data['xAl'].append(round(xAl, 4))
        data['xNi'].append(round(x_other, 4))
        data['xCr'].append(round(x_other, 4))
        data['xCo'].append(round(x_other, 4))
        data['xFe'].append(round(x_other, 4))
    
    return pd.DataFrame(data)

# Function to assign color values based on structure and y
def get_color_values(df):
    color_values = []
    for _, row in df.iterrows():
        alloy_name = row['mpea']
        structure = row['structure']
        y = float(alloy_name.split('Al')[1].split('Co')[0])
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

def main():
    st.title("AlyCoCrFeNi Ternary Diagram")
    st.write("Visualize the AlyCoCrFeNi alloy compositions in a ternary diagram with customizable options.")

    # User input for delta_y
    delta_y = st.slider(
        "Select step size for y (stoichiometry of Al)",
        min_value=0.001,
        max_value=0.1,
        value=0.05,
        step=0.001,
        format="%.3f"
    )

    # Generate data
    df = generate_hea_data(delta_y)

    # Save CSV locally for reference
    csv_path = os.path.join(os.getcwd(), "AlyCoCrFeNi_data.csv")
    df.to_csv(csv_path, index=False)
    st.write(f"Data saved locally at: {csv_path}")

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

    # Provide CSV download
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download Generated CSV",
        data=csv,
        file_name="AlyCoCrFeNi_data.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
