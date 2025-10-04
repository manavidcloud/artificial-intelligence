
# AI - Day 3: Functions, Decorators, and Exception Handling

---

## Nested Functions

We can declare a function inside another function. Such functions are called **nested functions**.

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

### Example 2: Calling Inner Function Before Print

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

### Example 3: Return Inner Function

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

## Function Decorators

* A **decorator** is a function which takes another function as argument, **extends its functionality**, and returns the modified function.

📌 **Example analogy:**
We have a room (ordinary function).
A decorator is like a decorator person who enhances the room.
The room remains, but its appearance improves.

---

### Example 1: Without `@decorator`

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

### Example 2: With `@decorator`

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

## Exception Handling

In any programming language, two types of errors are possible:

1. **Compile-time or Syntax errors**
2. **Runtime errors** (exceptions)

An **exception** is:

* An unwanted/unexpected event that disturbs normal flow of program.
* Example: `ZeroDivisionError`, `ValueError`, `TypeError`, `EOFError`, etc.

---

### Without Handling

```python
a = int(input('Enter any number : '))
b = int(input('Enter any number : '))
c = a / b
```

If `b = 0`, we get:

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

## Finally Block

* Always executes cleanup code whether exception occurs or not.
* Example: closing files, releasing resources, etc.

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

## Else Block with Try-Except-Finally

* `else` runs **only if no exception occurs** in the try block.
* `finally` runs always.

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

## User-Defined Exception

Also known as **customized/programmatic exceptions**.
Programmers define and raise them explicitly when needed.

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

📌 Note: `raise` is best for customized exceptions, but not for predefined ones.

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




