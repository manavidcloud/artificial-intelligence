
***

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
Here is a polished version of your "image.jpg" content with improved clarity and formatting:

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
- Characgter class gives under [] ex. [abc]
Character classes let us search for a group of characters:

| Expression      | Meaning                                         |
|-----------------|------------------------------------------------|
| [abc]           | Either 'a', 'b', or 'c'                        |
| [^abc]          | Except 'a', 'b', and 'c'                       |
| [a-z]           | Any lowercase alphabet symbol                   |
| [A-Z]           | Any uppercase alphabet symbol                   |
| [0-9]           | Any digit from 0–9                              |
| [a-zA-Z]        | Any alphabetic symbol                           |
| [a-zA-Z0-9]     | Any alphanumeric character                      |
| [^a-zA-Z0-9]    | Except alphanumeric characters (special chars)  |

***

Here’s a polished and formatted version of the Python code and explanation from your image:

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


Here is a clear and polished version of the content from your image about pre-defined character classes in Python regular expressions, with improved formatting and comments:

***

### Pre-defined Character Classes

| Expression   | Description                                                                     |
|--------------|---------------------------------------------------------------------------------|
| `\s`         | Space character                                                                 |
| `\S`         | Any character **except** space character                                        |
| `\d`         | Any digit (**0–9**), e.g., `[0-9]`                                              |
| `\D`         | Any character **except** digit, e.g., `[^0-9]`                                  |
| `\w`         | Any word character (alphanumeric + underscore), e.g., `[a-zA-Z0-9_]`            |
| `\W`         | Any character **except** word character (special characters), e.g., `[^a-zA-Z0-9_]` |
| `.`          | Any character, including special characters                                     |

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

This code uses the most common pre-defined character classes (`\s`, `\S`, `\d`) to find space characters, non-space characters, and digits within the string `"a7b k@9z"`, printing their positions and matched characters. If you want output examples for each, just ask!

- Regular expression have its site, if you add the details it will add the and give you the patttern 



***

### Quantifiers
- it will check number of occursance of charcater number of occurance or repetation 
Quantifiers specify how many times a character or group should be matched:

| Pattern     | Meaning                                                        |
|-------------|----------------------------------------------------------------|
| `a`         | Exactly one 'a'                                                |
| `a+`        | At least one 'a'                                               |
| `a*`        | Any number of 'a's including zero                              |
| `a?`        | At most one 'a' (zero or one)                                  |
| `a{m}`      | Exactly m number of 'a's                                       |
| `a{m,n}`    | Minimum m and maximum n number of 'a's                         |

**Special note:**
- `^` checks if the string starts with the given pattern.
- `$` checks if the string ends with the given pattern.

***

Chatgpt add example of each and shows the output as well for better understanding

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

This demonstrates the use of `a+` (at least one 'a') and `a*` (zero or more 'a's) to find matches in the test strings. Each match's position and matched group are printed in the output. If you want more detailed output explanation or examples for other quantifiers, let me know!


import re # refrecne class module

print('---------------------------------------------') # normal print() function
x = "a+" # quantifier input and find a here
print('Quantifier pattern:', x) # print statement
matcher = re.finditer(x, "abaaaaab") # what is matcher and finditer please help chatgpt?
for match in matcher:
    print(match.start(), '-------', match.group())

# Output of a+ program
    
import re # refrecne class module

print('---------------------------------------------') # normal print() function
x = "a*" # quantifier input and find a here
print('Quantifier pattern:', x) # print statement
matcher = re.finditer(x, "abaaaaab") # what is matcher and finditer please help chatgpt?
for match in matcher:
    print(match.start(), '-------', match.group())    
    
    
# output of a* program -     




import re

msg = 'Python is an easy programming language'

print('\n...................................')
x="^python"
print("pre-defined character class: ", x)
matcher = re.finditer(x,msg)
for match in matcher:
    print(match.start(),'-----------',match.group())


Here is a polished and organized version of your image's content, including code examples, quantifier output, and an overview of important `re` module functions:

***

### Quantifier Example (`a{2,3}`)

```python
import re

x = "a{2,3}"
print('\n---------------------------------------------')
print('Pre-defined Character Class :', x)
matcher = re.finditer(x, "abaaaaaabxyzaapaaapaaakaa")
for match in matcher:
    print(match.start(), '-------', match.group())
```

**Sample Output:**
```
2 ------- aa
4 ------- aaa
13 ------- aa
15 ------- aaa
20 ------- aa
```
This shows all occurrences of **two or three consecutive 'a'** characters in the string.

***

### Usage of `^` and `$`  
`^` checks if the string starts with a pattern; `$` checks if it ends with a pattern.

```python
import re

msg = 'Python is an easy programming language'
x = "^easy$"
print('\n---------------------------------------------')
print('Pre-defined Character Class :', x)
matcher = re.finditer(x, msg)
for match in matcher:
    print(match.start(), '-------', match.group())
```

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
s1 = input("Enter Pattern to check : ")
m = re.match(s1, str1)
if m is None:
    print('Match is not available at the beginning of the string.')
else:
    print('Match is available at the beginning of the string.')
```

This code checks whether the pattern exists **at the beginning** of `str1`. If the match is not found, the user is informed accordingly.

***


***

### 2. `fullmatch()`

- The `fullmatch()` function matches the entire target string against the given pattern.
- If the full string matches, it returns a Match object; otherwise, it returns `None`.

```python
import re

str1 = 'abcd'
s = input("Enter Pattern to check: ")
m = re.fullmatch(s, str1)

if m is not None:
    print('FullMatch is available at the beginning of the string.')
else:
    print('FullMatch is not available at the beginning of the string.')
```

***

### 3. `search()`

- The `search()` function looks for the first occurrence of the pattern anywhere in the string.
- Returns a Match object if found; otherwise, returns `None`.

```python
import re

str1 = 'abcabdefg'
s = input("Enter Pattern to check: ")
m = re.search(s, str1)

if m is not None:
    print('First occurrence of match: start index', m.start(), ', end index', m.end())
else:
    print('Match is not available in the beginning of the string')
```

***

### 4. `findall()`

- The `findall()` function returns all non-overlapping matches of the pattern as a list.

```python
msg = "Python is an easy programming language. Python is good lang"
import re

s1 = input('Enter Search Word: ')
matcher = re.findall(s1, msg)

print(matcher)
```
**If you enter “Python” as the search word, output will be:**  
```
['Python', 'Python']
```
This lists all occurrences of the word "Python" in the string.

***



***

### 5. `findall()`
- To find *all* occurrences that match a given pattern.
- Returns a list containing all matches.

```python
import re
matcher = re.findall(r'[0-9]', 'a7b9c5kz')
print(matcher)
```
**Output:**
```
['7', '9', '5']
```
This example finds all digits in the string.

***

### 6. `sub()`
- Means *substitution* or *replacement*.
- Syntax: `re.sub(pattern, replacement, target_string)`.
- Every matched pattern in the target string is replaced with the given replacement.

```python
import re
s = re.sub(r'[a-z]', '#', 'a7b9c5kz')
print(s)
```
**Output:**
```
#7#9#5#8#
```
Here, all lowercase letters are replaced by `#`.



***

### 6. `sub()` Example – Interactive Word Replacement

```python
msg = 'Python is an easy programming language. Python is good language'
import re

s1 = input('Enter Search Word: ')
s2 = input('Enter New Word: ')

# Correct usage: re.sub()
result = re.sub(s1, s2, msg)

print(result)
```

- This code asks the user for the word to search (`s1`) and the new word to substitute (`s2`).
- It then replaces all occurrences of the search word in `msg` with the new word, printing the resulting string.

***


***



Here’s the polished content from your image, explaining the `subn()` function in Python’s `re` module, with improved clarity:

***

### 7. `subn()`

- `subn()` works like `sub()`, but it also returns the number of replacements made.
- It returns a tuple: the first element is the resulting string and the second element is the number of replacements performed.

**Syntax:**  
```python
(result_string, number_of_replacements) = re.subn(pattern, replacement, target_string)
```

**Example:**
```python
import re

t = re.subn('[a-z]', '#', 'a7b9c5k8z')
print(t)
print('The Result string :', t[0])
print('The number of occurrence :', t[1])
```

**Output:**
```
('#7#9#5#8#', 5)
The Result string : #7#9#5#8#
The number of occurrence : 5
```

This shows both the transformed string and the count of substitutions made.

***


***

### 1. **Regular Expression for 10-digit Mobile Numbers**

**Rules:**
- The number must contain exactly 10 digits.
- The first digit must be 7, 8, or 9.

**Regex Pattern Examples:**
```python
# Possible patterns for a 10-digit mobile number starting with 7, 8, or 9:
[7-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]
# or
[7-9][0-9]{9}
# or
(7|8|9)\d{9}
```

import re
file = open('Data.txt') # enter the path of the file, chat gpt give example of if i want file to if stored in azure, aws and google
data = file.read()
#print(data)
pattern = r'[7-9]\d{9}' # we are creating the match here
mobile_numbers = re.findall(pattern,data) # Fin all function findll()
for m in mobile_numbers:
    print(m)
    

***

### 2. **Check String Starts with 'r' and Ends with 'h'**

To check if a string starts with "r" and ends with "h":

```python
import re

pattern = r'^r.*h$'
result = re.match(pattern, "rakesh")
print(result is not None)   # True for "rakesh"
```

***

### 3. **Regular Expression for Valid Email Address**

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

```python
import re

file = open('Data.txt')
data = file.read()
# print(data)  # Uncomment to print file contents

# Pattern to match 10-digit mobile numbers starting with 7, 8, or 9
pattern = r'[7-9]\d{9}'
mobile_numbers = re.findall(pattern, data)

# Pattern to match valid email addresses
pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
email_address = re.findall(pattern, data)

# Print all found mobile numbers
for m in mobile_numbers:
    print(m)

# Print all found email addresses
for e in email_address:
    print(e)
```

- This code opens a file called `Data.txt` and reads its contents.
- It then searches for all mobile numbers and email addresses using appropriate regular expressions, printing each one found.

***


***

### Python's Object Oriented Programming (OOP): What is a Class?

1. In Python, everything is an object. To create an object, a model or blueprint (which is a class) is required.
2. A class is used to represent properties (attributes) and actions (behavior) of objects. like lst.append(40) 
# ex: we have laptop and we can - chatgpt at example here
3. Properties are represented by variables.
4. Actions are represented by methods.
5. Therefore, a class contains both variables and methods.

ex:
- Earlier we were preaparing food at home
- now we are going out and getting ready to eat food
- earlier we weare accempbling laptop at our home, now we are getting ready assemble laptop in the market

- terminology
- class() :
    - in front of you table, chair or mobile 
    - chair and table is belongs to furniture class and mobile is electronic class
    - so furniture class have object like chair and table, same applicalbe to mobile
***

### How to Define a Class

A class is defined using the `class` keyword.
- Every object is belongs to some class 
**Syntax:**
```python
class ClassName:
    '''Documentation string'''
    # Variables: instance variables, static variables, local variables
    # Methods: instance methods, static methods, class methods
```
- The documentation string describes the class. It is optional but recommended for clarity.

list.__doc__
str.__doc__
tuple.__doc__
**Accessing the documentation string:**
```python
print(ClassName.__doc__)
help(ClassName)
```
Use either to view a class’s docstring.


_1st = [10,20,30]
print(type(_1st))

Output:
<class 'list'>
***



***

### Types of Variables in Python Classes

Within a Python class, data is represented using variables. There are three types of class-level variables:

1. **Instance Variables:**  
   Object-level variables unique to each instance.
2. **Static Variables:**  
   Class-level variables shared by all instances of the class.
3. **Local Variables:**  
   Method-level variables used within functions and not accessible outside.

***

### Types of Methods in Python Classes
- we can create our own class depends on the types.

Operations in Python classes are represented by methods. There are three types of allowed methods:

1. **Instance Methods:**  
   Operate on individual object instances.
2. **Class Methods:**  
   Operate on the class as a whole; use the `@classmethod` decorator.
3. **Static Methods:**  
   Independent of class or instance; use the `@staticmethod` decorator.

***

Here’s a polished summary of your image that covers what objects and reference variables are in Python classes, plus how `self` works:

***

### What is an Object?
ex: steave job have one idea like for apple mobile which is in his mind, now he given the mobile or blueprint to users, here mobile is object.

- The physical existence of a class is called an object.
- Any number of objects can be created from a class.

**Syntax to create an object:**
```python
reference_variable = ClassName()
# Example
s = Student()
```

***

### What is a Reference Variable?
- in abouve example if reference variable. 
- A reference variable is used to refer to an object.
- Through a reference variable, the properties and methods of the object can be accessed properties and methods of object.

***

### The `self` Variable

- `self` is the *default variable* in instance methods and constructors, always pointing to the current object (like `this` in Java).
- **self** allows access to instance variables and instance methods of the object.

**Notes:**
1. `self` must be the first parameter inside the constructor (`def __init__(self)`). # initiate the class - like you are registering your self first in the collecge for admission, it is also called contructore object, this can't change,
2. `self` must be the first parameter inside any instance method.
def show(self)



***

### Constructor Concept in Python

1. A constructor is a special method in Python.
2. The constructor's name must be `__init__(self)`.
3. It is executed automatically when an object is created.
4. Its main purpose is to declare and initialize instance variables.
5. Each object's constructor will only be executed once upon creation.
6. The constructor must take at least one argument (typically `self`).
7. If you don’t define a constructor, Python supplies a default one.

**Example constructor implementation:**
```python
def __init__(self, name, rollno, marks):
    self.name = name
    self.marks = marks
    self.rollno = rollno
```
Here is a concise and polished summary of your image, explaining instance and static variables in Python classes:

***

### Types of Variables in Python Classes

Python classes can represent data using three types of variables:
1. **Instance Variable (Object Level Variable):**
   - Value varies between objects.
   - Each object gets its own separate copy.
   - Can be accessed inside the class through `self`, and outside the class via object reference.



class Employee: #class <nameofyourclass>
    '''This is example of class object as Employee Class ....'''
    def __init__(self, id,nm,sal): #default constructor also called magical and self is variable - we also can mention s or a or n, this is special variable | after , what we mention this are argument
        self.empID = id # it creating the value in object self
        self.name = nm
        self.salary = sal
    def show_empinfo(self): # this can be anything and its manadaory be there - self or what you define in init
        print('Employee ID', self.empID)
        print('Employee Name', self.name)
        print('Salary', self.salary)
    def get_pf_da_info(self):
        print('PF', self.salary * .10) # here we are printing the PF but using the existing defined class which we did above
        print('DA', self.salary * .15)
        
Employee.__doc__

## Now I am going tocreate an object 'emp' of employee class
emp1 = Employee(101, 'Navid', 50000) # here it first call to class contractor and create object in memroy ex- id-9184 and later it gives referecne to "self" refercen of current object, with this we also pass the some values which refer to id,nm,sal
print(id(emp1))
print(type(emp1))

emp2 = Employee(201, 'Ali', 90000)
emp1.show_empinfo() # here even function is blank it will call to "self" refrecne which is self in our case
emp2.show_empinfo()


# here it create two object ex - 1001 for emp1 and 1002 for emp2, when i call from emp1 then self to details of emp1 one, same applicalbe to emp2        
# train example
# two passenger comes A and B on railway station wanted to book the ticket
# now A come on windows so "ticket counter employee (in our case self)" will book the ticket
# now B come on windows so "ticket counter employee (in our case self)" will book the ticket
# so A and B get the ticket with the help of "Ticket counter employee"



2. **Static Variable (Class Level Variable):**
   - Value is shared by all objects of the class (does not change per object).
   - Declared inside the class but outside of any methods.
   - Only one copy exists for the class, shared by all objects.
   - Accessible using the class name (recommended) or via object reference.

class Bank:
    ifsc_code = 98212  # Static variable (class level variable)

    def __init__(self, an, nm, bal):
        self.accno = an      # Instance variable (object level variable)
        self.name = nm
        self.balance = bal

    def show_acc_info(self):
        print('Account No:', self.accno)
        print('Name of account holder:', self.name)
        print('Balance in the account:', self.balance)  # corrected from self.bal to self.balance
        print('IFSC of your account:', self.ifsc_code) # ???
# Creating objects of Bank class
ac1 = Bank(1001, 'navid', 48592)
ac2 = Bank(1024, 'bob', 48291)
ac3 = Bank(1234, 'yogesh', 1482)

# Calling the method to display account information
ac1.show_acc_info()
ac2.show_acc_info()
ac3.show_acc_info()




Bank.ifsc_code = 2931 # updated ifsc code, here we are chaing the ifsc_code from bank so it will update for all 
ac1.show_acc_info()
ac2.show_acc_info()
ac3.show_acc_info()

# chat gpt share the output here


ac1.ifsc_code = 200
ac1.show_acc_info()
# chatgpt share the output here
### Explanation:
# - `ifsc_code` is a class-level static variable shared by all bank accounts.
# - `accno`, `name`, and `balance` are instance variables unique to each account.
# - The method `show_acc_info()` prints the details of each bank account.

# This example demonstrates how static variables and instance variables coexist and are used inside a Python class.

# If needed, I can provide an extended example showing access to the static variable and how it differs from instance variables!



### Explanation:
# - `ifsc_code` is a class-level static variable shared by all bank accounts.
# - `accno`, `name`, and `balance` are instance variables unique to each account.
# - The method `show_acc_info()` prints the details of each bank account.

# This example demonstrates how static variables and instance variables coexist and are used inside a Python class.

# If needed, I can provide an extended example showing access to the static variable and how it differs from instance variables!



3. **Local Variable (Method Level Variable):**
   - Declared inside methods and only accessible within that method.

# class and object example:
class Employee: #class <nameofyourclass>





