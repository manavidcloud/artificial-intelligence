# Day 4 - AI - Regular expression 
Here is the content from your "image.jpg" (with some slight polishing for clarity):

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

Here’s a polished, formatted version of the content about quantifiers in regular expressions from your image:

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

Here’s a clear and polished version of your image’s explanation and code examples for the `fullmatch()`, `search()`, and `findall()` functions in Python’s `re` module:

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


Here’s a polished and corrected version of your image’s code for demonstrating the use of the `sub()` function from Python’s `re` module. (There is a typo in the code: `re.sum` should be `re.sub`.)

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


Here is a clear, organized, and polished version of the content from your image, including three common regular expression use cases:

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

another example of email address find -

Here is a polished version of your code for extracting mobile numbers and email addresses from a file using regular expressions:

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

