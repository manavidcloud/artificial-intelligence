# Day 7 - Oct 11th 2025 - 
## 1. Joblib

C:\Users\manav>pip install joblib
Collecting joblib
  Downloading joblib-1.5.2-py3-none-any.whl.metadata (5.6 kB)
Downloading joblib-1.5.2-py3-none-any.whl (308 kB)
Installing collected packages: joblib
Successfully installed joblib-1.5.2

from sklearn.datasets import make_regression
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error

# Create dataset
X, y = make_regression(n_samples=100, n_features=1, noise=10, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Train model
model = LinearRegression()
model.fit(X_train, y_train)

# Evaluate
preds = model.predict(X_test)
print("MSE:", mean_squared_error(y_test, preds))



# Task 2: Serialize Model with Joblib
from joblib import dump

# Save model to file
dump(model, "linear_model.joblib")
print("Model saved successfully!")

---

## 2. Numpy
## Install numppy
```
C:\Users\manav>pip install numpy
Collecting numpy
  Downloading numpy-2.3.3-cp313-cp313-win_amd64.whl.metadata (60 kB)
Downloading numpy-2.3.3-cp313-cp313-win_amd64.whl (12.8 MB)
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ 12.8/12.8 MB 11.3 MB/s  0:00:01
Installing collected packages: numpy
Successfully installed numpy-2.3.3
```
## Find the correct path of your correct python interperter if vscode

python -m pip show numpy # To find install path
open vscode and Press Ctrl + Shift + P
Open VS Code Command Palette

Press Ctrl + Shift + P (or Cmd + Shift + P on Mac).

2. Select Interpreter

Type and choose “Python: Select Interpreter”.
- you will get two option, recommanded or global
- select the global
- check the program again your program must rexognise the numpy in the py.


***

### What is numpy?

NumPy is the fundamental package for scientific computing in Python. It is a Python library that provides a multidimensional array object, various derived objects (such as masked arrays and matrices), and an assortment of routines for fast operations on arrays, including mathematical, logical, shape manipulation, sorting, selecting, I/O, discrete Fourier transforms, basic linear algebra, basic statistical operations, random simulation, and much more.

At the core of the NumPy package is the ndarray object. This encapsulates n-dimensional arrays of homogeneous data types.

***

### NumPy Arrays vs Python Sequences

- NumPy arrays have a fixed size at creation, unlike Python lists (which can grow dynamically). Changing the size of an ndarray will create a new array and delete the original.
- The elements in a NumPy array are all required to be of the same data type, and thus will be the same size in memory.
- NumPy arrays facilitate advanced mathematical and other types of operations on large numbers of data. Typically, such operations are executed more efficiently and with less code than is possible using Python's built-in sequences.
- A growing plethora of scientific and mathematical Python-based packages are using NumPy arrays; though these typically support Python-sequence input, they convert such input to NumPy arrays prior to processing, and they often output NumPy arrays.

Here are the notes from your screenshot, formatted in Markdown:

***

### Reference

1. NumPy Mathematical Functions - [https://numpy.org/doc/stable/reference/routines.math.html](https://numpy.org/doc/stable/reference/routines.math.html)
2. NumPy Universal Functions - [https://numpy.org/doc/stable/reference/ufuncs.html](https://numpy.org/doc/stable/reference/ufuncs.html)

---

### [A] Creating Numpy Arrays
import numpy as np
a = np.array([1,2,3,4,5])
print(a)
print(type(a))

### Creating 2D and 3D array - Check the school Matrix maths
```
1D: ([1,2,3])
2D: ([1,2,3], [3,5,6])
3D: ([1,2,3], [3,5,6], [1,7,0])
```
b = np.arrary([[1,2,3],[4,5,6]])
print(b)

c = np.arrary([[1,2],[4,5], [6,7], [8,9]])
print(c)

#dtype -
np.array([1,2,3],dtype=float)

# np.arrayrange (arange)
d = np.arange(1,100,-2)
print(d)


# Array with shape
e = np.arange(16).reshape(4,4) # to gives the shape in 4 row and 4 coloumn
print(e)
##
f = np.arange(100).reshape(2,10,5) # 2 row 10 coloumn and 5??
print(f)

## 1. Random floats between 0 and 1
arr = np.random.rand(3,4) #  (rows,coloumn)random is function and rand is inside the random . rand by default start from 0-1
print(arr)

## 1. Random integers
arr = np.random.randinit(11,20,size=(4,4)) # this first create 4*4 block then take randinit from 11 - 20



arr = np.arange(1,11),reshape(3,3) # it will work 3*3 = 9 and in arange 1-11 will take 1 to 10 as its in range always be default -1.

arr = np.arange(1,11),reshape(5,2) # it will work

arr = np.arange(1,10),reshape(3,3) # it will work not work due to range 

# Random numbers between any two values (e.g., 10 to 50)
arr = np.random.uniform(10, 50, size=(3, 4)) # in numpy - np, we have random function in that we are using uniform is this method or function?
print(arr) # Generates random floats between 10 and 50.

# Output

# Example with np.random.seed()

import numpy as np

np.random.seed(10)  # Set the random seed

arr1 = np.random.randint(1, 10, size=(3, 3))
print(arr1)

# Output will always be the same, for example:


arr1 = np.random.randint(1, 10, size=(3, 3))
print(arr1)



import numpy as np

np.random.seed(10)  # Set the random seed
# seed is like a milk dary if you mention any number there you will get the same output
# creamy, tonned and thin milk 

arr1 = np.random.randint(1, 10, size=(3, 3))
print(arr1)

# 1, 10 - it will take output between 1 to 10
# will create 3 row and 3 coloum
# np is numpy
# random - select any random number between 1,10 which we define
# see(x) - this is just a referece where get the same value for x if change to y then it will be different, without seed it will change the value. output will be always be the same 

np.random.seed(11)  # Set the random seed
# seed is like a milk dary if you mention any number there you will get the same output
# creamy, tonned and thin milk 

arr1 = np.random.randint(1, 10, size=(3, 3))
print(arr1)

np.random.seed(10)  # Set the random seed
# seed is like a milk dary if you mention any number there you will get the same output
# creamy, tonned and thin milk 

arr1 = np.random.randint(1, 10, size=(3, 3))
print(arr1)

# output - this will be every time change when you run it


# np.linspace : Linear Space between numbers or points
import numpy as np

x = np.linspace(-10, 10, 10, dtype=int)
print(x)

np.linspace(start, stop, num, dtype=int) generates num evenly spaced samples from start to stop (inclusive) as integers.

In the example above, it generates 10 evenly spaced integers between -10 and 10

Output:
[-10  -8  -6  -4  -2   1   3   5   7  10]


y = np.linspace(-10, 10, 10, dtype=int)



### [B] Array Attributes

### [C] Changing Datatype 

### [D] Array Operations
### [E] Array Functions 