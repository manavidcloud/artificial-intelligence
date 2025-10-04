# Day 5: AI/ML - Oct 4, 2025
- setter and getter
- property of class
- decorator example 
- over loading
- overriidding 



### Setter and Getter Methods

We can set and get the values of instance variables by using getter and setter methods.

#### Setter Method

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

***

#### Getter Method

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

***

### Class Methods

Inside method implementation, if we are only using class variables (static variables), such type of methods should be declared as class methods.

Declare class method explicitly using `@classmethod` decorator. For class methods, the `cls` variable should be provided at the time of declaration.

Call class methods using class name or object reference.

***

---

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


## with gettter method we only featch the values - to validate the class

# after apply the setter method to class: set_cost()

# after apply the setter method to class: set_cost()
```python
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



## how to make private instanse variable

# after apply the setter method to class: set_cost()
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


Here is the extracted content from your image, formatted for easy copying in Markdown:

***

### Properties in Python Class and Objects

In Python, properties in a class are a way to manage access to instance attributes (variables) by defining getter and setter methods.

This allows encapsulation of the internal data and control over how it's accessed or modified.

- you buy a watch and given to fritend direclty but its looks odd, so what you do you wrap it in gift wrap. this is same applicalbe as properties in class.

- by using cost name properties in the class example in the proogram

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

# Property decorator method

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

- This code demonstrates how to use the `@property` decorator in Python to create managed attributes with getter and setter functionality.
- Attempting to set a negative cost prints an error and retains the previous valid value.

---

***

***

### 2. Class methods

Inside method implementation, if we are using only class variables (static variables), then such type of methods we should declare as class methods. We can declare class method explicitly by using `@classmethod` decorator.


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

    @classmethod
    def change_ifsc_code(cls, new_ifsc_code):
        cls.ifsc_code = new_ifsc_code
        print('IFSC Code Changed Successfully.')

    @staticmethod
    def check_eligibility(age):
        if age >= 18:
            print('You are eligible to open account')
        else:
            print('You are minor. Please come with parents.')

    @staticmethod
    def show_ifsc_code():
        print('IFSC Code  :', Bank.ifsc_code)
```

- `ifsc_code` is a class (static) variable.
- `change_ifsc_code` is a class method and changes the class variable.
- `check_eligibility` and `show_ifsc_code` are static methods; they don't access any instance or class level data except what is passed or referenced directly.
- `show_acc_info` is an instance method and prints account details, including the current IFSC code.


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



---

static method: like bank this will care about employee or customer. but ther eis third party as well that either employee or customer like someone comes to fill the form or come for inquary. like such feature we can allowi using static method 
- this allow to come in the back but can't allow withdarow money 
- this one have access to spedific location as well.

```
Bank.check_eligibility(20)

Bank.show_ifsc_code()

You are eligible to open account
IFSC Code  : 1007
```

- chat gpt give more details here. 

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


a = 10 + 20
print(a)

b = 'abc' + 'xyz'
print(b)

c = 10 * 2
print(c)


d = 'nanded' * 2
print(d)

---

Related to Polymorphism the following 3 topics are important:

1. Duck Typing Philosophy of Python

2. Overloading
    - Operator Overloading
    - Method Overloading: Unable to overload in python
    - Constractor overloading: unable to loverlod in python

3. Overridding:
 A. Method overridding
 B. contrator overriding


***

## 1. Duck Typing Philosophy of Python

In Python we cannot specify the type explicitly. Based on provided value at runtime the type will be considered automatically. Hence Python is considered as Dynamically Typed Programming Language.

```
def func1(obj):
    obj.talk()
```

What is the type of obj? We cannot decide at the beginning. At runtime we can pass any type. Then how can we decide the type?

At runtime if 'it walks like a duck and talks like a duck, it must be duck'. Python follows this principle. This is called Duck Typing Philosophy of Python.

---

### Demo Program:

```
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
- student a comes then security guard ask for what you come student a told for class then he allow

- student b comes then security guard ask for what you come student b told for class then he allow

- same in pyton it will not going to chec spefici class or object its call duck phylosopy



2. Overloading
    - Operator Overloading
    - Method Overloading: Unable to overload in python
    - Constractor overloading: unable to loverlod in python



### 1. Operator Overloading:

We can use the same operator for multiple purposes, which is nothing but operator overloading.  
Python supports operator overloading.

---

#### Eg1:
`+` operator can be used for Arithmetic addition and String concatenation

```
print(10 + 20)      # 30
print('new' + 'delhi')  # newdelhi
```

#### Eg2:
`*` operator can be used for multiplication and string repetition purposes.

```
print(10 * 20)      # 200
print('delhi' * 3)  # delhidelhidelhi
```

---

Demo program to use `+` operator for our class objects:

```
class Book:
    def __init__(self, pages):
        self.pages = pages
```

---

below progream will give an error

class Book:
    def __init__(self,pages):
        self.pages=pages


b1=Book(100)
b2=Book(200)

print(b1+b2)
        

Output:
    print(b1+b2)
          ~~^~~
TypeError: unsupported operand type(s) for +: 'Book' and 'Book'


To fix it we can use like this 

# Demo program to overload + operator for our Book class objects:
```python
class Book:
    def __init__(self, pages, name, cost):
        self.name = name
        self.pages = pages
        self.cost = cost

    def __add__(self, other):  #b1+b2 is calling to __add__ (magical method) and we are dundle method define here
        return self.cost + other.cost

b1 = Book(100, 'C Programming', 500)
b2 = Book(200, 'Java', 700)

total_cost = b1.cost + b2.cost

print('Total No. of Pages ', b1 + b2) # b1+b2 - it also called dundle method


```
b1+b2 = + must have either integer number of 'a' + 'b' string
- so it will check if it have any dundle method define def __add__ method
- self holding b1 as it inter method and first one. 

+ work and exiting datatype but if it get user defined datatype.
ex: b1+b2 = b1 .__add__ (b2) [__add__(self,other) - b1=self and other=b2]

- this wors with two object only
- this alwo works with list and tuple
- with existing code its ignoring 


The following is the list of operators and corresponding magic methods.

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




## prgoram with error


b1=Book(100, 'C Programming, 500)
b2=Book(200, 'Java',700)
b3 = Book (300, 'Python',900)
total cost b1.cost+b2.cost print('Total No. of Pages ',b1+b2)
total cost b1 +62 +b3 print(total_cost)
Total No. of Pages 1200
TypeError
Cell In[22], line 22
19 total cost = b1.cost+b2.cost
Traceback (most recent call last)
20 print('Total No. of Pages ',b1+b2)
---> 22 total cost = b1b2+b3
23 print(total_cost)
TypeError: unsupported operand type(s) for +: 'int' and 'Book'


# how to fix this 
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

# same prgram with different way 
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
Method Overloading: Unable to overload in python
- same name of function but different argument
ex: 
1. define funct(a,b)
2. define fun(a,b,c)
3. define fun(a,b,c,d)

- same name with multiple forms. 


- but in python this is not allow as python work on object base. 
hence funtion can refer later object only. method overloading now allowed


Constractor overloading: unable to loverlod in python

## Python Inheritance

Inheritance enables us to define a class that takes all the functionality from a parent class and allows us to add more. In this class, you will learn to use inheritance in Python.

Inheritance in Python is a powerful feature in object-oriented programming.

It refers to defining a new class with little or no modification to an existing class. The new class is called derived (or child) class and the one from which it inherits is called the base (or parent) class.

ex:
- one team was working but they left the organiszation
- now if you know the inheritance (like existing project) you can resume to work

- inhetircan : what we have we will use it as well as what is missing we will add this as well.

- we wiill create class in class. 


