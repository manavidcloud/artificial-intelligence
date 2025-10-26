import streamlit as st
import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt

# Set up the Streamlit app with a wide layout and a descriptive page title
st.set_page_config(layout="wide", page_title='Startup Analysis')

# Load the cleaned startup funding data
df = pd.read_csv('startup_cleanded.csv')

# Convert the 'date' column to pandas datetime format.
# This ensures unparseable dates become NaT (missing), making further time-based analysis reliable.
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# Create new columns for month and year, extracted from the parsed date for easier grouping and analysis.
df['month'] = df['date'].dt.month
df['year'] = df['date'].dt.year

# This function handles the main dashboard analysis and generates summary metrics as well as trend graphs
def load_overall_analysis():
    # Calculate the total amount invested across all startups
    total = df['amount'].sum()

    # Find the maximum amount funded in a single deal for any startup
    max_funding = (
        df.groupby('startup')['amount']
        .max()
        .sort_values(ascending=False) # Sort to get the highest funding
        .head(1)
        .values[0]
    )

    # Calculate the average total funding received by startups
    avg_funding = df.groupby('startup')['amount'].sum().mean()

    # Count the number of unique funded startups
    num_startups = df['startup'].nunique()

    # Display four summary metric cards at the top of the dashboard
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Total', f"{total:.0f} Cr")
    with col2:
        st.metric('Max', f"{max_funding:.0f} Cr")
    with col3:
        st.metric('Avg', f"{round(avg_funding):.0f} Cr")
    with col4:
        st.metric('Funded Startups', num_startups)
    
    # Month-over-Month analysis section
    st.header('MoM (Month-over-Month) Graph')

    # Option to switch between total funding and count of deals in the trend graph
    selected_option = st.selectbox('Select Type', ['Total', 'Count'])
    
    if selected_option == 'Total':
        temp_df = df.groupby(['year', 'month'])['amount'].sum().reset_index()
    else:
        temp_df = df.groupby(['year', 'month'])['amount'].count().reset_index()
    
    # Prepare an x-axis label combining month and year for better readability
    temp_df['x_axis'] = temp_df['month'].astype(str) + '-' + temp_df['year'].astype(str)

    # Plot the MoM trend using matplotlib and display it in the app
    fig, ax = plt.subplots()
    ax.plot(temp_df['x_axis'], temp_df['amount'])
    ax.set_xlabel('Month-Year')
    ax.set_ylabel('Amount (in Cr)' if selected_option == 'Total' else 'Number of Fundings')
    ax.set_title(f"Startup Funding {selected_option} (MoM)")
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

# Sidebar section for app navigation
st.sidebar.title('Startup Funding Analysis')

# Let the user select the dashboard section from the sidebar
option = st.sidebar.selectbox('Select One', ['Overall Analysis', 'StartUp', 'Investor'])

# Render different sections based on user selection
if option == 'Overall Analysis':
    load_overall_analysis()
elif option == 'StartUp':
    # Placeholder for startup-specific analysis
    st.write("StartUp analysis will be implemented here.")
elif option == 'Investor':
    # Placeholder for investor-specific analysis
    st.write("Investor analysis will be implemented here.")
