# AI - Day 3: Function - 

Here is the output shown in the provided image, reformatted in Markdown:

```markdown
## Nested Functions

We can declare a function inside another function, such type of functions are called Nested function.

### Example:
```
def outer(): # 1.we define the function, and it have its own id
    print('Outer Function started ') 2. we executed print statement for outer function
    def inner(): # 3. we define the innter function with print statment
        print('Inner Function execution')
    print('Outer Function calling Inner Function')
    inner() # we are calling innter function so it will printer "Inner function execution" even we can call it before the print line above, inner function have its own id

outer() # here we are calling outer function 
```

**Output:**
```
Outer Function started
Outer Function calling Inner Function
Inner Function execution
```
```
 
# Example one were we are calling innter function after print
def outer():
    print('Outer function started')
    def inner():
        print('Inner function started')
    print('Outer function calling Inner function')
    inner()

outer()
        
# Example one were we are calling innter function before print
def outer():
    print('Outer function started')
    def inner():
        print('Inner function started')
    inner()
    print('Outer function calling Inner function')

outer()
        

def outer():
    print('Outer function started')
    def inner():
        print('Inner function started')
    print('Outer function calling Inner function')
    inner()

outer()

fun = outer() # this will only print outer function this is third example

def outer():
    print('Outer function started')
    def inner():
        print('Inner function started')
    print('Outer function calling Inner function')
    return inner

fun_1 = outer() # this will only call outer function and exclude the innter function


def outer():
    print('Outer function started')
    def inner():
        print('Inner function started')
    print('Outer function calling Inner function')
    print('Id of innter', id(inner))
    return inner

fun_1 = outer()

fun_1() # this is going to call outer + innter function
Nested function

- this is function defination
def outer ()

    innter()


- this is function second part where we are using that function
outer()


# Function Decorators
- Decorators is a function which can take a function as argument and extends its functionality and return modified funcgtion with extended functionality.

ex: we have birthday at home
we call to decoreate guy to decoreate the room
room wil remain however decorate guy enhance the room 
this is call function decorators.

how it works?


normal function:
def ordinary():
    print('I am an ordinary function.....')
    
ordinary()

chatgpt explain whole program flow here for below program, i am unable to understand it. 

# this is ordinary - like room
def ordinary():
    print('I am an ordinary function.....')

# this is decorator function
def makemepretty(func): # makemepretty is function and we define ordanary function named 'func'
    def innter_func():
        print('Now I am pretty')
        func()
    return innter_func()


# now we wanted to use - like room decoration
pretty = makemepretty(ordinary)



# def NewOrginary():
#     print('I live in Nanded \n', 'Development needed here')

# NewOrginary()
# output - 
# I live in Nanded
# Development needed here

# use existing function
# below function already avaible in python or code here i am commenting to understand

def makemepretty(func): # makemepretty is function and we define ordanary function named 'func'
    def innter_func():
        print('Now I am pretty')
        func()
    return innter_func()


@makemepretty
def NewOrginary():
    print('I live in Nanded \n', 'Development needed here')


# Now I am pretty
#I live in Nanded 
# Development needed here
#

