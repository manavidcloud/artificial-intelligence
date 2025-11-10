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