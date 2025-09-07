import streamlit as st
import pandas as pd
import numpy as np
from io import StringIO

def generate_hea_data(delta_y):
    # Define the range for y (Al content) from 0 to 1.5
    y_values = np.arange(0, 1.51, delta_y)
    
    # Initialize lists to store data
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
        # Determine alloy name
        alloy_name = f"Al{y:.3f}CoCrFeNi"
        
        # Determine structure based on y
        if y <= 0.5:
            structure = 'FCC'
        elif 0.5 < y <= 1.0:
            structure = 'FCC+BCC'
        else:  # y > 1.0
            structure = 'BCC'
        
        # Calculate mole fractions
        xAl = y / (y + 4)  # y for Al, 4 for equimolar Co, Cr, Fe, Ni
        x_other = (1 - xAl) / 4  # Equimolar fractions for Co, Cr, Fe, Ni
        
        # Append data
        data['mpea'].append(alloy_name)
        data['structure'].append(structure)
        data['xAl'].append(round(xAl, 4))
        data['xNi'].append(round(x_other, 4))
        data['xCr'].append(round(x_other, 4))
        data['xCo'].append(round(x_other, 4))
        data['xFe'].append(round(x_other, 4))
    
    # Create DataFrame
    df = pd.DataFrame(data)
    return df

def main():
    st.title("AlyCoCrFeNi Alloy Data Generator")
    st.write("Generate CSV data for AlyCoCrFeNi high-entropy alloys with varying Al content (y).")

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

    # Display DataFrame
    st.write("Generated Data:")
    st.dataframe(df)

    # Provide CSV download
    csv = df.to_csv(index=False)
    st.download_button(
        label="Download CSV",
        data=csv,
        file_name="AlyCoCrFeNi_data.csv",
        mime="text/csv"
    )

if __name__ == "__main__":
    main()
