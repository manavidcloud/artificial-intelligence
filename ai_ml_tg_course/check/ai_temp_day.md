# Day 6 - AI/ML - Oct 5, 2025 - Inheritance 

Python Inheritance

Inheritance enables us to define a class that takes all the functionality from a parent class and allows us to add more.
In this class, you will learn to use inheritance in Python.

Inheritance in Python
Inheritance is a powerful feature in object oriented programming.

It refers to defining a new class with little or no modification to an existing class.
The new class is called derived (or child) class and the one from which it inherits is called the base (or parent) class.

--------------------------------------------------------

# Python Inheritance Syntax

class BaseClass:
    # Body of base class

class DerivedClass(BaseClass):
    # Body of derived class

# Derived class inherits features from the base class where new features can be added to it.
# This results in re-usability of code.

# Example of Inheritance in Python
# To demonstrate the use of inheritance, let us take an example.

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


# partent class block 

class Person:
    def __init__(self):
        self.age = 0
        self.name = ''
        self.location = ''

    def get_person_info(self): # this will get info from user 
        self.age = int(input('Age : '))
        self.name = input('Name : ')
        self.location = input('Location : ')

    def show_person_info(self): # what enterned using get_personal_info it will display 
        print('Name     :', self.name)
        print('Age      :', self.age)
        print('Location :', self.location)
        
        

P = Person()

P.get_person_info()
P.show_person_info()  

# stduent program

class Student:
    def __init__(self):
        self.age = 0
        self.name = ''
        self.location = ''
        self.rollno = 0
        self.marks = 0

    def get_person_info(self):
        self.age = int(input('Age : '))
        self.name = input('Name : ')
        self.location = input('Location : ')
        self.rollno = int(input('Roll no : '))
        self.marks = int(input('Marsk : '))  # Typo: "Marsk" should be "Marks"

    def show_person_info(self):
        print(f'\nAge      : {self.age}')
        print(f'Name     : {self.name}')
        print(f'Location : {self.location}')
        print(f'Roll No     : {self.rollno}')
        print(f'Marks     : {self.marks}')
        
        
S = Student()
S.get_person_info()
S.show_person_info()


# Inheritance program with parent class
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
        self.marks = int(input('Marsk : '))  # (typo: should be "Marks")

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

s = Student() : have its oown information like rollno and marks. but as we are using parent class it will add age name and location (this will add first as its coming from parent)

Types of Inheritance in Python:
1. Single Inheritance
2. Multiple Inheritance
3. Multi-Level Inheritance
4. Hierachical Inheritance
5. Hybrid Inheritance

#1. Single Inheritance: 
In this type of Inheritance we have One Base/Parent Class and only one is Derived/Child Class.

- required marmaid diagram

#2. Multiple Inheritance: 
In this type of Inheritance we have More than One Base Class and Only One derived class

- requird marmaid diagram

# Example of Multiple Inheritance in Python

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

# Dervied class (child class)        
class Order(Customer, Product):
    def __init__(self, name, email, product_name, price, quantity):
        # Initialize both parent classes
        Customer.__init__(self, name, email) # Order class calling to Customer class
        Product.__init__(self, product_name, price) # Order class calling product class
        self.quantity = quantity

    def order_summary(self):
        print("\n---ORDER SUMMARY ---")
        self.customer_details()
        self.product_details()
        print(f"Quantity: {self.quantity}")
        print(f"Total Amount: ₹{self.price * self.quantity}")

# Create an order
order1 = Order("Navid", "md.navid@example.com", "Playstation", 90000, 4)
order1.order_summary()
```
__init__() : __init__() method is the constrator to initilise the class and also can call from another constractor
self: self is belongs to current object class, 

### Super keyword in class and object python

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
        # Person.__init__(self, name, age) # either pass using class name or use the suppoer keyworad
        super().__init__(name, age)
        self.emp_id = emp_id
        self.salary = salary

    def show_details(self):
        # use super() to call parent method
        super().show_details()
        print(f"Employee ID: {self.emp_id}")
        print(f"Salary: ₹{self.salary}")

# Create an object
emp1 = Employee("navid", 40, "x102", 90000)
emp1.show_details()
```

## super example 2 - 
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

# Dervied class (child class)        
class Order(Customer, Product):
    def __init__(self, name, email, product_name, price, quantity):
        # Customer.__init__(self, name, email) # Order class calling to Customer class
        # Product.__init__(self, product_name, price) # Order class calling product class
        
        # Initialize both parent classes using super()
        super().__init__(name, email)  # calls Customer's __init__ due to MRO
        super().__init__(product_name, price)  # this line won't actually call Product's __init__ with most MROs
        
        self.quantity = quantity

    def order_summary(self):
        print("\n---ORDER SUMMARY ---")
        self.customer_details()
        self.product_details()
        print(f"Quantity: {self.quantity}")
        print(f"Total Amount: ₹{self.price * self.quantity}")


# Create an order
order1 = Order("Navid", "md.navid@example.com", "Playstation", 90000, 4)
order1.order_summary()
```


### Method Resolution Order (MRO) :-

# MRO Algorithm:
# If head element of first list not present in the tail part of any other list,
# then consider that element in the result and remove that element from all the lists.

# Example:

class A:
    def m1(self):
        print('Method of Class A')

class B(A):
    def m1(self):
        print('Method of Class B')

obj = B()
obj.m1()                 # Output: Method of Class B
print(B.mro())           # Output: [<class '__main__.B'>, <class '__main__.A'>, <class 'object'>]



# example without MRO 
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


obj.m2() # this will call x class and override Y class

obj.m3() # this will call A class method

print(P.mro()) # it will show the MRO 
```

## how MRO work example - MRO mechanisam
mro(P) = P + merge(mro(X),mro(Y),mro(C),XYC)
       = P + merge(XABO, YBCO, CO, XYC) # here x is head element and rest is tail element
       = P + X + merge(ABO, YBCO, CO, YC)
       = P + X + A + merge(BO, YBCO, CO, YC)
       = P + X + A + Y + merge(BO, BCO, CO, C) # B and O is coming in tail part hence we are not considiering it, considering second class here
       = P + X + A + Y + B + merge(O, CO, CO, C)
       = P + X + A + Y + B + C + merge(O, O, O)
       = P + X + A + Y + B + C + O

## using super method with example with MRO 

class A:
    def m1(self):
        print('Method of Class A')

class B:
    def m1(self):
        print('Method of Class B')

class C(A, B):
    def m1(self):
        # print('Method of Class C')
        super().m1()           # Calls m1 from A (first in MRO)
        super(A, self).m1()    # Calls m1 from B (the next after A in MRO)

obj = C()
obj.m1()


Output:

text
Method of Class A
Method of Class B
This shows how super() can be used to chain method calls in multiple inheritance, traversing the method resolution order.

