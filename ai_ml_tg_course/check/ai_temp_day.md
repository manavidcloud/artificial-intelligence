Day 14 - AI/ML - Oct 9, 2025 - Scatterplots
- Scatterplots is a linner one 
- Basic sctter plots is for co relationship between two data set like plot price and size datasete

## Covariance 
###  What is covariance and how is it interpreted?

Covariance is a statistical measure that describes the degree to which two variables are linearly related. It measures how much two variables change together, such that when one variable increases, does the other variable also increase, or does it decrease?

If the covariance between two variables is positive, it means that the variables tend to move together in the same direction. If the covariance is negative, it means that the variables tend to move in opposite directions. A covariance of zero indicates that the variables are not linearly related.


x is nothing but the data point

x is incresing and y also incresing = coverince +ve
x is incresing but y is decrying = coverince -ve
x is incresing but y is ideal = converince is 0

• How is it calculated?

|                 | Covariance Formula             |
|-----------------|-------------------------------|
| Population      | Sample                        |
| --------------- | -----------------------------|
| \(\sigma_{xy} = \frac{\sum (X - \mu_x)(Y - \mu_y)}{N}\) | \(s_{xy} = \frac{\sum (X - \bar{X})(Y - \bar{Y})}{n-1}\) |

- \(X, Y\) – The value of \(X\) and \(Y\)
- \(\mu_x, \mu_y\) – The population Mean of \(X\) and \(Y\)
- \(\bar{X}, \bar{Y}\) – The sample Mean of \(X\) and \(Y\)
- \(N\) – Total Number of population observations
- \(n\) – Total Number of sample observations

## Postive relationship of covariance 

Now check cvariance (Positvie relation between two data set example)
| Backlog (x) | Package (y) | X-X_mean | Y-Y_mean | (X-X_mean) * (Y-Y_mean) |
|-------------|-------------|----------|----------|-------------------------|
| 2           | 1           | -6       | -5       | 30                      |
| 5           | 2           | -3       | -4       | 12                      |
| 8           | 5           | 0        | -1       | 0                       |
| 13          | 12          | 5        | 6        | 30                      |
| 12          | 11          | 4        | 5        | 20                      |
| **8**       | **6**       |          | **Sum**  | **86**                  |
| X_Mean      | Y_Mean      |          |          |                         |

Covariance = 86/4 (we have 5 number and as per forumula n-1 = 4) **21.5**


Refrene Note: If our coverance output coming in 3 and 2 then most of time our coverince is positvle 

when creating a chart 

top left 1
top right 2
left bottom 3
right bottom 4 


```python
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.DataFrame()
x = pd.Series([12,25,68,42,113])
y = pd.Series([11,29,58,121,100])

df['x'] = x 
df['y'] = y 

print(df)



fig, (ax1,ax2) = plt.subplots(1,2, figsize = (10,3))

# Plot scatterplots on each axex
ax1.scatter(df['x'],df['y'])
ax2.scatter(df['x'],df['y'])

ax1.set_title('Covariance = ' + str(np.cov(df['x'], df['y'])[0, 1]))
ax2.set_title('Covariance = ' + str(np.cov(df['x'], df['y'])[0, 1]))
```



## Negative relationship of covariance 
Now check cvariance (Negative relation between two data set example)

| Backlog (x) | Package (y) | X-X_mean | Y-Y_mean | (X-X_mean) * (Y-Y_mean) |
|-------------|-------------|----------|----------|-------------------------|
| 2           | 10          | -6       | 4        | -24                     |
| 5           | 12          | -3       | 6        | -18                     |
| 8           | 5           | 0        | -1       | 0                       |
| 12          | 2           | 4        | -4       | -16                     |
| 13          | 1           | 5        | -5       | -25                     |
| **8**       | **6**       |          | **Sum**  | **-83**                 |
| X_Mean      | Y_Mean      |          |          |                         |

Covariance = **-20.75**

```python
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

df = pd.DataFrame()
x = pd.Series([2, 5, 8, 12, 13])
y = pd.Series([1, 2, 5, 12, 10])

df['x'] = x
df['y'] = y

fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3))

# Plot scatterplots on each axis
ax1.scatter(df['x'], df['y'])
ax2.scatter(df['x'], df['y'])

ax1.set_title('Covariance = ' + str(np.cov(df['x'], df['y'])[0, 1]))
ax2.set_title('Covariance = ' + str(np.cov(df['x'], df['y'])[0, 1]))
```



## No relationship of covariance 
Now check cvariance (Zero relation between two data set example)
| Backlog (x) | Package (y) | X-X_mean | Y-Y_mean | (X-X_mean) * (Y-Y_mean) |
|-------------|-------------|----------|----------|-------------------------|
| 2           | 10          | -6       | 0        | 0                       |
| 5           | 10          | -3       | 0        | 0                       |
| 8           | 10          | 0        | 0        | 0                       |
| 12          | 10          | 4        | 0        | 0                       |
| 13          | 10          | 5        | 0        | 0                       |
| **8**       | **10**      |          | **Sum**  | **0**                   |
| X_Mean      | Y_Mean      |          |          |                         |

Covariance = **0**

• Disadvantages of using Covariance

One limitation of covariance is that it does not tell us about the strength of the relationship between two variables, since the magnitude of covariance is affected by the scale of the variables.

• Covariance of a variable with itself

**Real-world example of covariance:**

**Ice Cream Sales and Temperature**
Imagine you own an ice cream shop and track daily sales alongside the temperature. You notice:
- On hot days (high temperature), ice cream sales are high
- On cold days (low temperature), ice cream sales are low

The covariance between temperature and ice cream sales would be **positive** because both variables tend to move in the same direction together.

**Why this matters:**
1. **Inventory planning** - If you know hot weather is forecasted, you can stock more ice cream
2. **Staffing decisions** - Schedule more employees during predicted hot periods
3. **Marketing timing** - Launch promotions when temperature patterns suggest lower sales


===

**Another example: Stock Portfolio Management**

Investment managers use covariance constantly:

If Stock A (tech company) and Stock B (another tech company) have positive covariance, they tend to rise and fall together.

If Stock A (airline) and Stock B (oil company) have negative covariance, when oil prices rise (Stock B up), airline costs increase and their stock might fall (Stock A down).

**Portfolio benefit:** By combining stocks with low or negative covariance, you can reduce overall risk - when one investment drops, another might rise, balancing your returns.

===

# Correlation

### What is correlation?

Correlation refers to a statistical relationship between two or more variables. Specifically, it measures the degree to which two variables are related and how they tend to change together.

Correlation is often measured using a statistical tool called the correlation coefficient, which ranges from -1 to 1. A correlation coefficient of -1 indicates a perfect negative correlation, a correlation coefficient of 0 indicates no correlation, and a correlation coefficient of 1 indicates a perfect positive correlation.

Formula

\[
\text{Correlation} = \frac{\text{Cov}(x,y)}{\sigma_x * \sigma_y}
\]


\[
r = \frac{\sum (x - m_x)(y - m_y)}{\sqrt{\sum (x - m_x)^2 \sum (y - m_y)^2}}
\]

**Example**

If studying hours (X) and test scores (Y):
- Covariance might be 15 (hard to interpret)
- But r = 0.85 clearly shows a strong positive relationship

**Key point:** Correlation is just *standardized* covariance, making it easier to interpret and compare!


```python
import seaborn as sns
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Create data
x = pd.Series([2, 5, 8, 12, 13])
y = pd.Series([1, 2, 5, 12, 10])

# Combine into a DataFrame
df = pd.DataFrame({'x': x, 'y': y})

# Create two subplots side by side
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 3))

# Plot scatterplots
ax1.scatter(df['x'], df['x'], color='steelblue')
ax2.scatter(df['x'], df['y'], color='darkorange')

# Compute correlations
corr_xx = df['x'].corr(df['x'])
corr_xy = df['x'].corr(df['y'])

# Set titles with formatted correlation values
ax1.set_title(f"Correlation = {corr_xx:.2f}")
ax2.set_title(f"Correlation = {corr_xy:.2f}")

# Add axis labels
ax1.set_xlabel('x')
ax1.set_ylabel('x')

ax2.set_xlabel('x')
ax2.set_ylabel('y')

# Improve layout and display
plt.tight_layout()
plt.show()
```
---

# Correlation and Causation

The phrase "correlation does not imply causation" means that just because two variables are associated with each other, it does not necessarily mean that one causes the other. In other words, a correlation between two variables does not necessarily imply that one variable is the reason for the other variable's behaviour.

Suppose there is a positive correlation between the number of firefighters present at a fire and the amount of damage caused by the fire. One might be tempted to conclude that the presence of firefighters causes more damage. However, this correlation could be explained by a third variable - the severity of the fire. More severe fires might require more firefighters to be present, and also cause more damage.

Thus, while correlations can provide valuable insights into how different variables are related, they cannot be used to establish causality. Establishing causality often requires additional evidence such as experiments, randomized controlled trials, or well-designed observational studies.

ex: when icream is more sell happening, more deth is happedning or murder are happedning. but this not shows the relation between two different values deth may cause because of different factors. Hence report will generate in wrong way. 


# Random variables 

what are algerbic varaible 

In algerbra a variable like x is an unknow value

x + 5 = 10 
x = 5

what are random variable in starts?

types of random variables 
1. Discrite random variables
- head, tail
- 1,2,3,4,5,6 in dice

2. continous random varaible 
- check student with height 5.67 or 6.25 or 
- random values with floting or without floating


# Probability Distributions
What are orbality disctributions?
- A probability disctribution is a list of all of the possible outcomes of a random variable along with their corresponing probability values.

ex1: coin toss

coin toss   head)1) tail(0)

p1             1/2      1/2



ex2: Dice


Dice        1   2   3   4   5   6
Probability 1/6 1/6 1/6 1/6 1/6 1/6

ex3: two dice roll
probalbity disctuoins table for two dice 

**Problem with Distribution?**

In many scenarios, the number of outcomes can be much larger and hence a table would be tedious to write down. Worse still, the number of possible outcomes could be infinite, in which case, good luck writing a table for that.

Example - Height of people, Rolling 10 dice together

Solution - Function?

What if we use a mathematical function to model the relationship between outcome and probability?


Note: a lot of time probability discturion and probabiltiy disctribution funcats are used interchangebly



Why are Probability Distributions important?
- Gives an idea about the shape/distribution of the data.
- And if our data follows a famous distribution then we automatically know a lot about the data.

A note on Parameters

Parameters in probability distributions are numerical values that determine the shape, location, and scale of the distribution.

Different probability distributions have different sets of parameters that determine their shape and characteristics, and understanding these parameters is essential in statistical analysis and inference.


# Probability Distribution Functions

1. PMF (Probability Mass Functions)
2. PDF (Probability Distribution Functions)
3. CDF Probability Cumulative Distributive Functions()

A probability distribution function (PDF) is a mathematical function that describes the probability of obtaining different values of a random variable in a particular probability distribution.


1. PMF (Probability Mass Functions)

PMF stands for Probability Mass Function. It is a mathematical function that describes the probability distribution of a **discrete random variable**.

The PMF of a discrete random variable assigns a probability to each possible value of the random variable. The probabilities assigned by the PMF must satisfy two conditions:

a. The probability assigned to each value must be non-negative (i.e., greater than or equal to zero).
b. The sum of the probabilities assigned to all possible values must equal 1.


ex1: Dice

        1       2       3       4       5       6
        1/6     1/6     1/6     1/6     1/6     1/6


as every number is coming only at once

 =      1       1       1       1       1       1
        /6      /6      /6      /6      /6      /6


=       6/6     = 1


Tow dice ( its comes under the PMF)


    1       1       1       1       1       1
    1/36    1/36    1/36    1/36    1/36    1/36



# Cumulative Distribution Function (CDF) of PMF

The cumulative distribution function (CDF) F(x) describes the probability that a random variable X with a given probability distribution will be found at a value less than or equal to x.

F(x) = P(X <= x)


```python
import pandas as pd
import random

L = []
for i in range(10000):
    a = random.randint(1, 6)
    L.append(a)

len(L)

L[:5]
#output: [5, 1, 4, 6, 1]

s = (pd.Series(L).value_counts() / pd.Series(L).value_counts().sum()).sort_index()
# his line of code calculates the normalized frequency (i.e., empirical probability) of each unique value in list L, sorts the results by their index, and stores the result in variable s. This produces an empirical probability mass function for the values in L.

print(s)


# define the plot
s.plot(kind='bar')

```
---


Work with Two dice

```python
import pandas as pd
import random

L = []
for i in range(10000):
    a = random.randint(1, 6)
    b = random.randint(1, 6)
    L.append(a + b)

L[:5]
# [8, 8, 6, 11, 9]

s = (pd.Series(L).value_counts() / pd.Series(L).value_counts().sum()).sort_index()

# define the plot
s.plot(kind='bar')

```

CDF example

```python
import numpy as np
import pandas as pd
import random

np.cumsum(s)

L = []
for i in range(10000):
    a = random.randint(1, 6)
    b = random.randint(1, 6)
    L.append(a + b)

L[:5]
# [8, 8, 6, 11, 9]

s2 = np.cumsum(s)
s2 = (pd.Series(L).value_counts() / pd.Series(L).value_counts().sum()).sort_index()

# define the plot
s2.plot(kind='bar')


print(s)
print(s2)


```

cumsum(): Cumalative sum
- 
Dataset         cumatlative sum
10              10
20              30
5               35
10              45
30              75




