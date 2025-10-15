
# 🧠 AI / ML Notes – Day 1 - Python installation and basices 

📅 **Date:** Sept 15

---

## 🐍 Python Setup

### ✅ Install Python

1. Install Python
2. Open **Command Prompt**
3. Run:

   ```bash
   pip install jupyter
   ```
4. Create a **shortcut key** for Jupyter Notebook
5. Change the **Start In path** in shortcut properties

💡 You can also use **Google Colab** instead of local Jupyter.

---

## 🧩 Program Flow

**Input → Process → Output**

---

### 🖥️ Input

Data can come from:

* User Interface
* CSV files
* APIs
* SQL Databases

**Example:**

```python
marks = input('Enter your marks: ')
```

---

## 📦 Data Structures

### 🧮 List

* **Insertion order preserved**
* **Duplicates allowed**
* **Heterogeneous objects allowed** (e.g., `[10, 'apple', 34.5]`)
* **Mutable** – can change elements
* **Dynamic** – can increase or decrease size

**Example:**

```python
lst = [10, 20, 30, 40, 50]
print(lst)
# Output: [10, 20, 30, 40, 50]

lst.append(1000)
lst.pop()
```

---

### 📚 Tuple

* **Immutable** – cannot change after creation
* Supports **packing** and **unpacking**
* A single-element tuple must have a comma → `(10,)`

**Example:**

```python
t1 = 10, 20, 30  # tuple packing
x, y, z = t1     # tuple unpacking
print(x, y, z)
# Output: 10 20 30

t4 = (10, 20, 30)
print(t4)
print(type(t4))
```

> A tuple with one element like `(10)` is not a tuple — it’s an integer.

---

### 🧮 Set

* **Unordered** (no insertion order)
* **No duplicate elements**
* **Mutable**
* Can perform **mathematical operations**

**Example:**

```python
set1 = {10, 20, 30, 40, 50}
print(set1)
# Output: {40, 10, 50, 20, 30}
```

---

### 📘 Dictionary

* Data from APIs often comes in **JSON**, which maps to **Python dictionary**
* **No indexing**
* **Access values by keys**
* **Keys must be unique**

**Example:**

```python
d1 = {'Name': 'Navid', 'Age': 40}
print(d1)
print(d1.keys())
print(d1.values())
print(d1.items())
```

**Find specific values in dictionary:**

```python
for key, value in d1.items():
    if value == 'Mango':
        print(key, value)
```

---

### 🔢 Advanced Data Structures

* **NumPy** → Numerical computations
* **Pandas** → Data manipulation and analysis

---

### 💡 Flask Framework

We can use **Flask** to build small **web applications** for AI/ML models.

---

## ⚙️ Process Module

**Example Calculations:**

```python
result = 10 + 20
print(result)   # 30

result = 10 / 20
print(result)   # 0.5

result = 22 / 7
print(result)   # 3.142857...

result = 22 % 7
print(result)   # 1  (% gives remainder)

result = 2 * 4
print(result)   # 8

result = 2 ** 4
print(result)   # 16 (power operator)
```

---

## 🔢 Indexing

| Index Type        | Direction    | Example          |
| ----------------- | ------------ | ---------------- |
| Positive Indexing | Left → Right | `0, 1, 2, 3`     |
| Negative Indexing | Right → Left | `-4, -3, -2, -1` |

**Example:**

```python
lst = [10, 30, 50, 60]
print(lst[0])   # 10
print(lst[-3])  # 30
```

---

## ✂️ Slice Operator

**Syntax:**

```
list[start : stop : step]
```

**Example:**

```python
lst = [10, 20, 30, 50, 80, 35]
sub_lst = lst[0:3]
print(sub_lst)
# Output: [10, 20, 30]
```

> Slice always goes up to `n-1` (stop is excluded)

---

## 🔁 Reverse a List

```python
lst = [10, 20, 30, 50, 60]
rev_list = lst[::-1]
print(rev_list)
# Output: [60, 50, 30, 20, 10]
```

* **First:** default start of list
* **Second:** default end of list
* **Step (-1):** reverses order

---

### 🔢 More Slice Examples

```python
lst = [10, 20, 30, 50, 60]

print(lst[2:5:1])   # [30, 50, 60]
print(lst[2:5:-1])  # []
print(lst[5:2:-1])  # [60, 50, 30]
print(lst[5:2:1])   # []
```

---

## 🧾 Dictionary Example

```python
d1 = {'empid': 10, 'name': 'Navid'}
print(d1)
print(d1.keys())
print(d1.values())
print(d1.items())
```

---

## 🧮 Set Examples

```python
d1 = {}
print(type(d1))  # <class 'dict'>

s1 = {10, 20, 30}
print(s1)
# Output: {10, 20, 30}

s2 = {10, 20, 30, 10}
print(s2)
# Output: {10, 20, 30}
```

### Set Operations

```python
# Union
s1 | s2  # or s1.union(s2)

# Difference
s1 - s2

# Symmetric Difference
s1 ^ s2  # Elements in s1 or s2, but not both
```

---

## 🧮 Example – Input and Print

```python
marks = input('Enter your marks: ')
print('You scored:', marks)
```

---

## 🧠 Notes Recap

| Concept            | Description                         |
| ------------------ | ----------------------------------- |
| **List**           | Ordered, mutable, allows duplicates |
| **Tuple**          | Ordered, immutable                  |
| **Set**            | Unordered, unique values            |
| **Dictionary**     | Key-value pairs                     |
| **NumPy / Pandas** | Advanced data structures            |
| **Flask**          | For web app deployment              |

---

# 🤖 AI / ML Notes – Day 2 & Day 3 - 📚 **Topic:** Functions, Decorators, and Exception Handling


---

## 🧩 What is a Function?

A **function** is a block of reusable code designed to perform a specific task.

> 💡 If a set of statements is required repeatedly, it’s inefficient to rewrite them.
> Instead, define a **function** once and call it wherever needed.

---

### ✅ Advantages of Functions

* Reduces lines of code
* Improves readability and debugging
* Enhances reusability
* Easy to maintain and extend

---

### 🧠 Example – Reusable Function

```python
def fun():
    print('Hello Python')

fun()
fun()
```

---

## ⚙️ Types of Functions in Python

1. **Built-in Functions** → predefined (e.g. `print()`, `len()`, `type()`)
2. **User-defined Functions** → created by the programmer

---

### 🧮 Example – Built-in Functions

```python
id()
type()
print()
input()
eval()
```

---

### 🧠 Example – User-defined Function

```python
def greet():
    print("Hello from a user-defined function!")

greet()
```

---

## 📦 Function Syntax

```python
def function_name(parameters):
    statements
    return value
```

* `def` → keyword to define a function
* `return` → optional; used to send data back to the caller

---

### Example – Function with Return Value

```python
def addition(a, b):
    return a + b

result = addition(10, 20)
print(result)  # Output: 30
```

If no `return` is used, the function returns `None`.

---

### Example – Return None by Default

```python
def fun():
    print('Hello Python')

print(fun())
# Output:
# Hello Python
# None
```

---

## 🎯 Function Parameters

**Formal Parameters** → variables defined inside the function
**Actual Arguments** → values passed when calling the function

```python
def addition(a, b):
    return a + b

print(addition(10, 20))
print(addition(15, 25))
```

---

## 🔁 Returning Multiple Values

Python allows returning **multiple values** (as a tuple).

```python
def sum_sub(a, b):
    return a + b, a - b

x, y = sum_sub(10, 20)
print('Sum:', x)
print('Sub:', y)
```

---

## ⚙️ Types of Arguments

1. **Positional Arguments**
2. **Keyword Arguments**
3. **Default Arguments**
4. **Variable-Length Arguments**

---

### 1️⃣ Positional Arguments

```python
def sub(a, b):
    print(a - b)

sub(10, 20)
sub(20, 10)
```

---

### 2️⃣ Keyword Arguments

```python
def student_info(rollno, name, marks):
    print('Roll No:', rollno)
    print('Name:', name)
    print('Marks:', marks)

student_info(name='Navid', rollno=9, marks=90)
```

---

### 3️⃣ Default Arguments

```python
def sum(a, b=0):
    return a + b

print(sum(10))
print(sum(10, 20))
```

---

### 4️⃣ Variable-Length Arguments

#### `*args` → multiple positional arguments as tuple

```python
def student_info(*info):
    print('Student Info:')
    for i in info:
        print(i)

student_info(101, 'Rakesh', 400, 'Delhi')
```

#### `**kwargs` → multiple keyword arguments as dictionary

```python
def student_info(**kwargs):
    for key, value in kwargs.items():
        print(f'{key} : {value}')

student_info(rollno=101, name='Rakesh', marks=300, city='Delhi')
```

---

## 🌍 Variable Scope

### 1️⃣ Global Variables

```python
a = 10

def fun1():
    print('a in fun1:', a)

def fun2():
    print('a in fun2:', a)

fun1()
fun2()
```

---

### 2️⃣ Local Variables

```python
def fun1():
    a = 10
    print('Local a:', a)

def fun2():
    print(a)  # Error

fun1()
fun2()
```

---

## 🌐 The `global` Keyword

Used to:

1. Declare a global variable inside a function
2. Modify a global variable within a function

---

### Example – Modify Global Variable

```python
a = 10

def fun1():
    global a
    a = 999
    print('a in fun1:', a)

fun1()
print('a outside:', a)
```

---

### Example – Access Global Variable When Local Exists

```python
a = 10

def fun1():
    a = 999
    print('Local a:', a)
    print('Global a:', globals()['a'])

fun1()
```

---

## 🧠 Nested Functions

We can declare a function inside another function.
Such functions are called **nested functions**.

---

### Example 1

```python
def outer():  # 1. Define outer function
    print('Outer Function started')  # 2. Print from outer

    def inner():  # 3. Define inner function
        print('Inner Function execution')

    print('Outer Function calling Inner Function')
    inner()  # Call inner function

outer()  # Call outer function
````

**Output:**

```
Outer Function started
Outer Function calling Inner Function
Inner Function execution
```

---

### Example 2 – Calling Inner Before Print

```python
def outer():
    print('Outer function started')
    def inner():
        print('Inner function started')
    inner()
    print('Outer function calling Inner function')

outer()
```

---

### Example 3 – Return Inner Function

```python
def outer():
    print('Outer function started')
    def inner():
        print('Inner function started')
    print('Outer function calling Inner function')
    return inner

fun_1 = outer()  # only runs outer()
fun_1()          # now runs inner()
```

* **Explanation:**

  * `outer()` prints outer messages and returns reference to `inner`.
  * `fun_1()` executes the returned `inner()`.

---

## 🎨 Function Decorators

A **decorator** is a function which takes another function as argument,
**extends its functionality**, and returns the modified function.

📌 *Analogy:*
A decorator is like someone who decorates your room —
the structure remains, but its appearance is enhanced.

---

### Example 1 – Without `@decorator`

```python
def ordinary():
    print('I am an ordinary function.....')

def makemepretty(func):  # decorator
    def inner_func():
        print('Now I am pretty')
        func()
    return inner_func()

# Apply decorator manually
pretty = makemepretty(ordinary)
```

---

### Example 2 – With `@decorator`

```python
def makemepretty(func):
    def inner_func():
        print('Now I am pretty')
        func()
    return inner_func

@makemepretty
def NewOrdinary():
    print('I live in Nanded \n', 'Development needed here')
```

**Output:**

```
Now I am pretty
I live in Nanded 
Development needed here
```

---

## ⚠️ Exception Handling

Two kinds of errors:

1. **Compile-time (Syntax errors)**
2. **Runtime errors (Exceptions)**

An **exception** is an unwanted/unexpected event
that disturbs the normal flow of the program.

Examples: `ZeroDivisionError`, `ValueError`, `TypeError`, `EOFError`, etc.

---

### Without Handling

```python
a = int(input('Enter any number : '))
b = int(input('Enter any number : '))
c = a / b
```

If `b = 0`, output:

```
ZeroDivisionError: division by zero
```

---

### With `try-except`

```python
c = 0
try:
    a = int(input('Enter any number : '))
    b = int(input('Enter any number : '))
    c = a / b
except (ZeroDivisionError, ValueError) as msg:
    print('Exception Occurred:', msg)

print('Value of c :', c)
print('Thank you')
```

**Output Example:**

```
Enter any number : 10
Enter any number : 0
Exception Occurred : division by zero
Value of c : 0
Thank you
```

---

### Generic `Exception`

```python
c = 0
try:
    a = int(input('Enter any number : '))
    b = int(input('Enter any number : '))
    c = a / b
except Exception as msg:  # catches all exceptions
    print('Exception Occurred:', msg)

print('Value of c :', c)
print('Thank you')
```

---

## 🧹 Finally Block

Always executes cleanup code whether exception occurs or not.

```python
c = 0
try:
    a = int(input('Enter any number : '))
    b = int(input('Enter any number : '))
    c = a / b
except (ZeroDivisionError, ValueError) as msg:
    print('Exception Occurred:', msg)
finally:
    print('Finally Block : Cleanup Code')

print('Value of c :', c)
print('Thank you ')
```

**Output:**

```
Enter any number : 10
Enter any number : 20
Finally Block : Cleanup Code
Value of c : 0.5
Thank you
```

---

## ✅ Else Block with Try-Except-Finally

* `else` → runs only if no exception occurs
* `finally` → always executes

```python
c = 0
try:
    a = int(input('Enter any number : '))
    b = int(input('Enter any number : '))
    c = a / b
except (ZeroDivisionError, ValueError) as msg:
    print('Exception Occurred:', msg)
else:
    print('Value of c :', c)
finally:
    print('Finally Block : Cleanup Code')

print('Thank you ')
```

**Output:**

```
Enter any number : 10
Enter any number : 20
Value of c : 0.5
Finally Block : Cleanup Code
Thank you
```

---

## 🚨 User-Defined Exception (Custom Exception)

Also known as **customized/programmatic exceptions**.
Defined and raised explicitly by programmers.

```python
class MyException(Exception):  # must inherit from Exception
    def __init__(self, *args):
        self.msg = args

try:
    temp = int(input("Enter Temperature: "))
    if temp < 20:
        raise MyException("Low Temperature")
    print('Temperature is:', temp)
except MyException as msg:
    print("Error:", msg)

print('Thank you ')
```

**Output:**

```
Enter Temperature: 15
Error: ('Low Temperature',)
Thank you
```

📌 Note: `raise` is best for **customized exceptions**,
not for predefined ones.

---

# 🧾 Summary

| Concept                | Description                |
| ---------------------- | -------------------------- |
| **Function**           | Reusable block of code     |
| **Return**             | Sends value back to caller |
| **Args / Kwargs**      | Variable-length arguments  |
| **Global / Local**     | Variable scope control     |
| **Nested Function**    | Function inside another    |
| **Decorator**          | Enhances existing function |
| **Exception Handling** | Controls runtime errors    |
| **Finally / Else**     | Cleanup and success blocks |
| **Custom Exception**   | User-defined runtime error |

---

Would you like me to **export this as a `.ipynb` (Jupyter)** or **`.pdf` study sheet** with a clickable table of contents and highlighted sections next?

---

# Day 4: AI - 28th Sept - 2025 - Regular expression

### Regular Expressions

If a group of strings needs to be represented according to a particular format or pattern, Regular Expressions should be used.

A Regular Expression is a declarative mechanism to describe a group of strings that follow a particular format/pattern.

**Examples:**  
- We can write a regular expression to represent all mobile numbers.  
- We can write a regular expression to represent all email IDs.

**Main application areas of Regular Expressions:**  
1. Developing validation frameworks/validation logic.  
2. Developing pattern matching applications (e.g., ctrl+F in Windows, grep in Unix).  
3. Building translators such as compilers and interpreters.  
4. Creating digital circuits.  
5. Developing communication protocols (TCP/IP, UDP, etc.), such as matching IP addresses (e.g., 192.168.1.101).

Regular Expression-based applications can be developed in Python using the `re` module.

This module provides several built-in functions for using Regular Expressions easily in applications.

#### 1. `compile()`  
- The `re` module provides the `compile()` function, which compiles a pattern into a RegexObject.

#### 2. `finditer()`  
- Returns an iterator that yields Match objects for every match found.

**Example:**  
```python
matcher = pattern.finditer("abaabababa")
```

For the Match object, the following methods can be called:  
- `start()` returns the starting index of the match.  
- `end()` returns the end (index + 1) of the match.  

***  

#### group()  
- `group()` returns the matched string.  

***  

### Example  

```python
import re
count = 0

pattern = re.compile("ab")
matcher = pattern.finditer("abaabababa")

for match in matcher:
    count += 1
    print(match.start(), match.end(), match.group())

print('The number of occurrences:', count)
```

**Output:**  
```
0 2 ab
3 5 ab
5 7 ab
The number of occurrences: 3
```

***  

### Character Classes

Character classes let us search for a group of characters:

| Expression      | Meaning                                          |
|-----------------|-------------------------------------------------|
| [abc]           | Either 'a', 'b', or 'c'                         |
| [^abc]          | Except 'a', 'b', and 'c'                        |
| [a-z]           | Any lowercase alphabet symbol                    |
| [A-Z]           | Any uppercase alphabet symbol                    |
| [0-9]           | Any digit from 0–9                               |
| [a-zA-Z]        | Any alphabetic symbol                            |
| [a-zA-Z0-9]     | Any alphanumeric character                       |
| [^a-zA-Z0-9]    | Except alphanumeric characters (special chars) |  

***  

### Example: Using Character Classes in Regular Expressions  

```python
import re

print('---------------------------------------------')
x = "[abc]"
print('Character Class :', x)

matcher = re.finditer(x, "a7b@k9z")
for match in matcher:
    print(match.start(), '-------', match.group())

print('---------------------------------------------')
x = "[^abc]"
print('Character Class :', x)

matcher = re.finditer(x, "a7b@k9z")
for match in matcher:
    print(match.start(), '-------', match.group())

print('---------------------------------------------')
x = "[a-z]"
print('Character Class :', x)

matcher = re.finditer(x, "a7b@k9z")
for match in matcher:
    print(match.start(), '-------', match.group())
```

***  

### Pre-defined Character Classes  

| Expression   | Description                                                               |
|--------------|---------------------------------------------------------------------------|
| `\s`         | Space character                                                           |
| `\S`         | Any character **except** space character                                  |
| `\d`         | Any digit (**0–9**), e.g., `[0-9]`                                        |
| `\D`         | Any character **except** digit, e.g., `[^0-9]`                            |
| `\w`         | Any word character (alphanumeric + underscore), e.g., `[a-zA-Z0-9_]`      |
| `\W`         | Any character **except** word character (special characters)              |
| `.`          | Any character, including special characters                               |  

***  

### Example  

```python
import re

print('---------------------------------------------')
x = "\s"
print('Pre-defined Character Class :', x)
matcher = re.finditer(x, "a7b k@9z")
for match in matcher:
    print(match.start(), '-------', match.group())

print('---------------------------------------------')
x = "\S"
print('Pre-defined Character Class :', x)
matcher = re.finditer(x, "a7b k@9z")
for match in matcher:
    print(match.start(), '-------', match.group())

print('---------------------------------------------')
x = "\d"
print('Pre-defined Character Class :', x)
matcher = re.finditer(x, "a7b k@9z")
for match in matcher:
    print(match.start(), '-------', match.group())
```

***  

### Quantifiers  

Quantifiers specify how many times a character or group should be matched:

| Pattern  | Meaning                                |
|----------|---------------------------------------|
| `a`      | Exactly one 'a'                       |
| `a+`     | At least one 'a'                      |
| `a*`     | Any number of 'a's including zero     |
| `a?`     | At most one 'a' (zero or one)         |
| `a{m}`   | Exactly m number of 'a's              |
| `a{m,n}` | Minimum m and maximum n number of 'a's|  

**Special note:**  
- `^` checks if the string starts with the given pattern.  
- `$` checks if the string ends with the given pattern.  

***  

### Examples  

```python
import re

print('---------------------------------------------')
x = "a+"
print('Quantifier pattern:', x)
matcher = re.finditer(x, "abaaaaab")
for match in matcher:
    print(match.start(), '-------', match.group())

print('---------------------------------------------')
x = "a*"
print('Quantifier pattern:', x)
matcher = re.finditer(x, "abaaaab")
for match in matcher:
    print(match.start(), '-------', match.group())
```

***  

Continuing the formatted content from where we left off:

***

### Important Functions of the `re` Module

1. `match()`  
2. `fullmatch()`  
3. `search()`  
4. `findall()`  
5. `finditer()` – Returns an iterator yielding Match objects for every match  
6. `sub()`  
7. `subn()`  
8. `split()`  
9. `compile()` – Compiles a pattern into a RegexObject

#### Example: Using `match()` function

```python
import re
str1 = 'ababcabdefg'
s1 = input("Enter Pattern to check: ")
m = re.match(s1, str1)

if m is None:
    print('Match is not available at the beginning of the string.')
else:
    print('Match is available at the beginning of the string.')
```

This code checks whether the pattern exists **at the beginning** of `str1`. If the match is not found, it notifies the user.

***

### 2. `fullmatch()`

- Matches the entire target string against a pattern.
- Returns a Match object if full string matches, else None.

```python
import re

str1 = 'abcd'
s = input("Enter Pattern to check: ")
m = re.fullmatch(s, str1)

if m is not None:
    print('FullMatch is available for the string.')
else:
    print('FullMatch is not available for the string.')
```

***

### 3. `search()`  

- Searches the given pattern anywhere in the string.
- Returns the first Match object if found, else None.

```python
import re

str1 = 'abcabdefg'
s = input("Enter Pattern to check: ")
m = re.search(s, str1)

if m is not None:
    print('First occurrence start index:', m.start(), 'End index:', m.end())
else:
    print('Match not found in the string.')
```

***

### 4. `findall()`  

- Returns a list of all matches found (non-overlapping).

```python
import re

msg = "Python is an easy programming language. Python is good lang"
s1 = input('Enter Search Word: ')

matches = re.findall(s1, msg)
print(matches)
```

Example input `"Python"` outputs:  
```
['Python', 'Python']
```

***

### 5. `findall()` Example to Find Digits

```python
import re

digits = re.findall(r'[0-9]', 'a7b9c5kz')
print(digits)
```

Output:  
```
['7', '9', '5']
```

***

### 6. `sub()` (Substitution)

- Replaces every matched pattern with the specified replacement.

```python
import re

result = re.sub(r'[a-z]', '#', 'a7b9c5kz')
print(result)
```

Output:  
```
#7#9#5#8#
```

***

### 6. `sub()` Example – Interactive Replacement

```python
msg = 'Python is an easy programming language. Python is good language'
import re

s1 = input('Enter Search Word: ')
s2 = input('Enter New Word: ')

result = re.sub(s1, s2, msg)
print(result)
```

***

### 7. `subn()`

- Like `sub()`, but also returns the number of replacements as a tuple.

```python
import re

t = re.subn('[a-z]', '#', 'a7b9c5k8z')
print(t)
print('Result string:', t[0])
print('Number of replacements:', t[1])
```

Output:  
```
('#7#9#5#8#', 5)
Result string: #7#9#5#8#
Number of replacements: 5
```

***

### 1. Regular Expression for 10-digit Mobile Numbers

Rules:  
- Exactly 10 digits.  
- First digit is 7, 8, or 9.

Patterns:  
```python
[7-9][0-9]{9}
# or
(7|8|9)\d{9}
```

***

### 2. Check if String Starts with “r” and Ends with “h”

```python
import re

pattern = r'^r.*h$'
result = re.match(pattern, "rakesh")
print(result is not None)  # True for "rakesh"
```

***

### 3. Valid Email Address Check

```python
import re

def is_valid_email(email):
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def main():
    email = input("Enter an email address: ")
    if is_valid_email(email):
        print("Valid email address")
    else:
        print("Invalid email address")

if __name__ == "__main__":
    main()
```

***

### Extract Mobile Numbers and Email Addresses from File

```python
import re

file = open('Data.txt')
data = file.read()

pattern_mobile = r'[7-9]\d{9}'
mobile_numbers = re.findall(pattern_mobile, data)

pattern_email = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
email_addresses = re.findall(pattern_email, data)

for m in mobile_numbers:
    print(m)
for e in email_addresses:
    print(e)
```

***

Continuing with Object-Oriented Programming (OOP) content formatting:

***

### Python's Object Oriented Programming (OOP): What is a Class?

1. In Python, everything is an object. To create an object, a model or blueprint called a *class* is required.
2. A class represents properties (attributes) and actions (behavior) of objects. For example, `lst.append(40)` uses a method on a list object.
3. Properties are represented by variables.
4. Actions are represented by methods.
5. Therefore, a class contains both variables and methods.

**Example analogy:**  
- Earlier, we prepared food at home.  
- Now, we go out and get food.   
- Similarly, earlier we assembled laptops at home; now, we assemble laptops in the market.

***

### Terminology Example

- Objects like tables, chairs, and mobiles belong to classes such as Furniture and Electronics.
- Furniture class has objects like chairs and tables.
- Mobile class has objects like specific mobile phones.

***

### How to Define a Class

A class is defined using the `class` keyword.

**Syntax:**

```python
class ClassName:
    '''Documentation string'''
    # Variables: instance variables, static variables, local variables
    # Methods: instance methods, static methods, class methods
```

- The documentation string describes the class; it's optional but recommended for clarity.

***

### Accessing Docstring of a Class

```python
print(ClassName.__doc__)
help(ClassName)
```

Example:

```python
list.__doc__
str.__doc__
tuple.__doc__
```

***

### Types of Variables in Python Classes

1. **Instance Variables:** Object-level, unique per instance.  
2. **Static Variables:** Class-level, shared among all instances.  
3. **Local Variables:** Method-level, accessible only within methods.

***

### Types of Methods in Python Classes

1. **Instance Methods:** Operate on instance data.  
2. **Class Methods:** Operate on the class itself, marked with `@classmethod`.  
3. **Static Methods:** No reference to instance or class, marked with `@staticmethod`.

***

### What is an Object?
ex: steave job have one idea like for apple mobile which is in his mind, now he given the mobile or blueprint to users, here mobile is object.

- The physical existence of a class — an instance created from the class blueprint.  
- Any number of objects can be created from a class.

Syntax:

```python
reference_variable = ClassName()
# Example
s = Student()
```

***

### What is a Reference Variable?

- Reference variable refers to an object, allowing access to its properties and methods.

***

### The `self` Variable

- `self` refers to the current instance of the class, similar to `this` in other languages.  
- Used inside constructors (`__init__`) and instance methods to access instance variables and methods.

**Notes:**

1. `self` must be the first parameter in constructors and instance methods.  
2. Example method header:  
```python
def show(self):
    pass
```

***

### Constructor Concept in Python

1. A constructor is a special method `__init__` called automatically when an object is created.  
2. Its main purpose is initializing instance variables.  
3. Must take at least the `self` parameter.  
4. If not provided, Python supplies a default constructor.

Example:

```python
def __init__(self, name, rollno, marks):
    self.name = name
    self.rollno = rollno
    self.marks = marks
```

***

Continuing with formatted content including class examples:

***

## Example: Employee Class with Instance Variables and Methods

```python
class Employee:
    '''This is an example Employee class.'''
    
    def __init__(self, id, nm, sal):
        self.empID = id       # Instance variable
        self.name = nm
        self.salary = sal
    
    def show_empinfo(self):
        print('Employee ID:', self.empID)
        print('Employee Name:', self.name)
        print('Salary:', self.salary)
    
    def get_pf_da_info(self):
        print('PF:', self.salary * 0.10)
        print('DA:', self.salary * 0.15)
```

### Using the Employee Class and Objects

```python
emp1 = Employee(101, 'Navid', 50000)
emp2 = Employee(201, 'Ali', 90000)

print(id(emp1))
print(type(emp1))

emp1.show_empinfo()
emp2.show_empinfo()

emp1.get_pf_da_info()
```

**Explanation:**  
- `self` refers to the current object.  
- Each object `emp1`, `emp2` has its own data.

***

## Example: Bank Class with Static and Instance Variables

```python
class Bank:
    ifsc_code = 98212  # Static variable shared by all instances
    
    def __init__(self, an, nm, bal):
        self.accno = an      # Instance variables unique to each instance
        self.name = nm
        self.balance = bal
    
    def show_acc_info(self):
        print('Account No:', self.accno)
        print('Name of account holder:', self.name)
        print('Balance in the account:', self.balance)
        print('IFSC of your account:', self.ifsc_code)
```

### Using the Bank Class and Objects

```python
ac1 = Bank(1001, 'navid', 48592)
ac2 = Bank(1024, 'bob', 48291)
ac3 = Bank(1234, 'yogesh', 1482)

ac1.show_acc_info()
ac2.show_acc_info()
ac3.show_acc_info()

# Update the static variable for all accounts
Bank.ifsc_code = 2931

ac1.show_acc_info()
ac2.show_acc_info()
ac3.show_acc_info()

# Override static variable for an instance
ac1.ifsc_code = 200
ac1.show_acc_info()
```

***

---

# Day 5: AI/ML - Oct 4, 2025

* setter and getter
* property of class
* decorator example
* over loading
* overriidding

---

## Setter and Getter Methods

We can set and get the values of instance variables by using getter and setter methods.

### Setter Method

Setter methods (also known as mutator methods) are used to set values to instance variables.

**Syntax:**

```python
def setVariable(self, variable):
    self.variable = variable
```

**Example:**

```python
def setRollno(self, rollno):
    self.rollno = rollno
```

---

### Getter Method

Getter methods (also known as accessor methods) are used to get values of instance variables.

**Syntax:**

```python
def getVariable(self):
    return self.variable
```

**Example:**

```python
def getName(self):
    return self.name
```

---

### Class Methods

Inside method implementation, if we are only using class variables (static variables), such type of methods should be declared as class methods.

Declare class method explicitly using `@classmethod` decorator. For class methods, the `cls` variable should be provided at the time of declaration.

Call class methods using class name or object reference.

---

## Example: Without Setter Method

```python
# without setter method
class Product:
    def __init__(self, id, na, co):
        self.p_id = id 
        self.name = na 
        self.cost = co 
    
    def show_product_info(self):
        print('Product ID  : ', self.p_id)
        print('Product Name  : ', self.name)
        print('Product Cost  : ', self.cost)

P1 = Product(101, 'Computer', 50483)
P1.show_product_info()           # This will print product info

P1.cost = 70000
P1.show_product_info()           # This will print product info

P1.cost = -40000
P1.show_product_info()           # This will print product info
```

---

## Example: With Setter Method

```python
# with setter method 
# after apply the setter method to class: set_cost() as to avoid negative value issue

class Product:
    def __init__(self, id, na, co):
        self.p_id = id 
        self.name = na 
        self.cost = co 
    
    def set_cost(self,new_cost):
        if new_cost >= 0:
            self.cost = new_cost
    
    def show_product_info(self):
        print('Product ID  : ', self.p_id)
        print('Product Name  : ', self.name)
        print('Product Cost  : ', self.cost)

# this is initital input 
P2 = Product(201, 'Mouse', 4000)
P2.show_product_info()           # This will print product info

# change the cost using the set
P2.cost = 70000
P1.show_product_info()           # This will print product info

P2.cost = -40000
P1.show_product_info()           # This will print product info
```

---

## Example: With Getter Method

```python
## with gettter method we only featch the values - to validate the class

# after apply the setter method to class: set_cost()

class Product:
    def __init__(self, id, na, co):
        self.p_id = id 
        self.name = na 
        self.cost = co 
    
    def set_cost(self,new_cost):
        if new_cost >= 0:
            self.cost = new_cost
        else:
            print('Eorr: Invalid cost. please provide postivie value')

    def get_cost(self):   # Getter Method
        return self.cost        
    
    def show_product_info(self):
        print('Product ID  : ', self.p_id)
        print('Product Name  : ', self.name)
        print('Product Cost  : ', self.cost)

# this is initital input 
P2 = Product(201, 'Mouse', 4000)
P2.show_product_info()           # This will print product info

# change the cost using the set
P2.set_cost(-70000)
P2.show_product_info()           # This will print product info

# get method
P2.cost = -40000
P2.show_product_info()           # This will print product info
```

---

## Example: Private Instance Variable

```python
## how to make private instanse variable

# after apply the setter method to class: set_cost()
class Product:
    def __init__(self, id, na, co):
        self.p_id = id 
        self.name = na 
        self._cost = co 
    
    def set_cost(self,new_cost):
        if new_cost >= 0:
            self.cost = new_cost
        else:
            print('Eorr: Invalid cost. please provide postivie value')

    def get_cost(self):   # Getter Method
        return self._cost        ## private method 
    
    def show_product_info(self):
        print('Product ID  : ', self.p_id)
        print('Product Name  : ', self.name)
        print('Product Cost  : ', self._cost)

# this is initital input 
P2 = Product(201, 'Mouse', 4000)
P2.show_product_info()           # This will print product info

# change the cost using the set
P2.set_cost(-70000)
P2.show_product_info()           # This will print product info

# get method
P2.cost = -40000
P2.show_product_info()           # This will print product info
```
---

## Properties in Python Class and Objects

In Python, properties in a class are a way to manage access to instance attributes (variables) by defining getter and setter methods.

This allows encapsulation of the internal data and control over how it's accessed or modified.

* you buy a watch and given to fritend direclty but its looks odd, so what you do you wrap it in gift wrap. this is same applicalbe as properties in class.
* by using cost name properties in the class example in the proogram

```python
class Product:
    def __init__(self, id, na, co):
        self.p_id = id 
        self.name = na 
        self._cost = co 
    
    def set_cost(self,new_cost):
        if new_cost >= 0:
            self.cost = new_cost
        else:
            print('Eorr: Invalid cost. please provide postivie value')

    def get_cost(self):   # Getter Method
        return self._cost        ## private method 
    
    def show_product_info(self):
        print('Product ID  : ', self.p_id)
        print('Product Name  : ', self.name)
        print('Product Cost  : ', self._cost)
        
    cost = property(get_cost,set_cost) # cost is properyty in product class

# this is initital input 
P3 = Product(201, 'Mouse', 4000)
P3.show_product_info()           # This will print product info

# with chaning one
P3.cost = 6000
P3.show_product_info()

# negative - it will fail due to setter method
P3.cost = -1000
P3.show_product_info()
```

---

## Property Decorator Method

```python
class Product:
    def __init__(self, id, nm, co):
        self.p_id = id
        self.name = nm
        self._cost = co   # Private Instance Variable...

    @property
    def cost(self):      # Getter Method
        return self._cost

    @cost.setter
    def cost(self, new_cost):   # Setter Method
        if new_cost >= 0:
            self._cost = new_cost
        else:
            print('Error : Invalid Cost. Please provide Positive Value...')

    def show_product_info(self):
        print('Product Id   :', self.p_id)
        print('Product Name :', self.name)
        print('Product Cost :', self._cost)
```

**Usage and Output:**

```python
P1 = Product(101, 'Computer', 50000)
P1.show_product_info()
```

```
Product Id   : 101
Product Name : Computer
Product Cost : 50000
```

```python
P1.cost = -1000
P1.show_product_info()
```

```
Error : Invalid Cost. Please provide Positive Value...
Product Id   : 101
Product Name : Computer
Product Cost : 50000
```

---

## Class Methods & Static Methods

```python
class Bank:
    ifsc_code = 1007   # Static Variable (Class Level Variable)

    def __init__(self, acno, name, bal):
        self.acno = acno
        self.name = name
        self.balance = bal

    def show_acc_info(self):
        print('Account No  :', self.acno)
        print('Name        :', self.name)
        print('Balance     :', self.balance)
        print('IFSC Code   :', self.ifsc_code)

    @classmethod # this is helping for validation and without @ - decorator we are making it to class method from instance method.
    def change_ifsc_code(cls, new_ifsc_code): # we define normal method of class, here cls defining the class so globally its from Bank class so it will change
        cls.ifsc_code = new_ifsc_code
        print('IFSC Code Changed Successfully.')

    @staticmethod
    def check_eligibility(age):
        if age >= 18:
            print('You are eligible to open account')
        else:
            print('You are minor. Please come with parents.')

    @staticmethod # this is like utility method
    def show_ifsc_code():
        print('IFSC Code  :', Bank.ifsc_code)

#
AC1 = Bank(101,'navid',9000)
AC2 = Bank(101,'ali',8000)
AC3 = Bank(101,'bob',7000)

AC1.show_acc_info()
AC2.show_acc_info()
AC3.show_acc_info()

Bank.ifsc_code = 5001 # this is not a good way to change the ifsc code without validation 
AC1.show_acc_info()
AC2.show_acc_info()
AC3.show_acc_info()

Bank.show_acc_info() # this will give an errror becuase its in an instansme method , can't be call by class name direclty

Bank.change_ifsc_code(7001)
AC2.show_acc_info()
AC3.show_acc_info()
```

---

### Static Method Explanation

static method: like bank this will care about employee or customer. but ther eis third party as well that either employee or customer like someone comes to fill the form or come for inquary. like such feature we can allowi using static method

* this allow to come in the bank but can't allow withdraw money
* this one have access to spedific location as well

```python
Bank.check_eligibility(20)
Bank.show_ifsc_code()
```

```
You are eligible to open account
IFSC Code  : 1007
```

* chat gpt give more details here.

---

## Polymorphism

Poly means many.
Morph means forms.

Polymorphism means 'Many Forms'.

Python is implicitly polymorphic.

---

### Eg1:

Yourself is best example of polymorphism. In front of Your parents You will have one type of behaviour and with friends another type of behaviour. Same person but different behaviours at different places, which is nothing but polymorphism.

---

### Eg2:

`+` operator acts as "concatenation" and "arithmetic addition"

---

### Eg3:

`*` operator acts as multiplication and repetition operator

---

### Eg4:

The same method with different implementations in Parent class and child classes (overriding).

```python
a = 10 + 20
print(a)

b = 'abc' + 'xyz'
print(b)

c = 10 * 2
print(c)

d = 'nanded' * 2
print(d)
```

---

## Related to Polymorphism

The following 3 topics are important:

1. Duck Typing Philosophy of Python
2. Overloading

   * Operator Overloading
   * Method Overloading: Unable to overload in python
   * Constractor overloading: unable to loverlod in python
3. Overridding

   * Method overridding
   * contrator overriding

---

## 1. Duck Typing Philosophy of Python

In Python we cannot specify the type explicitly. Based on provided value at runtime the type will be considered automatically. Hence Python is considered as Dynamically Typed Programming Language.

```python
def func1(obj):
    obj.talk()
```

What is the type of obj? We cannot decide at the beginning. At runtime we can pass any type. Then how can we decide the type?

At runtime if 'it walks like a duck and talks like a duck, it must be duck'. Python follows this principle. This is called Duck Typing Philosophy of Python.

---

### Demo Program:

```python
class Duck:
    def talk(self):
        print('Quack.. Quack..')

class Dog:
    def talk(self):
        print('Bow Bow..')

class Cat:
    def talk(self):
        print('Moew Moew ..')

class Goat:
    def talk(self):
        print('Mee Mee ..')

def f1(obj):
    obj.talk()

lst = [Duck(), Cat(), Goat()]
for obj in lst:
    f1(obj)
```

---

ex: you want to go to college in that security guard

* student a comes then security guard ask for what you come student a told for class then he allow

* student b comes then security guard ask for what you come student b told for class then he allow

* same in pyton it will not going to chec spefici class or object its call duck phylosopy

---

## 2. Overloading

* Operator Overloading
* Method Overloading: Unable to overload in python
* Constractor overloading: unable to loverlod in python

---

### 1. Operator Overloading

We can use the same operator for multiple purposes, which is nothing but operator overloading.
Python supports operator overloading.

#### Eg1:

```python
print(10 + 20)      # 30
print('new' + 'delhi')  # newdelhi
```

#### Eg2:

```python
print(10 * 20)      # 200
print('delhi' * 3)  # delhidelhidelhi
```

---

### Demo Program to use `+` operator for our class objects

```python
class Book:
    def __init__(self, pages):
        self.pages = pages
```

---

### Program with Error

```python
class Book:
    def __init__(self,pages):
        self.pages=pages

b1=Book(100)
b2=Book(200)

print(b1+b2)
```

**Output:**

```
TypeError: unsupported operand type(s) for +: 'Book' and 'Book'
```

---

### Fix with Operator Overloading

```python
# Demo program to overload + operator for our Book class objects:
class Book:
    def __init__(self, pages, name, cost):
        self.name = name
        self.pages = pages
        self.cost = cost

    def __add__(self, other):  # b1+b2 is calling to __add__ (magical method)
        return self.cost + other.cost

b1 = Book(100, 'C Programming', 500)
b2 = Book(200, 'Java', 700)

total_cost = b1.cost + b2.cost
print('Total No. of Pages ', b1 + b2) # b1+b2 - it also called dundle method
```

---

**Notes:**

* b1+b2 = + must have either integer number of 'a' + 'b' string
* so it will check if it have any dundle method define def `__add__` method
* self holding b1 as it inter method and first one.

`+` works with existing datatype but if it get user defined datatype → it checks `__add__`.

* ex: `b1+b2 = b1.__add__(b2)` → here b1=self and other=b2
* this works with two object only
* this also works with list and tuple
* with existing code its ignoring

---

### List of Magic Methods for Operators

```
+   ---> object.__add__(self, other)
-   ---> object.__sub__(self, other)
*   ---> object.__mul__(self, other)
/   ---> object.__div__(self, other)
//  ---> object.__floordiv__(self, other)
%   ---> object.__mod__(self, other)
**  ---> object.__pow__(self, other)
+=  ---> object.__iadd__(self, other)
-=  ---> object.__isub__(self, other)
*=  ---> object.__imul__(self, other)
/=  ---> object.__idiv__(self, other)
//= ---> object.__ifloordiv__(self, other)
%=  ---> object.__imod__(self, other)
**= ---> object.__ipow__(self, other)
<   ---> object.__lt__(self, other)
<=  ---> object.__le__(self, other)
>   ---> object.__gt__(self, other)
>=  ---> object.__ge__(self, other)
==  ---> object.__eq__(self, other)
!=  ---> object.__ne__(self, other)
```

---

### Program with Error

```python
b1=Book(100, 'C Programming, 500)
b2=Book(200, 'Java',700)
b3 = Book (300, 'Python',900)
total cost b1.cost+b2.cost print('Total No. of Pages ',b1+b2)
total cost b1 +62 +b3 print(total_cost)
```

**Output:**

```
Total No. of Pages 1200
TypeError
Cell In[22], line 22
19 total cost = b1.cost+b2.cost
Traceback (most recent call last)
20 print('Total No. of Pages ',b1+b2)
---> 22 total cost = b1b2+b3
23 print(total_cost)
TypeError: unsupported operand type(s) for +: 'int' and 'Book'
```

---

### Fix

```python
class Book:
    def __init__(self, pages, name, cost):
        self.name = name
        self.pages = pages
        self.cost = cost

    def __add__(self, other):
        if isinstance(other, Book):
            return Book(self.pages + other.pages,
                        self.name + ' & ' + other.name,
                        self.cost + other.cost)
        return self.cost + other.cost  # This line may not work as intended if 'other' isn't a Book

b1 = Book(100, 'C Programming', 500)
b2 = Book(200, 'Java', 700)
b3 = Book(300, 'Python', 900)

# Adding cost directly works, but for chained addition, __add__ must return a Book object
total_cost = b1 + b2 + b3
print('Total No. of Pages:', total_cost.pages)
print('Total Cost:', total_cost.cost)

# If you want to print info about the combined object, add a __str__ method to Book
def __str__(self):
    return f"Total No. of Pages: {self.pages}\nTotal Cost: {self.cost}\nBooks: {self.name}"

Book.__str__ = __str__

print(total_cost)
```

---

### Same Program in Different Way

```python
class Book:
    def __init__(self, pages, name, cost): # constrative call. 
        self.name = name
        self.pages = pages
        self.cost = cost

    def __add__(self, other):
        if isinstance(other, Book):
            # return Book(self.pages + other.pages,
            #             self.name + ' & ' + other.name,
            #             self.cost + other.cost)
            return Book('','',self.cost + other.cost)            
        return self.cost + other.cost  # This line may not work as intended if 'other' isn't a Book

b1 = Book(100, 'C Programming', 500)
b2 = Book(200, 'Java', 700)
b3 = Book(300, 'Python', 900)

total_cost = b1 + b2

# print('Total No. of Pages:', total_cost.pages)
print('Total Cost:', total_cost.cost)

total_cost = b1 + b2 + b3
# this will used bodomust mass of math right to left b2+b3 (self,other as arugment) then its checkg if its boject using __add__ magical method
# once its solved or go return (return like which we mention self.cost + other cost this will contain the final value of b2+b3)
# later it will do like b1 + value which we got and perfrom the same to get the final value. 

# print('Total No. of Pages:', total_cost.pages)
print('Total Cost:', total_cost.cost)
```

---

## Method Overloading

* same name of function but different argument

ex:

1. define funct(a,b)
2. define fun(a,b,c)
3. define fun(a,b,c,d)

* same name with multiple forms.

* but in python this is not allow as python work on object base.

* hence funtion can refer later object only. method overloading not allowed.

---

## Constructor Overloading

Constractor overloading: unable to loverlod in python

---

## Python Inheritance

Inheritance enables us to define a class that takes all the functionality from a parent class and allows us to add more.

In this class, you will learn to use inheritance in Python.

Inheritance in Python is a powerful feature in object-oriented programming.

It refers to defining a new class with little or no modification to an existing class. The new class is called derived (or child) class and the one from which it inherits is called the base (or parent) class.

ex:

* one team was working but they left the organiszation
* now if you know the inheritance (like existing project) you can resume to work
* inhetircan : what we have we will use it as well as what is missing we will add this as well.
* we wiill create class in class.

---


# Day 6 - AI/ML - Oct 5, 2025 - Inheritance 

## Python Inheritance

Inheritance enables us to define a class that takes all the functionality from a parent class and allows us to add more.  
In this class, you will learn to use inheritance in Python.

**Inheritance in Python**  
Inheritance is a powerful feature in object-oriented programming.  

It refers to defining a new class with little or no modification to an existing class.  
The new class is called **derived (or child)** class and the one from which it inherits is called the **base (or parent)** class.

---

## Python Inheritance Syntax

```python
class BaseClass:
    # Body of base class

class DerivedClass(BaseClass):
    # Body of derived class
````

* Derived class inherits features from the base class where new features can be added to it.
* This results in re-usability of code.

---

## Example of Inheritance in Python

To demonstrate the use of inheritance, let us take an example.

```python
class Person:
    def __init__(self):
        self.age = 0
        self.name = ''
        self.location = ''

    def get_person_info(self):
        self.age = int(input('Age : '))
        self.name = input('Name : ')
        self.location = input('Location : ')

    def show_person_info(self):
        print('Name     :', self.name)
        print('Age      :', self.age)
        print('Location :', self.location)

class Student(Person):
    def __init__(self):
        super().__init__()
        self.rollno = 0
        self.marks = 0

    def get_student_info(self):
        self.rollno = int(input('Roll no : '))
        self.marks = int(input('Marks : '))

    def show_student_info(self):
        print('Roll no  :', self.rollno)
        print('Marks    :', self.marks)
```

---

### Parent class block

```python
class Person:
    def __init__(self):
        self.age = 0
        self.name = ''
        self.location = ''

    def get_person_info(self):  # this will get info from user 
        self.age = int(input('Age : '))
        self.name = input('Name : ')
        self.location = input('Location : ')

    def show_person_info(self):  # what entered using get_person_info it will display 
        print('Name     :', self.name)
        print('Age      :', self.age)
        print('Location :', self.location)
        

P = Person()
P.get_person_info()
P.show_person_info()
```

---

### Student program (without inheritance)

```python
class Student:
    def __init__(self):
        self.age = 0
        self.name = ''
        self.location = ''
        self.rollno = 0
        self.marks = 0

    def get_person_info(self):
        self.age = int(input('Age : '))
        self.name = input('Name : '))
        self.location = input('Location : '))
        self.rollno = int(input('Roll no : '))
        self.marks = int(input('Marks : '))  # Typo corrected

    def show_person_info(self):
        print(f'\nAge      : {self.age}')
        print(f'Name     : {self.name}')
        print(f'Location : {self.location}')
        print(f'Roll No  : {self.rollno}')
        print(f'Marks    : {self.marks}')
        
        
S = Student()
S.get_person_info()
S.show_person_info()
```

---

## Inheritance program with parent class

```python
class Person:
    def __init__(self):
        self.age = 0
        self.name = ''
        self.location = ''

    def get_person_info(self):
        self.age = int(input('Age : '))
        self.name = input('Name : ')
        self.location = input('Location : ')

    def show_person_info(self):
        print(f'\nAge      : {self.age}')
        print(f'Name     : {self.name}')
        print(f'Location : {self.location}')


class Student(Person):
    def __init__(self):
        super().__init__()
        self.rollno = 0
        self.marks = 0

    def get_student_info(self):
        self.rollno = int(input('Roll no : '))
        self.marks = int(input('Marks : '))

    def show_student_info(self):
        print(f'Roll no  : {self.rollno}')
        print(f'Marks    : {self.marks}')


# Usage
s = Student()
s.get_person_info()
s.get_student_info()
s.show_person_info()
s.show_student_info()
```

**Explanation:**
`s = Student()` has its own information like `rollno` and `marks`.
But as we are using the parent class, it will also include `age`, `name`, and `location` from the parent.

---

## Types of Inheritance in Python

1. Single Inheritance
2. Multiple Inheritance
3. Multi-Level Inheritance
4. Hierarchical Inheritance
5. Hybrid Inheritance

---

### 1. Single Inheritance

In this type of inheritance, we have **one base/parent class** and **one derived/child class**.

classDiagram
    Parent <|-- Child
    class Parent {
        <<Base Class>>
    }
    class Child {
        <<Derived Class>>
    }

classDiagram
    Parent <|-- Child
    class Parent
    class Child

---

### 2. Multiple Inheritance

In this type of inheritance, we have **more than one base class** and **only one derived class**.

classDiagram
    Base1 <|-- Derived
    Base2 <|-- Derived

    class Base1 {
        <<Base Class>>
    }
    class Base2 {
        <<Base Class>>
    }
    class Derived {
        <<Derived Class>>
    }


classDiagram
    BaseClass1 <|-- DerivedClass
    BaseClass2 <|-- DerivedClass


---

### Example of Multiple Inheritance in Python

```python
class Customer:
    cust_id
    name
    location

class Product:
    product_id
    name
    cost

class Order(Customer, Product):
    order_id
    quantity
    total_cost
```

---

```python
# Parent Class 1
class Customer:
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def customer_details(self):
        print(f"Customer Name: {self.name}")
        print(f"Email: {self.email}")

# Parent Class 2
class Product:
    def __init__(self, product_name, price):
        self.product_name = product_name
        self.price = price

    def product_details(self):
        print(f"Product: {self.product_name}")
        print(f"Price: ₹{self.price}")

# Derived class (child class)        
class Order(Customer, Product):
    def __init__(self, name, email, product_name, price, quantity):
        # Initialize both parent classes
        Customer.__init__(self, name, email)
        Product.__init__(self, product_name, price)
        self.quantity = quantity

    def order_summary(self):
        print("\n--- ORDER SUMMARY ---")
        self.customer_details()
        self.product_details()
        print(f"Quantity: {self.quantity}")
        print(f"Total Amount: ₹{self.price * self.quantity}")

# Create an order
order1 = Order("Navid", "md.navid@example.com", "Playstation", 90000, 4)
order1.order_summary()
```

---

### Notes

* `__init__()` → Constructor to initialize the class.
* `self` → Refers to the current instance of the class.

---

## Super keyword in class and object Python

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def show_details(self):
        print(f"Name: {self.name}")
        print(f"Age: {self.age}")

# Child class inheriting from Person
class Employee(Person):
    def __init__(self, name, age, emp_id, salary):
        # use super() to call parent constructor
        # Person.__init__(self, name, age) # either pass using class name or use super keyword
        super().__init__(name, age)
        self.emp_id = emp_id
        self.salary = salary

    def show_details(self):
        # use super() to call parent method
        super().show_details()
        print(f"Employee ID: {self.emp_id}")
        print(f"Salary: ₹{self.salary}")

# Create an object
emp1 = Employee("Navid", 40, "x102", 90000)
emp1.show_details()
```

---

## Super Example 2

```python
# Parent Class 1
class Customer:
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def customer_details(self):
        print(f"Customer Name: {self.name}")
        print(f"Email: {self.email}")

# Parent Class 2
class Product:
    def __init__(self, product_name, price):
        self.product_name = product_name
        self.price = price

    def product_details(self):
        print(f"Product: {self.product_name}")
        print(f"Price: ₹{self.price}")

# Derived class (child class)        
class Order(Customer, Product):
    def __init__(self, name, email, product_name, price, quantity):
        # Initialize both parent classes using super()
        super().__init__(name, email)  # calls Customer's __init__ due to MRO
        # NOTE: In multiple inheritance, `super()` only calls the next class in MRO chain
        self.product_name = product_name
        self.price = price
        self.quantity = quantity

    def order_summary(self):
        print("\n--- ORDER SUMMARY ---")
        self.customer_details()
        self.product_details()
        print(f"Quantity: {self.quantity}")
        print(f"Total Amount: ₹{self.price * self.quantity}")


# Create an order
order1 = Order("Navid", "md.navid@example.com", "Playstation", 90000, 4)
order1.order_summary()
```

---

## Method Resolution Order (MRO)

**MRO Algorithm:**
If head element of first list not present in the tail part of any other list,
then consider that element in the result and remove that element from all the lists.

Example:

```python
class A:
    def m1(self):
        print('Method of Class A')

class B(A):
    def m1(self):
        print('Method of Class B')

obj = B()
obj.m1()                 # Output: Method of Class B
print(B.mro())           # Output: [<class '__main__.B'>, <class '__main__.A'>, <class 'object'>]
```

---

### Example without MRO

```python
class A:
    def m1(self):
        print('A Class Method')

    def m3(self):
        print('A Class Method')

class B(A):
    def m1(self):
        print('B Class Method')
        
    def m3(self):
        print('B Class Method')

class C:
    def m1(self):
        print('C Class Method')

    def m3(self):
        print('C Class Method')

class X(A, B):
    def m1(self):
        print('X Class Method')

    def m2(self):
        print('X Class Method')

class Y(B, C):
    def m1(self):
        print('Y Class Method')

    def m2(self):
        print('Y Class Method')

class P(X, Y, C):
    def m1(self):
        print('P Class Method')


obj = P()
obj.m1()
obj.m2()  # this will call X class and override Y class
obj.m3()  # this will call A class method

print(P.mro())  # it will show the MRO 
```

---

### How MRO Works (Example)

```
mro(P) = P + merge(mro(X), mro(Y), mro(C), XYC)
       = P + merge(XABO, YBCO, CO, XYC)
       = P + X + merge(ABO, YBCO, CO, YC)
       = P + X + A + merge(BO, YBCO, CO, YC)
       = P + X + A + Y + merge(BO, BCO, CO, C)
       = P + X + A + Y + B + merge(O, CO, CO, C)
       = P + X + A + Y + B + C + merge(O, O, O)
       = P + X + A + Y + B + C + O
```

---

### Using `super()` with MRO Example

```python
class A:
    def m1(self):
        print('Method of Class A')

class B:
    def m1(self):
        print('Method of Class B')

class C(A, B):
    def m1(self):
        super().m1()           # Calls m1 from A (first in MRO)
        super(A, self).m1()    # Calls m1 from B (the next after A in MRO)

obj = C()
obj.m1()
```

**Output:**
 
```
Method of Class A
Method of Class B
```

This shows how `super()` can be used to chain method calls in multiple inheritance,
traversing the **Method Resolution Order (MRO)**.

---

# Types of data used for I/O:
- Text: '12345' as a sequence of unicode chars
- Binary: 12345 as a sequence of bytes of its binary equivalent

Hence there are 2 file types to deal with
- Text files – All program files are text files
- Binary files – Images, music, video, exe files

# How File i/o



# create and Writing to a file 
```python
# case 1 - if the file is not present
f = open('sample.txt', 'w') # this will create a file
f.write('Hello world') # this will add the details in file
f.close() # this file is close the file

# since file is closed hence this will not work
f.write('hello')
```
---

# this will overwrite the data in the file
# write multiline strings
```python
f = open('sample.txt', 'w')
f.write('hello world')
f.write('\nhow are you?')
f.close()
```
---
# append text into existing file
```python
f = open('sample.txt', 'a')
f.write('\nHi, Technical Guftgu')
f.write('\nhow are you?')
f.close()
```
---

# write lines
L = ['hello\n', 'hi\n', 'how are you\n', 'I am fine']

f = open('/content/temp/sample.txt', 'w')
f.writelines(L)
f.close() # this will close the file from pvm. 

# if we have list then we will use writeline and if we have string we will use write function


### Read from file
f = open('sample.txt', 'r')
data = f.read()
print(data)
f.close()


# readline() read a single at a time.

f = open('sample.txt', 'r')
print(f.readline())
print(f.readline())
print(f.readline())
print(f.readline())

# readlines() read a all the lines.
# readlines()
f = open('sample.txt', 'r')  # 'r' read mode
for line in f.readlines():
    print(line)
print('----------------------')


- **Serialization** is the process of converting Python data types to JSON format.
- **Deserialization** is the process of converting JSON to Python data types.

The image also answers "What is JSON?" by showing a JSON structure example:

```json
{
  "results": [
    {
      "__metadata": {
        "type": "EmployeeDetails;Employee"
      },
      "UserID": "E12012",
      "RoleCode": "35"
    }
  ]
}
```

without json + dictironay




with json + dictory to fix the issue - this only read the file
import json

product_info = {101: 'Apple', 102: 'Orange', 103: 'Kiwi'}

with open('ProductList.json', 'w') as f: # with - this will open and close the file once the block completed. 
    json.dump(product_info, f)

Output:

root
  apple
  orangle
  kiwi

Using Context Manager (With)
- It's a good idea to close a file after usage as it will free up the resources.
- If we don't close it, garbage collector would close it.
- with keyword closes the file as soon as the usage is over


# writing in the file
import json
with_open('ProductionList.json, 'r') as f:
P_dict = json.load(f)
print(P_dict)
print(type(P_dict))


P_dict['102']

#output


ex:  i have to buy a furtuniture and i have space to take that furniture as well. however from the road its coming it don't have much space. so furthrniture is going to sealization and deserialization at you home

Json only helping until list, dic string but is going to fail on your class and object
- user defined class where json going to fail to bind
-

## examples 
Json -> pickle -> jlib

1. this program is going to fail
class Person:
    def __init__(self):
        self.age = 0
        self.name = ''
        self.location = ''

    def get_person_info(self):
        self.age = int(input('Age : '))
        self.name = input('Name : ')
        self.location = input('Location : ')

    def show_person_info(self):
        print(f'\nAge       : {self.age}')
        print(f'Name      : {self.name}')
        print(f'Location  : {self.location}')

P = Person()
P.get_person_info()
P.show_person_info()


import json


2. pickling

The image provides definitions for pickling in Python:

- **Pickling** is the process whereby a Python object hierarchy is converted into a byte stream.
- **Unpickling** is the inverse operation, where a byte stream (from a binary file or bytes-like object) is converted back into an object hierarchy.[1]



import pickle
with open(person.pkl, 'wb') as f:
    pickle.dump(P.f)


import pickle
with open(person.pkl, 'rb') as f:
    D = pickle.load(f)

D.show_person_info()

print(D)
dir(D)


---


# 🧠 Day 7 - Oct 11th  2025

## 1. Joblib

### Installation

```bash
pip install joblib
```

### Example

```python
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
```

### Serialize Model with Joblib

```python
from joblib import dump

# Save model to file
dump(model, "linear_model.joblib")
print("Model saved successfully!")
```

---

## 2. NumPy

### Installation

```bash
pip install numpy
```

### Configure Correct Interpreter in VS Code

1. Run:

   ```bash
   python -m pip show numpy
   ```

   → Note the installation path.
2. Open VS Code → **Ctrl + Shift + P**
3. Search **“Python: Select Interpreter”**
4. Choose the **Global** interpreter (not recommended one if virtual).
5. Re-run the program to ensure NumPy is recognized.

---

### 🧩 What is NumPy?

NumPy is the **core package for numerical computing in Python**.
It provides:

* The **ndarray object** — n-dimensional arrays of uniform data type.
* Fast mathematical operations (vectorized).
* Tools for linear algebra, statistics, random numbers, etc.

---

### 🔍 NumPy Arrays vs Python Lists

| Feature   | NumPy Array             | Python List          |
| --------- | ----------------------- | -------------------- |
| Size      | Fixed                   | Dynamic              |
| Data Type | Homogeneous             | Heterogeneous        |
| Speed     | Very fast (C optimized) | Slower               |
| Memory    | Compact                 | High memory overhead |

---

## [A] Creating NumPy Arrays

```python
import numpy as np

# 1D Array
a = np.array([1, 2, 3, 4, 5])
print(a)
print(type(a))
```

### 2D and 3D Arrays

```python
b = np.array([[1, 2, 3], [4, 5, 6]])
c = np.array([[1, 2], [4, 5], [6, 7], [8, 9]])
```

### Specify Datatype

```python
np.array([1, 2, 3], dtype=float)
```

### Using `arange`

```python
d = np.arange(1, 100, 2)
```

### Reshape Arrays

```python
e = np.arange(16).reshape(4, 4)
f = np.arange(100).reshape(2, 10, 5)
```

---

## Random Numbers

```python
# Random floats (0–1)
arr = np.random.rand(3, 4)

# Random integers
arr = np.random.randint(11, 20, size=(4, 4))

# Random floats between two numbers
arr = np.random.uniform(10, 50, size=(3, 4))
```

### Using Seed

```python
np.random.seed(10)
arr1 = np.random.randint(1, 10, size=(3, 3))
print(arr1)
```

> Seed ensures the same random numbers each run.

---

## Using `linspace`

```python
x = np.linspace(-10, 10, 10, dtype=int)
print(x)
```

→ Generates **10 evenly spaced numbers** between -10 and 10.

---

## [B] Array Attributes

```python
import sys, numpy as np

a1 = np.arange(10, dtype=np.int32)
print('Memory usage:', sys.getsizeof(a1))
print(a1.size)        # number of elements
print(a1.itemsize)    # bytes per element
print(a1.shape)       # dimensions
```

---

## [C] Changing Datatype

```python
a2 = np.arange(12, dtype=float).reshape(3, 4)
print(a2.dtype)
a2 = a2.astype(np.int32)
print(a2.dtype)
```

---

## [D] Array Operations

```python
a1 = np.arange(12).reshape(3, 4)
a2 = np.arange(12, 24).reshape(3, 4)
```

### Scalar Operations

```python
a1 ** 2
a2 == 15
```

### Vector Operations

```python
x = np.array([[1, 2], [3, 4]])
y = np.array([[5, 6], [7, 8]])
print(np.power(x, y))
```

---

## [E] Array Functions

```python
a1 = np.random.random((3, 3))

np.max(a1)
np.max(a1, axis=0)  # column-wise
np.max(a1, axis=1)  # row-wise
```

Other Functions:

```python
np.min(a1)
np.sum(a1)
np.prod(a1)
np.mean(a1)
np.std(a1)
np.var(a1)
```

### Dot Product

```python
a2 = np.arange(12).reshape(3, 4)
a3 = np.arange(12, 24).reshape(4, 3)
np.dot(a2, a3)
```

---

### Log & Exponentials

```python
np.log(a1)
np.exp(a1)
```

### Rounding

```python
np.round(a1)
np.ceil(a1)
np.floor(a1)
```

---

## Indexing & Slicing

```python
a1 = np.arange(10)
a2 = np.arange(12).reshape(3, 4)
a3 = np.arange(8).reshape(2, 2, 2)
```

### 1D

```python
a1[5]
```

### 2D

```python
a2[0, 3]
```

### 3D

```python
a3[1, 0, 1]
```

### Slicing

```python
arr = np.arange(20)
arr[2:15:2]
```

---

## Iteration

```python
for i in np.nditer(a3):
    print(i)
```

---

## Reshaping & Combining

```python
a2 = np.arange(12).reshape(3, 4)
a2.reshape(4, 3)
a2.T          # Transpose
a2.ravel()    # Flatten
```

### Stacking

```python
np.hstack((a4, a5))
np.vstack((a4, a5))
```

### Splitting

```python
a1, a2 = np.hsplit(a4, 2)
a1, a2, a3 = np.vsplit(a4, 3)
```

---

## Python Lists vs NumPy Arrays (Performance)

### Python List

```python
a = [i for i in range(1000000)]
b = [i for i in range(1000000, 2000000)]

import time
start = time.time()
c = [a[i] + b[i] for i in range(len(a))]
print(time.time() - start)
```

### NumPy Array

```python
import numpy as np, time
a = np.arange(1000000)
b = np.arange(1000000, 2000000)

start = time.time()
c = a + b
print(time.time() - start)
```

### Memory

```python
import sys
a = [10 for i in range(1000000)]
sys.getsizeof(a)

c = np.arange(1000000)
sys.getsizeof(c)
```

---

## [F] Advanced Indexing

### Fancy Indexing

```python
a = np.arange(24).reshape(6,4)
print(a[[0, 2, 3, -1]])   # select rows
print(a[:, [0, 2, 3]])    # select columns
```

### Boolean Indexing

```python
a = np.random.randint(1, 100, 24).reshape(6, 4)
a[a > 50]                     # elements > 50
a[(a > 50) & (a % 2 == 0)]    # even & >50
a[~(a % 7 == 0)]              # not divisible by 7
```

---

## [G] Broadcasting

Broadcasting allows arithmetic operations on arrays of **different shapes**.

### Example 1: Same Shape

```python
a = np.arange(6).reshape(2,3)
b = np.arange(6,12).reshape(2,3)
print(a + b)
```

### Example 2: Different Shape

```python
a = np.arange(6).reshape(2,3)
b = np.arange(3).reshape(1,3)
print(a + b)
```

### Example 3: Column Broadcasting

```python
x = np.arange(6).reshape(3,2)
y = np.arange(3).reshape(3,1)
print(x + y)
```

---

## Broadcasting Rules

1. Make both arrays have **same number of dimensions**.
2. Sizes must be **equal** or one of them must be **1**.

### Examples

```python
np.arange(3) + 5
np.ones((3,3)) + np.arange(3)
np.arange(3).reshape((3,1)) + np.arange(3)
```

---
