# Day 11: AI/ML - Oct 25, 2025 - 

# More Important Functions

# value_counts
# sort_values
# rank
# sort_index
# set_index
# rename index -> rename
# reset_index
# unique & nunique
# isnull/notnull/hasnans
# dropna
# fillna
# drop_duplicates
# drop
# apply
# isin
# corr
# nlargest -> nsmallest
# insert
# copy

import numpy as np
import pandas as pd

# value_counts
- this will show how many time numbers repet 

```python
import numpy as np
import pandas as pd
a = pd.Series([1, 1, 1, 2, 2, 3])
print(a.value_counts())
```
**Output:**
```
1    3
2    2
3    1
```
---

value counts with chaning dtype
```python
import numpy as np
import pandas as pd
a = pd.Series([1, 1, 1, 2, 2, 3],dtype="int8")
result = a.value_counts() # init 64 is coming is from result which is getting from a.vloue_counts()
print(result)
result = result.astype('init8') # astype for chaing the datatype in datframe
print(result)
```
Note: 
- by default its int64
dtype: when building the data frame
astype: when you already have data set and wanted to change it from 64 to another value for memorty optomisation.

# value count, with dataframe
```python
import numpy as np
import pandas as pd
marks = pd.DataFrame([
    [100, 80, 10],
    [90, 70, 7],
    [120, 100, 14],
    [80, 70, 14],
    [80, 70, 14]
], columns=['iq', 'marks', 'package'])

print(marks)
print(marks.value_counts())
```
**Output:**
```
    iq  marks  package
0  100     80       10
1   90     70        7
2  120    100       14
3   80     70       14
4   80     70       14

# this is feaching the data as per the row.
iq   marks  package
80   70     14         2
90   70     7          1
100  80     10         1
120  100    14         1
Name: count, dtype: int64
```
---
```python
import numpy as np
import pandas as pd
ipl=pd.read_csv('./content/opl-matches.csv')
ipl.columns

ipl[~ipl['MatchNumber'].str.isdigit()]['Player_of_Match'].value_counts()

OR 

ipl[ipl['MatchNumber']]
0      1
1      2
2      3
3      QF1
4      Eliminator
5      4
dtype: object


ipl[ipl['MatchNumber']].unique
0     True
1     True
2     True
3    False
4    False
5     True
Name: MatchNumber, dtype: bool

ipl[~ipl['MatchNumber'].str.isdigit()] # Important: ~: this will change T to F and F to T and star.isdigit() helping us to give that value

ipl[ipl['MatchNumber'].str.isdigit()]
MatchNumber  |  Player_of_Match  |  ...
-------------+-------------------+-----
1            |  Kohli            |  ...
2            |  Dhoni            |  ...
Eliminator   |  Maxwell          |  ...
QF1          |  Jadeja           |  ...
Final        |  Buttler          |  ...
3            |  Rahul            |  ...


ipl[~ipl['MatchNumber'].str.isdigit()]

MatchNumber  |  Player_of_Match  |  ...
-------------+-------------------+-----
Eliminator   |  Maxwell          |  ...
QF1          |  Jadeja           |  ...
Final        |  Buttler          |  ...

value_counts() later gives us value counts


---
ipl['MatchNumber'].str.isdigit()
ipl['MatchNumber']

```
---

# sort_values function
x = pd.Sergies([12,14,1,56,89])
print(x)

x.sort_values # default ascending value = True

x.sort_values(asending=False)



---

movies = pd.read.csv('./contenct/movies.csv')
movies['title_x'].head()

movies.sort_values('title_x',ascending=False)['title_x'].head[]

---

import numpy as np
import pandas as pd 
students = pd.DataFrame(
{
    'name': ['rakesh', 'ankit', 'rupesh', np.nan, 'mrityunjay', np.nan, 'rishabh', np.nan, 'aditya', np.nan],
    'college': ['bit', 'iit', 'vit', np.nan, np.nan, 'vlsi', 'ssit', np.nan, np.nan, 'git'],
    'branch': ['eee', 'it', 'cse', np.nan, 'me', 'ce', 'civ', 'cse', 'bio', np.nan],
    'cgpa': [6.66, 8.25, 6.41, np.nan, 5.6, 9.0, 7.4, 10, 7.4, np.nan],
    'package': [4, 5, 6, np.nan, 6, 7, 8, 9, np.nan, np.nan]
}
)

print(students)

print(students.sort_values('package',ascending=False))

---

# rank
- The smallest value (10) appears twice -> both get rank 1.5 (average of rangks 1 and 2)
then 15 get 3 and 20 gets 4


import pandas as pd
s= pd.Series([10, 20, 15, 10])
print(s.rank())

0    1.5
1    4.0
2    3.0
3    1.5
dtype: float64

---

rank example 2:

import pandas as pd
s = pd.Series([100, 200, 200, 300])
print(s.rank(method='average')) # default
print(s.rank(method='min'))
print(s.rank(method='max'))
print(s.rank(method='first'))
print(s.rank(method='dense'))

average:
0    1.0
1    2.5
2    2.5
3    4.0

min:
0    1.0
1    2.0
2    2.0
3    4.0

max:
0    1.0
1    3.0
2    3.0
3    4.0

first:
0    1.0
1    2.0
2    3.0
3    4.0

dense:
0    1.0
1    2.0
2    2.0
3    3.0


---

# Groupby
```python
import numpy as np
import pandas as pd 
movies = pd.read.csv('./contenct/movies.csv')
movies.head()

genre = movies.groupby('Genre')
print(genre)
print(genre.std(numeric_only=True)) #this will group all the genere, and addtional all then gives the average, hence numberic only true required

# find the top 3 geners by total earning
genre = movies.groupby('Genre').sum().['Gross'].head()

or

genere.sum()['Gross'].head()


now check 3:
genre = movies.groupby('Genre').sum().['Gross'].head().sort_values(ascending=False).head()
```

# find the gere with highted avd imdb rating
genre.mean()

genre['IMDB'].mean().sort_values(ascending=False).head(2)

# Find the director with most popularity
# find director with most popularity
movies.groupby('Director')['No_of_votes'].sum().sort_values(ascending=False).head()

---

---

# find numbrer of movies done by each actor
movies['Start1'].value_counts()

#
movies.groupby('Genre')
len(movies.groupby('Genre'))

#
movies.groupby('Genre').size()
movies['Genre'].value_counts()


movies.groupby('Genre').first()

##
genre.get_group('Action')

OR 

movies[movies['Genre'] == 'Action']

---

# mergeing
import numpy as np
import pandas as pd
all_marks = pd.DataFrame([
    [100, 80, 10],
    [90, 70, 7],
    [120, 100, 14],
    [80, 70, 14],
    [80, 70, 14]],
    columns=['iq','marks','package']



print(all_marks)

 OR 

import numpy as np
import pandas as pd

marks1=pd.DataFrame([
    [100, 80, 10],
    [90, 70, 7],
    columns=['iq','marks','package']]


marks2=pd.DataFrame([
    [120, 100, 14],
    [80, 70, 14],
    [80, 70, 14]],
    columns=['iq','marks','package'])


combin_marks = pd.concat([marks1,marks2])
print(combin_marks)


## when we have 3 sets 
import numpy as np
import pandas as pd

marks1=pd.DataFrame([
    [100, 80, 10],
    [90, 70, 7],
    columns=['iq','marks','package']]


marks2=pd.DataFrame([
    [120, 100, 14],
    [80, 70, 14],
    [80, 70, 14]],
    columns=['iq','marks','package'])


marks3=pd.DataFrame([
    [120, 100, 14],
    [80, 70, 14],
    [80, 70, 14]],
    columns=['iq','marks','package3']) # differnt columns, this is vertically merged means columns wise


new_combin_marks = pd.concet([marks1,marks3]
print(new_combin))



new_combin_marks = pd.concet([marks1,marks2], ignore_index=True
print(new_combin))


## now to fill the horizontally index setting, by default its axis=0 (columnasiwd)
combine_marks_5 = pd.concat([marks1,marks2],ignore_index=True, axis=1)
print(combin_marks_5)


###
customer = pd.DataFrame([
    [101, 'Navid', 'Nanded'],
    [102, 'Raj', 'Pune'],
    [103, 'Bob', 'US']
], COLUMNS=['cid','name','location'])


order = pd.DataFrame([
    [1001,101,500],
    [1002,102,1500],
    [1003,103,4000],
    [1004,101,820],
    [1005,102,90],
],columns=['oid','cit','sales'])

## left join - matching or not matching shows everryting for left dataset
order.merge(customre,how='left', on='cid')

## right join - matching or not matching shows everryting for right dataset
order.merge(customre,how='right', on='cid')

# null joins 
df f= order.merge(customre,how='outer', on='cid')
df = df.isnull()
print(df [df['oid'],isnull()])
print(df [df['cid'],isnull()])


========================

# Day 12 - AI/ML - Oct 26 2025 - Startup_Funcing_Project
step1: Import raw file in py

import numpy as np
import panda as pd

df = pd.read_csv('starup_funding.csv')  # this will export your csv file
print(df) # this will dispaly only 10 records, first 5 and last 5 lines by default

df.info # this will give information about your data set

# Remove unwanted coloum - which become grabage chunk for our data sets
df.drop(columns=['Remarks'],inplace=True) # this will drop it and saved that dataset copy in memory and not change in original file

print(df.info())


# Access columns as with the help of indexing and colum number
df.set_index('Sr No', inplace=True) # take example of roll number which have 101, 102 so our custom index will change
df.loc[1] # like loc[101]

OR 

# To get the default indexing
df.iloc[0] 

```python
import numpy as np
import panda as pd

df = pd.read_csv('starup_funding.csv')  # this will export your csv file
print(df) # this will dispaly only 10 records, first 5 and last 5 lines by default

df.info # this will give information about your data set

# Remove unwanted coloum - which become grabage chunk for our data sets
df.drop(columns=['Remarks'],inplace=True) # this will drop it and saved that dataset copy in memory and not change in original file

print(df.info())


# Access columns as with the help of indexing and colum number
df.set_index('Sr No', inplace=True) # take example of roll number which have 101, 102 so our custom index will change
df.loc[1] # like loc[101]

# OR 

# To get the default indexing
df.iloc[0] 

# To rename the colums and well formatting
df.rename(columns={
    'Date dd/mm/yyyy': 'date',
    'Startup Name': 'startup',
    'Industry Vertical': 'vertical',
    'SubVertical': 'subvertical',
    'City  Location': 'city',
    'Investors Name': 'investors',
    'InvestmentType': 'round',
    'Amount in USD': 'amount'
}, inplace=True)


df.head()
df.info()

# Dtype is important ideally it shows as object but if you have amount it should be in number

# #type casting example - 
# amt1 = '20000' # this will still be string
# print(type(amt1)) # it must shows as string type
# amt2 = int(amt1) # we are converting it to interget so data set value can be read
# print(amt2)
# print(type(amt2))

# when we have quoma in number it will shows as error 

# amt1 = '20,000'
# amt2 = int(amt1)
# print(amt2)
# print(type(amt2))

# now take help of type casting 

# amt1 = '20,000'
# amt1 = amt1.replace(',','')
# amt2 = int(amt1)
# print(amt2)
# print(type(amt2))

# Check amount column and remove "," from the value and its dtype still string as consider as object
df['amount'] = df['amount'].str.replace(',','')
df.head(5)

# Masking - checked what are my amount column is converted into init
# step1: Idenfity which values can be converted to init
def can_convert_to_int(x):
    try:
        int(x)
        return True
    except:
        return False

# step2: Apply the function - this will call to con_convert_to_int and apply the changes
# apply will refer to x and pass the value
convertiable_mask = df['amount'].apply(can_convert_to_int)
type(convertiable_mask) # this will give the type as panda Series of single coloum will have either True or False

df.loc[convertiable_mask, 'mask']
        
# check what are my invalid values in amount
invalid_values = df.loc[~convertiable_mask,'amount'] # true becove false and false become true and will give the invalid values here
print(invalid_values)

# check what are my invalid values in amount with unique
invalid_values = df.loc[~convertiable_mask,'amount'].unique()# true becove false and false become true and will give the invalid values here
print(invalid_values)
print(len(invalid_values))

# Replace invalid values with string - "0"
df.loc[~convertiable_mask,'amount'] = '0'


# convert the column to inter type
df['amount'] = df['amount'].astype(int)
df.info()

# you have amount in dollor and wanted to convert in INR using creation of function
def to_inr(dollor):
    inr = dollor * 88.2
    return inr/1000000

df['amount'] = df['amount'].apply(to_inr)
df.head()



# now replace or format dates - earlier we only change the column name and we are working on date data for well formating 
# like some are indian date format - dd/mm/yyy or some dates are US format yyyy/mm/dd
from datetime import datetime

def  parse_mixed_date(date_str):
    for fmt in ("%d/%m/%Y","%m/%d/%Y"):
        try:
            return datetime.strptime(date_str,fmt) # it will first read the date_str function and check first formating and change th date
        except ValueError:
            continue # if it fail it will check second format value which is "%m/%d/%Y"
    return pd.NaT # Iit will return not(missing) if neither fromat works (fmt)


df['date'] = df['date'].apply(parse_mixed_date)
df.info()

# if you have most of row with 2000 and one or two have 3012 or 3912 then to get the exact row value
# Drop the row which even gives us 90% of our data

df = df.dropna(subset=['date', 'startup', 'vertical', 'city', 'investors', 'round', 'amount'])
df.info()

# as we converted date we can analaysi of the basisc of day, month or year
df['date'].dt.day
df['date'].dt.month
df['date'].dt.year


# now save your clean file
df.to_csv('startup_cleaned.csv', index=False)


# now in our investors we may have multiple investors which is our problem as well
df.head()

df('investors')
set(df['investors']) # this still not clean
(df['investors'].str.split(',')) # now we will get list
type(df['investors'].str.split(',')) # this will be in series
(df['investors'].str.split(',')).sum() # with sum() we got single list 
len(df['investors'].str.split(',')).sum()
type(df['investors'].str.split(',')).sum()) # this will give the data frame

set((df['investors'].str.split(',')).sum())


#
df[df['investors'].str.container('Tiger Global Management')].head()
df[df['investors'].str.container('Tiger Global Management')].head(10)

# this for just to check only
df[df['investors']] == 'Tiger Global Management'


# now groupby with startup and action on amount so we will get the value
df[df['investors'].str.contains('Tiger Global Management')].groupby('startup')['amount'].sum().sort_values(ascending=False)
   
# check in graph
df[df['investors'].str.contains('Tiger Global Management')].groupby('startup')['amount'].sum().sort_values(ascending=False).plot(kind='pie')

df[df['investors'].str.contains('Tiger Global Management')].groupby('city')['amount'].sum().sort_values(ascending=False).plot(kind='pie')


# have to check timeframe where and what time invesment happen
# if you don't have year coloum then create it in your data set which we can get 
df['year'] = df['date'].dt.year

df[df['investors'].str.contains('Tiger Global Management')].groupby('year')['amount'].sum().

```


=======================


# Install streamlit and Matplotlib

pip install streamlit - to run - streamlit run app.py
pip install matplotlib

1. create one application folder
2. Create application.py

```python
# Use the clean data which you can refer from Day 12 for straup example 
import streamlit as st
import pandas as pd
import time

st.title('Startup Dashboard')
st.header('I am learning Streamlit')
st.subheader('Salman Khan!')

st.write('This is a normal text')

st.markdown("""
## My favorite movies
- Race 3
- Humshakals
- Housefull
""")

st.code("""
def foo(input):
    return foo*2
""")

x = foo(2)
y = foo(2)

st.latex("x^2 + y^2 + z^2 = 0") # its library in streamlit

df = pd.DataFrame({
    'name': ['Nitish', 'Ankit', 'Anupam'],
    'marks': [50, 60, 70],
    'package': [10, 12, 14]
})

st.dataframe(df)

st.metric('Revenue', 'Rs 3L', '-3%')

# st.json is our dictionary
st.json({
    'name': ['Rakesh', 'Sumit', 'Kapil'],
    'marks': [50, 60, 70],
    'package': [10, 12, 14]
})

# Use image on your app - image should be in your path
st.image('unnamed.jpg')

# use video - this file should be in your path
st.video('For Loop in Python.mp4')

# Sidbar for your title
st.sidebar.title('Sidebar ka Title')

# To show in multiple coloms
col1, col2, col3 = st.columns(3)

with col1:
    st.image('unnamed.jpg')
with col2:
    st.image('unnamed.jpg')
with col3:
    st.image('unnamed.jpg')

st.error('Login Failed')
st.success('Login Successful')
st.info('Login Successful')
st.warning('Login Successful')

bar = st.progress(0)
for i in range(1, 51):
    time.sleep(1)
    bar.progress(i) # it will show progress bar

email1 = st.text_input('Enter email', key='email1')
number = st.number_input('Enter age')
st.date_input('Enter regis date')

email2 = st.text_input('Enter email', key='email2')
password = st.text_input('Enter password')
gender = st.selectbox('Select gender', ['male', 'female', 'others'])

btn = st.button('Login Karo')


# if the button is clicked
if btn:
    if email2 == 'info@technicalguffgu.com' and password == '1234':
        st.balloons()
        st.write(gender)
    else:
        st.error('Login Failed')

file = st.file_uploader('Upload a csv file')

if file is not None:
    df = pd.read_csv(file)
    st.dataframe(df.describe())
```

=============


# Now work on clean data
```python
import streamlit as st
import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt

# Set up the Streamlit app layout and title for the browser tab
st.set_page_config(layout="wide", page_title="Startup Analysis")

# Load the cleaned startup funding dataset
df = pd.read_csv('startup_cleanded.csv')

# Convert the 'date' column to pandas datetime, making sure any invalid parsing returns NaT
# This ensures consistent handling of date values for time-based analysis and filtering
df['date'] = pd.to_datetime(df['date'], errors='coerce')

# Extract 'month' and 'year' as separate integer columns from the parsed 'date'.
# This is useful for grouping and time series visualizations.
df['month'] = df['date'].dt.month
df['year'] = df['date'].dt.year

# Function to process and display overall analysis dashboard metrics and time series
def load_overall_analysis():
    # Calculate the total invested amount across all startups
    total = df['amount'].sum()

    # Find the maximum single funding amount ever received by any startup
    # Group by 'startup', then find the max 'amount', sort descending, collect the largest one
    max_funding = (
        df.groupby('startup')['amount']
        .max()
        .sort_values(ascending=False)
        .head(1)
        .values[0]
    )
  
    # Calculate average total funding received across all startups
    avg_funding = df.groupby('startup')['amount'].sum().mean()
  
    # Count the total number of unique funded startups
    num_startups = df['startup'].nunique()

    # Create four columns for metric cards in the dashboard layout
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric('Total', f"{total:.0f} Cr")
    with col2:
        st.metric('Max', f"{max_funding:.0f} Cr")
    with col3:
        st.metric('Avg', f"{round(avg_funding):.0f} Cr")
    with col4:
        st.metric('Funded Startups', num_startups)

    st.header('MoM (Month-over-Month) Graph')
    # User chooses whether to plot total funding or count of deals per month
    selected_option = st.selectbox('Select Type', ['Total', 'Count'])

    # Group data by year and month for the selected plot type
    if selected_option == 'Total':
        # Sum of funding amounts each month
        temp_df = df.groupby(['year', 'month'])['amount'].sum().reset_index()
    else:
        # Count of number of funding events each month
        temp_df = df.groupby(['year', 'month'])['amount'].count().reset_index()

    # Create a label for x-axis by month-year (e.g., '5-2021')
    temp_df['x_axis'] = temp_df['month'].astype(str) + '-' + temp_df['year'].astype(str)

    # Plot the trend using matplotlib and display it in Streamlit
    fig, ax = plt.subplots()
    ax.plot(temp_df['x_axis'], temp_df['amount'])
    ax.set_xlabel('Month-Year')
    ax.set_ylabel('Amount' if selected_option == 'Total' else 'Number of Deals')
    ax.set_title(f"Startup Funding {selected_option} (MoM)")

    st.pyplot(fig)


# Sidebar configuration for main navigation
st.sidebar.title('Startup Funding Analysis')

# Main dashboard option selection
option = st.sidebar.selectbox('Select One', ['Overall Analysis', 'StartUp', 'Investor'])

# Routing based on sidebar selection
if option == 'Overall Analysis':
    load_overall_analysis()
elif option == 'StartUp':
    # Placeholder for 'StartUp' analysis section
    pass
elif option == 'Investor':
    # Placeholder for 'Investor' analysis section
    pass


```