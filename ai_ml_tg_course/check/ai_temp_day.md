# Day 13 - Nov 1, 2025 - Statistices 1


# What is Statistics?

Statistics is a branch of mathematics that involves collecting, analysing, interpreting, and presenting data. It provides tools and methods to understand and make sense of large amounts of data and to draw conclusions and make decisions based on the data.

In practice, statistics is used in a wide range of fields, such as business, economics, social sciences, medicine, and engineering. It is used to conduct research studies, analyse market trends, evaluate the effectiveness of treatments and interventions, and make forecasts and predictions.

## Examples

1. **Business** – Data Analysis (Identifying customer behaviour) and Demand Forecasting
2. **Medical** – Identify efficacy of new medicines (Clinical trials), Identifying risk factor for diseases (Epidemiology)
3. **Government & Politics** – Conducting surveys, Polling
4. **Environmental Science** – Climate research



***

# Types of Statistics

1. **Descriptive Statistics**

   Descriptive statistics deals with the collection, organization, analysis, interpretation, and presentation of data. It focuses on summarizing and describing the main features of a set of data, without making inferences or predictions about the larger population.

- when working on historical data
- measure of central tendency is part of descriptvie statistices.

ex: we already have data or actual data where we are not going to predict anyhwere.


2. **Inferential Statistics**

   Inferential statistics deals with making conclusions and predictions about a population based on a sample. It involves the use of probability theory to estimate the likelihood of certain events occurring, hypothesis testing to determine if a certain claim about a population is supported by the data, and regression analysis to examine the relationships between variables.

- working on prediction or future analysis
- prediction about population based on samples 
ex: take sample of 10cr people out of 140cr people and later use that prediction on 140cr people. 

ex1: we have 140cr people and we have to get the average salary of each person, so we take sample from some people which is called sample size. then the result comes as per prediction called interferential statistices.


prediction: sample data
forcasting: i have 1000 people data, and average usage is 5G, as per this data i am forcasting what will usage of them in the furture. 



***

# Population Vs Sample

Population (or target group)
Population refers to the entire group of individuals or objects that we are interested in studying. It is the complete set of observations that we want to make inferences about. For example, the population might be all the students in a particular school or all the cars in a particular city.

Sample (or sample data)
A sample, on the other hand, is a subset of the population. It is a smaller group of individuals or objects that we select from the population to study. Samples are used to estimate characteristics of the population, such as the mean or the proportion with a certain attribute. For example, we might randomly select 100 students.

## Examples

- All cricket fans vs fans who were present in the stadium
- All students vs those we visit college for lectures

## Things to be careful about when creating samples

1. Sample Size
2. Random
3. Representative

## Parameter Vs Statistic

A parameter is a characteristic of a population, while a statistic is a characteristic of a sample. Parameters are generally unknown and are estimated using statistics. The goal of statistical inference is to use the information obtained from the sample to make inferences about the population parameters.


##



***

Inferential statistics is a branch of statistics that deals with making inferences or predictions about a larger population based on a sample of data. It involves using statistical techniques to test hypotheses and draw conclusions from data. Some of the topics that come under inferential statistics are:

1. **Hypothesis testing:** This involves testing a hypothesis about a population parameter based on a sample of data. For example, testing whether the mean height of a population is different from a given value.

2. **Confidence intervals:** This involves estimating the range of values that a population parameter could take based on a sample of data. For example, estimating the population mean height within a given confidence level.

3. **Analysis of variance (ANOVA):** This involves comparing means across multiple groups to determine if there are any significant differences. For example, comparing the mean height of individuals from different regions.

4. **Regression analysis:** This involves modeling the relationship between a dependent variable and one or more independent variables. For example, predicting the sales of a product based on advertising expenditure.

5. **Chi-square tests:** This involves testing the independence or association between two categorical variables. For example, testing whether gender and occupation are independent variables.

6. **Sampling techniques:** This involves ensuring that the sample of data is representative of the population. For example, using random sampling to select individuals from a population for a survey.

7. **Bayesian statistics:** This is an alternative approach to statistical inference that involves updating beliefs about the probability of an event based on new evidence. For example, updating the probability of a disease given a positive test result.


## Types of data

flowchart TD
    A[Types of Data]
    B1[Categorical or Qualitative Data]
    B2[Numerical or Quantitative Data]
    C1[Nominal Data]
    C2[Ordinal Data]
    C3[Discrete Data]
    C4[Continuous Data]

    A --> B1
    A --> B2
    B1 --> C1
    B1 --> C2
    B2 --> C3
    B2 --> C4



Categorical or Qualitative Data: like location, gender of data
    - Nominal Data: male or female
    - Ordinal Data: how it behavirous good, fair, bad


Numerical or Quantitative Data: we can do calculation marks, age, weight, height
Discrete Data: there is no gap in data, like exact age like 35yr. any value which value don't dome in dots. this always be whole numerical data
Continuous Data: some people may have height of 5 or 5.1 or 6 / like percentage 58.2 or 59.8, this is float data


## Measure of Central Tendency
A measure of central tendency is a statistical measure that represents a typical or central value for a dataset. It provides a summary of the data by identifying a single value that is most representative of the dataset as a whole.

- we have to search whole datas center point
- example: for all student get the average or their marks.

we can calculate central tendency using
- mean
    - weighted mean
    - trimmed mean
- mediam
- mode


1. Mean
- the mean is the sum of all values in the datased divied by the number of values i.e average 
population mean formula ???
sample mean formula ??

flow: outlier - example there are number of students 5 and 4 got package between 4lpa to 9lpa however one stucent got 45lpa package in this case that 45lpa student is flow outlier mean here, which is taking care by medin



2. Mediam
- The median is the middle value in the dataset when the data is arranged in order 
ex data set: 45 5 6 7 8 10 15
using order: 5 6 7 8 10 15 45
median: 8 and ourlier will be not comes under cosideration

ex1: 1 2 3 4 5 6 7 8 
median: 4 + 5 = 9/2 = 4.5


3. Mode
- The mode is the value that appera most freqnelty in the dataset
- it us useful for categorical data or diccrete numerical values. 

datset: 1 1 2 3 1 4 5 6 1 2
mode: 1 mode

dataset1: 1 1 2 3 1 4 5 2
mode: 1,2 mode 

# 4. weighted mean
- The weighted mean is the sum of the products of each value and its weight, divided by the sum of the weights. it iss used to calculate a mean when the values in the datsset have different importance or frequency.

- we have 1 2 3 but all are representing other properties holding 

- so we will tread one as indivusual 

we are going to calculate with ML multiple model (another example is mean+mediam+mode ML model)
Liner regreation    : 0.2 -> 10L
regression analysis : 0.3 -> 15L
xdboost             : 0.5 -> 12L

0.2 x 10 + 0.3 x 15 + 0.5 x 12       2 + 4.5 + 6
-----------------------------   =   ------------  =  12.5 (weighted mean)
   0.2 + 0.3 + 0.5                      1



***

# 5. Trimmed Mean

A trimmed mean is calculated by removing a certain percentage of the smallest and largest values from the dataset and then taking the mean of the remaining values. The percentage of values removed is called the trimming percentage.

```
$20,000, $22,000, $23,000, $25,000, $28,000, $30,000, $32,000, $35,000, $50,000, $80,000
Trimmed Mean: $36,500
```

```
$25,000, $28,000, $30,000, $32,000, $35,000
Mean: $30,000
```

---

# Measure of Dispersion
A measure of dispersion is a statistical measure that describes the spread or variability of a dataset. It provides information about how the data is distributed around the central tendency (mean, median, or mode) of the dataset.

ex1: -5-----------0-------5 = -5 + 0 + 5 / 3 = 0

1. Range
- The range is the difference between the maximum and minimum values in the dataset
- It is simple measure of dispersion that is easy to calculate but can be affected by outliers. 

ex1: -5 (min value) -----------0-------5(max value) = 5 - (-5) = 10 is our range
ex2: -10 (min value) -----------0-------10(max value) = 10 - (-10) = 20 is our range

ex3 with outliers which can help using range hence we have to use variance: -5 (min value) -----0-------5-----250(max value)


2. Variance
Variance: The variance is the average of the squared differences between each data point and the mean. It measures the average distance of each data point from the mean and is useful in comparing the dispersion of datasets with different means.

Here is the completed variance table in Markdown format, using your data values (4, 8, 6, 5, 3):

First, calculate the mean:

$$
\text{Mean} = \frac{4+8+6+5+3}{5} = \frac{26}{5} = 5.2
$$

Now fill the table:

| x  | x - mean | (x - mean)² |
|----|----------|-------------|
| 3  | 3-3     | 0        |
| 2  | 2-3      | 1        |
| 1  | 1-3      | 4        |
| 5  | 5-3     | 4        |
| 4  | 4-3      | 1        |

x values mean is 3.
now in x - mean we are doing x - mean = 3(x value) - 3 (mean value)

average dispersion of each data point from the mean = 0 + 1 + 4 + 4 + 1 / 5 (total values) = 10 / 5 = 2 

variance formula for population
variance formula for sample population 


3. Standard deviation:
The standard deviation is the sqare root of the variance. It is a widely used measure of dispersion that is useful in descrpting theshape of a distribution. 

- what we got in variance we squre root the values that is standar deviation. 


4. Coefficient of Variation
Coefficient of Variation (CV): The CV is the ratio of the standard deviation to the mean expressed as a percentage. It is used to compare the variability of datasets with different means and is commonly used in fields such as biology, chemistry, and engineering.

The coefficient of variation (CV) is a statistical measure that expresses the amount of variability in a dataset relative to the mean. It is a dimensionless quantity that is expressed as a percentage.

The formula for calculating the coefficient of variation is:

CV = (standard deviation / mean) × 100%

example on titanic dataset, cv between age and fare column 

##### 

Examples

Here is the content from your image in Markdown format:

***

A common real-world use case for the **Coefficient of Variation (CV)** is in finance, particularly when comparing the **risk-adjusted returns** of different investments.

### Finance and Investment Analysis

The CV is an excellent tool for comparing the relative variability (risk) between two or more datasets that have **significantly different means** (average returns).

#### Scenario
Imagine you are comparing two stocks, **Stock A** and **Stock B**, over the last year.

| Investment | Average Monthly Return (Mean, μ) | Standard Deviation (Risk, σ) |
|------------|----------------------------------|------------------------------|
| Stock A    | 10%                              | 5%                           |
| Stock B    | 5%                               | 3%                           |

#### The Problem with Standard Deviation Alone

Stock A has a higher Standard Deviation (5%) than Stock B (3%), suggesting it is **riskier**.
However, Stock A also has a much higher average return (10%) than Stock B (5%).
Simply looking at the standard deviation doesn’t tell you if the extra risk is "worth it" for the extra return.

#### The Solution: Coefficient of Variation

The CV is calculated as the ratio of the standard deviation to the mean, expressed as a percentage:

$$
\text{CV (\%)} = \left( \frac{\text{Standard deviation}}{\text{Mean}} \right) \times 100
$$



***

In this context, the CV is essentially the **risk taken per unit of return**. A lower CV indicates a better risk-adjusted performance.

### Calculation:

- **Stock A CV:**  $$ \frac{5\%}{10\%} = 0.5 = 50\% $$
- **Stock B CV:**  $$ \frac{3\%}{5\%} = 0.6 = 60\% $$

### Conclusion:
- **Stock A has a CV of 50%.**
- **Stock B has a CV of 60%.**

Even though Stock A has a higher absolute risk ($$ \sigma = 5\% $$), it offers a better risk-adjusted return (lower CV) than Stock B. An investor seeking the most efficient use of risk would typically prefer **Stock A**.

### In Summary

The CV allows for a **fair, normalized comparison** of risk when the average values (returns) of the investments are unequal, making it a critical metric in portfolio management and investment selection.


### titanic

Here is the table content from your image in Markdown format:

***

| Passenger | Survived | Pclass | Name               | Sex     | Age | SibSp | Parch | Ticket   | Fare    | Cabin      | Embarked |
|-----------|----------|--------|--------------------|---------|-----|-------|-------|----------|---------|------------|----------|
| 1         | 0        | 3      | Braund, Mmale      | male    | 22  | 1     | 0     | A/5 21171| 7.25    |            | S        |
| 2         | 1        | 1      | Cumings, Ifemale   | female  | 38  | 1     | 0     | PC 17599 | 71.2833 | C85        | C        |
| 3         | 1        | 3      | Heikkinen, Ifemale | female  | 26  | 0     | 0     | STON/O2. | 7.925   |            | S        |
| 4         | 1        | 1      | Futrelle, Mfemale  | female  | 35  | 1     | 0     | 113803   | 53.1    | C123       | S        |
| 5         | 0        | 3      | Allen, Mr. male    | male    | 35  | 0     | 0     | 373450   | 8.05    |            | S        |
| 6         | 0        | 3      | Moran, Mmale       | male    |     | 0     | 0     | 330877   | 8.4583  |            | Q        |
| 7         | 1        | 1      | McCarthy, male     | male    | 54  | 0     | 0     | 17463    | 51.8625 | E46        | S        |
| 8         | 0        | 3      | Palsson, Mmale     | male    | 2   | 3     | 1     | 349909   | 21.075  |            | S        |
| 9         | 1        | 3      | Johnson, Mfemale   | female  | 27  | 0     | 2     | 247742   | 11.1333 |            | S        |
| 10        | 1        | 2      | Nasser, Mfemale    | female  | 14  | 1     | 0     | 237736   | 30.0708 |            | C        |



### check using ==== in excel
| Age | Fare    |
| --- | ------- |
| 22  | 7.25    |
| 38  | 71.2833 |
| 26  | 7.925   |
| 35  | 53.1    |
| 35  | 8.05    |
|     | 8.4583  |
| 54  | 51.8625 |
| 2   | 21.075  |
| 27  | 11.1333 |
| 14  | 30.0708 |

Column  std-deviation   Mean    Coefficient (percentage)
Age     =STDEV.S(A2:A89)        =std-devisation/mean * 100 
Fare    =


####

### Graphs for Univariate analysis
- when we work how our graph generated, of single colum either it will be categorical or numerical

1. Categorical
2. Numerical


***

# 1. Categorical – Frequency Distribution Table & Cumulative Frequency

A **frequency distribution table** is a table that summarizes the number of times (or frequency) that each value occurs in a dataset. 

Let’s say we have a survey of 200 people and we ask them about their favourite type of vacation, which could be one of six categories: Beach, City, Adventure, Nature, Cruise, or Other.

| Type of Vacation | Frequency |
|------------------|-----------|
| Beach            | 60        |
| City             | 40        |
| Adventure        | 30        |
| Nature           | 35        |
| Cruise           | 20        |
| Other            | 15        |



***

**Relative frequency** is the proportion or percentage of a category in a dataset or sample. It is calculated by dividing the frequency of a category by the total number of observations in the dataset or sample.

| Type of Vocation | Frequency | Relative Frequency |
|------------------|-----------|-------------------|
| Beach            | 60        | 0.3               |
| City             | 40        | 0.2               |
| Adventure        | 30        | 0.15              |
| Nature           | 35        | 0.175             |
| Cruise           | 20        | 0.1               |
| Other            | 15        | 0.075             |


Here is the content from your image in Markdown format:

***

## Cumulative frequency 
- Cumulative frequency is the running total of frequencies of a variable or category in a dataset or sample. It is calculated by adding up the frequencies of the current category and all previous categories in the dataset or sample.

| Type of Vocation | Frequency | Relative Frequency | Cumulative Frequency |
|------------------|-----------|-------------------|---------------------|
| Beach            | 60        | 0.3               | 60                  |
| City             | 40        | 0.2               | 100                 |
| Adventure        | 30        | 0.15              | 130                 |
| Nature           | 35        | 0.175             | 165                 |
| Cruise           | 20        | 0.1               | 185                 |
| Other            | 15        | 0.075             | 200                 |


Here is the content from your image in Markdown format:

***

# 2. Numerical – Frequency Distribution Table & Histogram

### Shape of Histogram

|   | Shape           | Description                       |
|---|-----------------|-----------------------------------|
| 1 | Symmetric (Normal disctriubtion)       | More value at middle              |
| 2 | Bimodal/Trimoal | Two Different Set of Values       |
| 3 | Left Skew       | Easy Exam Marks                   |
| 4 | Right Skew      | Hard Exam Marks                   |
| 5 | Uniform         | No. of Bins Reduced               |
| 6 | No Pattern      | No. of Bins more                  |


***

# 1. Categorical – Categorical

**Contingency Table/Crosstab**

A contingency table, also known as a cross-tabulation or crosstab, is a type of table used in statistics to summarize the relationship between two categorical variables. A contingency table displays the frequencies or relative frequencies of the observed values of the two variables, organized into rows and columns.

| Survived \   | 1   | 2   | 3   | Grand Total |
|--------------|-----|-----|-----|-------------|
| 0            | 80  | 97  | 372 | 549         |
| 1            | 136 | 87  | 119 | 342         |
| Grand Total  | 216 | 184 | 491 | 891         |

