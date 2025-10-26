import streamlit as st
import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title='Startup Analysis')
df = pd.read_csv('startup_cleanded.csv')



# This code converts the 'date' column in the DataFrame df to pandas datetime format, coercing invalid or unparseable dates to NaT (Not a Time). This ensures consistent date datatypes for further analysis or filtering
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# creating two coloum of month and year with the help of date
df['month'] = df['date'].dt.month
df['year'] = df['date'].dt.year

# To call overall analyssi data processing we required this function
def load_overall_analysis():
    # pass
    # Total invested Amount
    total = df['amount'].sum()
    
    # Check max funding
    #max_funding = df.groupby('startup'['amount']) - showing the amount coloum
    #max_funding = df.groupby('startup'['amount'].max() - max value
    # max_funding = df.groupby('startup'['amount'].max().sort_values(ascending=False) - sorting
    # max_funding = df.groupby('startup'['amount'].max().sort_values(ascending=False).head[1].index[0] - it will gives the key
    max_funding = df.groupby('startup'['amount'].max().sort_values(ascending=False).head[1].values[0])
    
    avg_funding = df.groupby('startup')['amount'].sum().mean()
    
    # total funded startups 
    num_startups = df['startup'].nunique()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Total', str(total) + ' Cr')
    with col2:
        st.metric('Max', str(max_funding) + ' Cr')
    with col3:
        st.metric('Avg', str(round(avg_funding)) + ' Cr')
    with col4:
        st.metric('Funded Startups', num_startups)
        
    st.header('MoM Graph')
    
    selected_option = st.selectbox('Select Type', ['Total', 'Count'])
    
    if selected_option == 'Total':
        temp_df = df.groupby(['year', 'month'])['amount'].sum().reset_index()
        
    else:
        temp_df = df.groupby(['year', 'month'])['amount'].count().reset_index()
        
    
    temp_df['x_axis'] = temp_df['month'].astype('str') + '-' + temp_df['year'].astype('str')

    fig3, ax3 = plt.subplots()
    ax3.plot(temp_df['x_axis'],temp_df['amount'])
    
    st.pyplot(fig3)
    

        



st.sidebar.title('Startup Funding Analyasis')

option = st.sidebar.selectbox('Select One', ['Overall Analysis', 'StartUp', 'Investor'])

if option == 'Overall Analysis':
    # pass
    load_overall_analysis()

elif option == 'StartUp':
    pass

else:
    pass