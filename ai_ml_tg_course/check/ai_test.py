## Standard Normal Variate

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
import seaborn as sns 

df = pd.read_csv('titanic.csv')
df['']

'''

|   | PassengerId | Survived | Pclass | Name                                              | Sex    | Age | SibSp | Parch | Ticket           | Fare    | Cabin | Embarked |
|---|-------------|----------|--------|---------------------------------------------------|--------|-----|-------|-------|------------------|---------|-------|----------|
| 0 | 1           | 0        | 3      | Braund, Mr. Owen Harris                           | male   | 22.0| 1     | 0     | A/5 21171        | 7.2500  | NaN   | S        |
| 1 | 2           | 1        | 1      | Cumings, Mrs. John Bradley (Florence Briggs Thayer)| female | 38.0| 1     | 0     | PC 17599         | 71.2833 | C85   | C        |
| 2 | 3           | 1        | 3      | Heikkinen, Miss. Laina                            | female | 26.0| 0     | 0     | STON/O2. 3101282 | 7.9250  | NaN   | S        |
| 3 | 4           | 1        | 1      | Futrelle, Mrs. Jacques Heath (Lily May Peel)      | female | 35.0| 1     | 0     | 113803           | 53.1000 | C123  | S        |

'''



df['Age']

'''
Sample output:

0      22.0
1      38.0
2      26.0
3      35.0
4      35.0
...
886    27.0
887    19.0
888     NaN
889    26.0
890    32.0
Name: Age, Length: 891, dtype: float64
'''

sns.kdeplot(titanic['Age'])

titatnic['Age'].mean()
titanic['Age'].std() 

titanic['Age']

# now standarize the data- converting it to SNV 
x = (titanic['Age'] - titanic['Age'].mean())

# now divide it to its standad deviation 
x = (titanic['Age'] - titanic['Age'].mean())

### After Standard Normal Variate
x = (titanic['Age'] - titanic['Age'].mean()) / titanic['Age'].std()
x

'''
Sample output:


0      -0.530005
1       0.571430
2      -0.254646
3       0.364911
4       0.364911
...
886    -0.185807
887    -0.736524
888          NaN
889    -0.254646
890     0.158392
Name: Age, Length: 891, dtype: float64
'''


# kdplot with normal data without standard deviation
sns.kdeplot

# kdplot with stand deviation 
sns.kdplot(x)
x.mean()

x.std()

