# Day 16 - AI/ML - Oct 16, 2025 - EDA of Titanic dataset


# Exploratory Data Analysis – Titanic Dataset

This notebook provides a clean and structured EDA with:

- Dataset overview
- Missing value analysis
- Univariate analysis
- Bivariate analysis
- Correlation heatmap

```python
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
```

### Why do EDA

- Model building
- Analysis and reporting
- Validate assumptions
- Handling missing values
- Feature engineering
- Detecting outliers


### Column Types

- **Numerical** – Age, Fare, PassengerId
- **Categorical** – Survived, Pclass, Sex, SibSp(Siblings_with spouse), Parch(Parent_child), Embarked(from where they started)
- **Mixed** – Name, Ticket, Cabin


Categorical: we can catoriges these, like male and feamle as per sex


Mixed data type: we have 100, people with there name we can't categorical then its comes under mixed one but you can catorigzed as per their mark.


### Univariate Analysis

Univariate analysis focuses on analyzing each feature in the dataset independently.

- **Distribution analysis:** The distribution of each feature is examined to identify its shape, central tendency, and dispersion.
- **Identifying potential issues:** Univariate analysis helps in identifying potential problems with the data such as outliers, skewness, and missing values.

# distribution
The shape of a data distribution refers to its overall pattern or form as it is represented on a graph. Some common shapes of data distributions include:

- **Normal Distribution:** A symmetrical and bell-shaped distribution where the mean, median, and mode are equal and the majority of the data falls in the middle of the distribution with gradually decreasing frequencies towards the tails.
- **Skewed Distribution:** A distribution that is not symmetrical, with one tail being longer than the other. It can be either positively skewed (right-skewed) or negatively skewed (left-skewed).
- **Bimodal Distribution:** A distribution with two peaks or modes.
- **Uniform Distribution:** A distribution where all values have an equal chance of occurring.

The shape of the data distribution is important in identifying the presence of outliers, skewness, and the type of statistical tests and models that can be used for further analysis.

# Dispersion
**Dispersion** is a statistical term used to describe the spread or variability of a set of data. It measures how far the values in a data set are spread out from the central tendency (mean, median, or mode) of the data.

There are several measures of dispersion, including:

- **Range:** The difference between the largest and smallest values in a data set.
- **Variance:** The average of the squared deviations of each value from the mean of the data set.
- **Standard Deviation:** The square root of the variance. It provides a measure of the spread of the data that is in the same units as the original data.
- **Interquartile range (IQR):** The range between the first quartile (25th percentile) and the third quartile (75th percentile) of the data.

Dispersion helps to describe the spread of the data, which can help to identify the presence of outliers and skewness in the data.



Here is the Markdown transcription of the content from your provided image:

***

### Steps of doing Univariate Analysis on Numerical columns

- **Descriptive Statistics:** Compute basic summary statistics for the column, such as mean, median, mode, standard deviation, range, and quartiles. These statistics give a general understanding of the distribution of the data and can help identify skewness or outliers.

- **Visualizations:** Create visualizations to explore the distribution of the data. Some common visualizations for numerical data include histograms, box plots, and density plots. These visualizations provide a visual representation of the distribution of the data and can help identify skewness and outliers.

- **Identifying Outliers:** Identify and examine any outliers in the data. Outliers can be identified using visualizations. It is important to determine whether the outliers are due to measurement errors, data entry errors, or legitimate differences in the data, and to decide whether to include or exclude them from the analysis.

- **Skewness:** Check for skewness in the data and consider transforming the data or using robust statistical methods that are less sensitive to skewness, if necessary.

- **Conclusion:** Summarize the findings of the EDA and make decisions about how to proceed with further analysis.

# Age
conclusions: here we are using descfriptive stats

```python
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

```python

df['Age'].plot(kind='hist', bins=20)

'''
<Axes: ylabel='Frequency'>

'''

df['Age'].plot(kind='kde') # kernel desimal estimate

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
```

# now check how many comes in outliers



# Now check dataset with fare

#df['Fare'].plot(kind=) 

### Steps of doing Univariate Analysis on Categorical columns

**Descriptive Statistics:** Compute the frequency distribution of the categories in the column. This will give a general understanding of the distribution of the categories and their relative frequencies.

**Visualizations:** Create visualizations to explore the distribution of the categories. Some common visualizations for categorical data include count plots and pie charts. These visualizations provide a visual representation of the distribution of the categories and can help identify any patterns or anomalies in the data.

**Missing Values:** Check for missing values in the data and decide how to handle them. Missing values can be imputed or excluded from the analysis, depending on the research question and the data set.

**Conclusion:** Summarize the findings of the EDA and make decisions about how to proceed with further analysis.




# worked on serviceral
```python

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

df['sex'].value_counts()                    # Get the frequency count of each category in 'sex' column
df['sex'].value_counts().plot(kind='bar')   # Plot a bar chart of category frequencies in 'sex' column
df['sex'].value_counts().plot(kind='pie', autopct='%0.1f%%') # Plot a pie chart of category frequencies in 'sex' with percentage labels


df['Sibsp'].value_counts()                    # Get the frequency count of each category in 'Sibsp' column
df['Sibsp'].value_counts().plot(kind='bar')   # Plot a bar chart of category frequencies in 'Sibsp' column
df['Sibsp'].value_counts().plot(kind='pie', autopct='%0.1f%%') # Plot a pie chart of category frequencies in 'Sibsp' with percentage labels


df['Parch'].value_counts()                    # Get the frequency count of each category in 'Parch' column
df['Parch'].value_counts().plot(kind='bar')   # Plot a bar chart of category frequencies in 'Parch' column
df['Parch'].value_counts().plot(kind='pie', autopct='%0.1f%%') # Plot a pie chart of category frequencies in 'Parch' with percentage labels



```

### Embarked

- Southampton
- Queenstown
- Cherbourg

```python


df['Embarked'].value_counts()                    # Get the frequency count of each category in 'Embarked' column
df['Embarked'].value_counts().plot(kind='bar')   # Plot a bar chart of category frequencies in 'Embarked' column
df['Embarked'].value_counts().plot(kind='pie', autopct='%0.1f%%') # Plot a pie chart of category frequencies in 'Embarked' with percentage labels

df['Embarked'].isnull                    # checking null value where we don't know location from they started
```

####
```python

pd.crosstab(df['Pclass'], df['Embarked'], normalize='columns')*100
```

# survived and age
```python
df[df['Survived'] == 1]['Age'].plot(kind='kde', label='Survived')        # Plot KDE for 'Age' column where passengers survived
df[df['Survived'] == 0]['Age'].plot(kind='kde', label='Not Survived')    # Plot KDE for 'Age' column where passengers did not survive

plt.legend()    # Show legend for Survived/Not Survived curves
plt.show()      # Display the plot
```

# mean value who is traveling in third class
```python
df[df['Pclass'] == 2]['Age'].mean()    # Calculate the mean age of passengers in class 2
```


# Feature engineering on Fare col
```python
df['SibSp'].value_counts()    # Display the frequency count of each value in the 'SibSp' column (number of siblings/spouses aboard)

```

## 
```python
df[['individual_fare', 'Fare']].describe()    # Show summary statistics for 'individual_fare' and 'Fare' columns in the df2 DataFrame
```

#### family_type
# 1 -> alone
# 2-4 -> small
# >5 -> large

```python
def transform_family_size(num):               # Define a function to classify family size
    if num == 1:
        return 'alone'                       # Single person classified as 'alone'
    elif num > 1 and num < 5:
        return 'small'                       # Family size of 2 to 4 classified as 'small'
    else:
        return 'large'                       # Family size of 5 or more classified as 'large'

df['family_type'] = df['family_size'].apply(transform_family_size)   # Apply classification to each row in 'family_size', store result in 'family_type'

pd.crosstab(df2['Survived'], df2['family_type'], normalize='columns') * 100

```
### cabin 
df2['Cabin'].isnull().sum()/len(df2['Cabin'])
df2['Cabin']
df2['Cabin'].fillna('M',inplace=True)
df2['Cabin'].value_counts()

