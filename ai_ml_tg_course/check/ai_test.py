import numpy as np
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt 

df = pd.read_csv('./titanic/train.csv')

df.head()

'''
# Output from reading the titanic csv
| PassengerId | Survived | Pclass | Name                                              | Sex    | Age  | SibSp | Parch | Ticket        | Fare    | Cabin | Embarked |
|-------------|----------|--------|---------------------------------------------------|--------|------|-------|-------|---------------|---------|-------|----------|
| 1           | 0        | 3      | Braund, Mr. Owen Harris                           | male   | 22.0 | 1     | 0     | A/5 21171     | 7.2500  | NaN   | S        |
| 2           | 1        | 1      | Cumings, Mrs. John Bradley (Florence Briggs Th...)| female | 38.0 | 1     | 0     | PC 17599      | 71.2833 | C85   | C        |
| 3           | 1        | 3      | Heikkinen, Miss. Laina                            | female | 26.0 | 0     | 0     | STON/O2. 3101282 | 7.9250 | NaN   | S        |
| 4           | 1        | 1      | Futrelle, Mrs. Jacques Heath (Lily May Peel)      | female | 35.0 | 1     | 0     | 113803        | 53.1000 | C123  | S        |
| 5           | 0        | 3      | Allen, Mr. William Henry                          | male   | 35.0 | 0     | 0     | 373450        | 8.0500  | NaN   | S        |
'''

df['Age'].describe()
'''
count    714.000000
mean      29.699118
std       14.526497
min        0.420000
25%       20.125000
50%       28.000000
75%       38.000000
max       80.000000
Name: Age, dtype: float64

'''

df['Age'].plot(kind='hist', bins=20)

'''
<Axes: ylabel='Frequency'>

'''

df['Age'].plot(kind='kde')

'''
<Axes: ylabel='Density'>

'''
df['Age'].skew()

'''
np.flot64(0.3891077)
'''

df['Fare'].plot(kind='kde')

df['Age'].plot(kind='box')

df['Age'].describe()

df[df['Age'] > 65] # checking outliners

df[df['Age'].isnull().sum()]

df[df['Age'].isnull().sum()/len(df['Age']*100)] # age is not defined

# Now check dataset with fare

#df['Fare'].plot(kind=) 

# worked on serviceral
df['Survived'].describe()
df['Survived'].value_counts() # getting total counts of survived

df['Survived'].value_counts().plot(kind='bar') # virutalisation 

df['Survived'].value_counts().plot(kind='pie',autopct="%0.1f%%") # getting percentage 


# servuval - onpplass (top class from dataset )
df['Pclass'].describe()
df['Plass'].value_counts() # getting total counts of pclass (first class)

df['Plass'].value_counts().plot(kind='bar') # virutalisation 

df['Plass'].value_counts().plot(kind='pie',autopct="%0.1f%%") # getting percentage 

#Do the same as per sex(male,female), Sibsp, pach (parent-child)

df['sex'].value_counts()                    # Get the frequency count of each category in 'Parch' column
df['sex'].value_counts().plot(kind='bar')   # Plot a bar chart of category frequencies in 'Parch' column
df['sex'].value_counts().plot(kind='pie', autopct='%0.1f%%') # Plot a pie chart of category frequencies in 'Parch' with percentage labels


df['Sibsp'].value_counts()                    # Get the frequency count of each category in 'Parch' column
df['Sibsp'].value_counts().plot(kind='bar')   # Plot a bar chart of category frequencies in 'Parch' column
df['Sibsp'].value_counts().plot(kind='pie', autopct='%0.1f%%') # Plot a pie chart of category frequencies in 'Parch' with percentage labels


df['Parch'].value_counts()                    # Get the frequency count of each category in 'Parch' column
df['Parch'].value_counts().plot(kind='bar')   # Plot a bar chart of category frequencies in 'Parch' column
df['Parch'].value_counts().plot(kind='pie', autopct='%0.1f%%') # Plot a pie chart of category frequencies in 'Parch' with percentage labels


df['Embarked'].value_counts()                    # Get the frequency count of each category in 'Embarked' column
df['Embarked'].value_counts().plot(kind='bar')   # Plot a bar chart of category frequencies in 'Embarked' column
df['Embarked'].value_counts().plot(kind='pie', autopct='%0.1f%%') # Plot a pie chart of category frequencies in 'Embarked' with percentage labels

df['Embarked'].isnull()                  # checking null value where we don't know location from they started


###
pd.crosstab(df['Pclass'], df['Embarked'], normalize='columns')*100


# survived and age

df[df['Survived'] == 1]['Age'].plot(kind='kde', label='Survived')        # Plot KDE for 'Age' column where passengers survived
df[df['Survived'] == 0]['Age'].plot(kind='kde', label='Not Survived')    # Plot KDE for 'Age' column where passengers did not survive

plt.legend()    # Show legend for Survived/Not Survived curves
plt.show()      # Display the plot

# mean value who is traveling in third class
df[df['Pclass'] == 2]['Age'].mean()    # Calculate the mean age of passengers in class 2

# Feature engineering on Fare col
df['SibSp'].value_counts()    # Display the frequency count of each value in the 'SibSp' column (number of siblings/spouses aboard)

### 
df[['individual_fare', 'Fare']].describe()    # Show summary statistics for 'individual_fare' and 'Fare' columns in the df2 DataFrame
df[df['Fare'] > 500]
df[df['Individual_fate'] > 500]




#### family_type
# 1 -> alone
# 2-4 -> small
# >5 -> large

def transform_family_size(num):               # Define a function to classify family size
    if num == 1:
        return 'alone'                       # Single person classified as 'alone'
    elif num > 1 and num < 5:
        return 'small'                       # Family size of 2 to 4 classified as 'small'
    else:
        return 'large'                       # Family size of 5 or more classified as 'large'

df['family_type'] = df['family_size'].apply(transform_family_size)   # Apply classification to each row in 'family_size', store result in 'family_type'

pd.crosstab(df2['Survived'], df2['family_type'], normalize='columns') * 100

### cabin 
df2['Cabin'].isnull().sum()/len(df2['Cabin'])
df2['Cabin']
df2['Cabin'].fillna('M',inplace=True)
df2['Cabin'].value_counts()

