
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
