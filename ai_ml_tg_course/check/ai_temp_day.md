# Day 17 - AI/ML - Nov 22, 2025 - PDF an dCDF in data science 

How to use PDF in Data Science
Saturday, November 22, 2025 8:01 AM

Use the IRIS dataset (150 flower samples).

It is a Machine Learning (ML) problem.

We need to predict the flower type using the following features:

Sepal Length, Sepal Width, Petal Length, and Petal Width.

Species : Setosa, Versicolor, Virginica

Feature selection is required to build an accurate prediction model.

We should use only the features that help in prediction and remove the features that do not contribute to the prediction.

The PDF will help us perform feature selection.

```python
import seaborn as sns 
df = sns.load_dataset('iris')
df.head()

# Display unique species in the DataFrame
df['species'].unique()
# Output:
# array(['setosa', 'versicolor', 'virginica'], dtype=object)

# Kernel density estimation plot of sepal length
sns.kdeplot(data=df, x='sepal_length')
# <Axes: xlabel='sepal_length', ylabel='Density'>

sns.kdeplot(data=df, x='petal_length')
# <Axes: xlabel='petal_length', ylabel='Density'>

sns.kdeplot(data=df, x='petal_width')
# <Axes: xlabel='petal_width', ylabel='Density'>

# KDE plot by species for sepal length (using hue)
sns.kdeplot(data=df, x='sepal_length', hue='species')
# <Axes: xlabel='sepal_length', ylabel='Density'>

# KDE plot by species for petal length
sns.kdeplot(data=df, x='petal_length', hue='species')

# KDE plot by species for petal width
sns.kdeplot(data=df, x='petal_width', hue='species')


```
---
kdeplot - represent pdf
ecdfplot - represent cdf

# CDF 
sns.kdeplot(data=df, x='petal_width', hue='species')
sns.ecdfplot(data=df, x='petal_width', hue='species')

I have number like 1, 2,3,4,5,4,2,1 then this is PDF 
but cdf will do like 1, 1+2 = 3, 3+3 = 6, 6+4=10



### 2D Density Plots - this is also called contor plot where we use the tow different plots

sns.jointplot(
    data=df, 
    x='petal_length', 
    y='sepal_length', 
    kind='kde', 
    fill=True, 
    cbar=True
)


## Poisson Distribution

*Saturday, November 15, 2025   8:01 AM*

***

The **Poisson Distribution** is a **probability distribution** used to model the number of times an event occurs **within a fixed interval of time, space, or area**, when:

- The events occur **independently**
- The average rate of occurrence (λ – lambda) is **constant**
- Two events **cannot happen at the same time**

***

Here is the transcribed content from your image, formatted in Markdown:

***

## Poisson Distribution

The Poisson Distribution is a probability distribution used to model the number of times an event occurs within a fixed interval of time, space, or area, when:

- ✔️ The events occur **independently**
- ✔️ The average rate of occurrence (λ – lambda) is **constant**
- ✔️ Two events **cannot happen at the same time**

***

**The Poisson Distribution is a probability distribution** used to model the number of times an event occurs **within a fixed interval of time, space, or area**, when:

- The events occur **independently**
- The average rate of occurrence (λ – lambda) is **constant**
- Two events **cannot happen at the same time**

***


### Real-Life Scenario            | Event Counted
----------------------------------|-----------------
Number of phone calls received in an hour       | Calls
Number of road accidents in a city per day      | Accidents
Number of defects in a manufacturing batch      | Defects
Number of messages you get per minute           | Messages
Number of customers arriving at a shop per hour | Customers


The horizontal axis is the index \( k \), the number of occurrences.  
\( \lambda \) is the expected rate of occurrences.  
The vertical axis is the probability of \( k \) occurrences given \( \lambda \). The function is defined only at integer values of \( k \); the connecting lines are only guides for the eye.

```python
import pandas as pd 
import numpy as np 
import matplotlib.pyplot as plt
import math
data = pd.read_csv('CallCenter.csv')
data
'''
|    | Call_ID | Call_Time                 | Call_Duration_sec | Agent_ID | Customer_ID | Issue_Type | Resolution_Status | Wait_Time_sec |
|----|---------|--------------------------|-------------------|----------|-------------|------------|-------------------|--------------|
| 0  | 1       | 2025-02-15 09:00:32.007593 | 535               | 1003     | 2026        | Billing    | Escalated         | 105          |
| 1  | 2       | 2025-02-15 09:01:07.362849 | 136               | 1012     | 2001        | Billing    | Escalated         | 51           |
| 2  | 3       | 2025-02-15
'''

# check hours based data
data['Hour'] = data['Call_time'].dt.hour

data.info()
data['Call_Time'] = pd['Call_Time'].astype('datetime')



# group by calls per hours now 
call_per_hours = data.groupby('Hour')['Call_ID'].count()
call_per_hours

'''
Hour
9   61
10  50
11  28
12  29
'''
# gettting lambad mean value - average envts (lambda)
lambda_val = call_per_hours.mean()
lambda_val
'''
np.flat64(50.0)
'''
# now get the probolty using pmf function 

k = 30 # number of evenrt we want probabiltiy for 
'''
use pmf formula - # Poisson formula: P(X = k) = (e^-λ * λ^k) / k!

'''

probability = (math.exp(-lambda_val) * (lambda_val ** k)) / math.factorial[k]
probability

'''
np.flot64(0.000)
'''


# example 2 -
# Poisson formula: P(X=k) = (e^-λ * λ^k) / k!

k = 50  # number of events we want probability for
probability = (math.exp(-lambda_val) * (lambda_val ** k)) / math.factorial(k)
print(f"Probability of {k} events occuring (lambda_val = {lambda_val} : {probability:.4f})")

'''
Output:
```
Probability of 50 events occuring (lambda_val = 50.0 : 0.0563)
'''

####
# Poisson formula: P(X=k) = (e^-λ * λ^k) / k!

k = 40  # number of events we want probability for
probability = (math.exp(-lambda_val) * (lambda_val ** k)) / math.factorial(k)
print(f"Probability of {k} events occuring (lambda_val = {lambda_val} : {probability:.4f})")

# Output: Probability of 40 events occuring (lambda_val = 50.0 : 0.0215)

# Generate values for k: and use metaplotlib for generating the plots 
k_values = np.arange(30, 70)
poisson_pmf = [(math.exp(-lambda_val) * (lambda_val ** k)) / math.factorial(k) for k in k_values]

plt.plot(k_values, poisson_pmf, marker='o')
plt.title('Poisson Distribution (lambda_val = 50)')
plt.xlabel('Number of Events (k)')
plt.ylabel('Probability P(X = k)')
plt.grid(True)
plt.show()

# now create table for all the values in stread of working on selective one 
k_values = np.arange(0, int(lambda_val*2))  # up to 2*avg calls
poisson_pmf = [(math.exp(-lambda_val) * lambda_val**k) / math.factorial(k) for k in k_values]

pmf_table = pd.DataFrame({'k (calls)': k_values, 'P(X=k)': poisson_pmf})
pmf_table
'''
| k (calls) |      P(X=k)      |
|-----------|------------------|
|     0     | 1.928750e-22     |
|     1     | 9.643749e-21     |
|     2     | 2.410937e-19     |
|     3     | 4.018229e-18     |
|     4     | 5.022786e-17     |
|   ...     |      ...         |
|    95     | 4.713320e-09     |
|    96     | 2.454854e-09     |
|    97     | 1.265389e-09     |
|    98     | 6.450656e-10     |
|    99     | 3.260639e-10     |


'''

# now get the pick hours 
peak_hours = call_per_hours['call_per_hours'] > call_per_hours.mean()
print("Peak Hours (Above Average):")
print(peak_hours)

'''
# Output
Hour
9     61
10    50
11    50
12    42
13    54
14    63
15    48
16    53
17    60
18    19
Name: Call_ID, dtype: int64

Peak Hours (Above Average):
Hour
9     61
13    54
14    63
16    53
17    60
Name: Call_ID, dtype: int64

'''

# This example demonstrates how to compute the Poisson PMF and CDF using scipy.stats.poisson for a given mean rate (λ) of 50.

import numpy as np
from scipy.stats import poisson 

lambda_val = 50

# Probability of exactly 50 calls
p_50 = poisson.pmf(50, lambda_val)

# Probability of 60 or fewer calls (CDF)
p_60 = poisson.cdf(60, lambda_val)

print("P(X = 50) =", p_50)
print("P(X ≤ 60) =", p_60)
print("P(X > 60) =", 1 - p_60)


# This code calculates the 95% safe hourly call volume using the Poisson distribution and estimates the number of agents needed given the agent capacity.

import numpy as np
from scipy.stats import poisson

lambda_val = 50        # average calls/hour
agent_capacity = 20    # # calls per agent per hour

# Find 95% safe call volume
safe_calls = poisson.ppf(0.95, lambda_val)
agents_needed = safe_calls / agent_capacity

print("Safe number of calls (95% of hours):", safe_calls)
print("Agents needed:", np.ceil(agents_needed))

---


## Normal Distribution

### 1. What is normal distribution?

Normal distribution, also known as Gaussian distribution, is a probability distribution that is commonly used in statistical analysis. It is a continuous probability distribution that is symmetrical around the mean, with a bell-shaped curve.



> Lots of points near the mean and very few far away

The normal distribution is characterized by two parameters: the mean (\(\mu\)) and the standard deviation (\(\sigma\)). The mean represents the centre of the distribution, while the standard deviation represents the spread of the distribution. Denoted as:


n ~ N(M,o) # [m -meanm, o - standard discutubtion]

### Why is it so important?

Commonality in Nature: Many natural phenomena follow a normal distribution, such as the heights of people, the weights of objects, the IQ scores of a population, and many more. Thus, the normal distribution provides a convenient way to model and analyse such data.

***

### PDF Equation of Normal Distribution

\[
f(x) = \frac{1}{\sigma \sqrt{2\pi}} e^{-\frac{1}{2} \left(\frac{x-\mu}{\sigma}\right)^2}
\]

***

Parameters in Normal Distribution

Equation in detail:

snd
m =0
standard diviation = 1
desmos.com


f(x) = 1/2pie - 1/2 (x-u )



















##################### 


### What is the Benefit?

Suppose the heights of adult males in a certain population follow a normal distribution with a mean of 68 inches and a standard deviation of 3 inches. What is the probability that a randomly selected adult male from this population is taller than 72 inches?

***

### What are Z-tables

A Z-table tells you the area underneath a normal distribution curve, to the left of the z-score.


# example of code 

