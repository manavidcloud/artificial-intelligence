
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


