
# In this we only defined the funcation and now we are going to calling that function 
# calling function
# as in python 
# less line of code - there are some line in the code which are repetativley use, 
# function is reusable 
# easy to debug 
# function is dynamic type 

## Funcations 
# By default function return none.
def MyFunction():
    print('Hello Python')

MyFunction()
id(MyFunction)
print(type(MyFunction))


## Operator 
# = : assignment operator a=10, for 10 a is assigning
# == : Equality operator a == 10 (it will check both have same values ture/false)
#  += : compound assignment a+=10 (a=a+10)
# a>=
# 

# def = define - defination only use in function 
# return = only use with function - it return the value the function 

# Function + 
def funAllR(option):
    result  = None # result is just kind of variable we can use any other as well if nothing then your output will be non
    if option == 'A':
        result = 100
    elif option == 'B':
        result = 'Delhi'
    elif option == 'C':
        result = 35.5
    else:
        print('Invalid Option')    
    return result

option = input('Option A \nOption B \nOption C \nSelect Any Option:')
answer = funAllR(option)
print('Result:', answer)
print('Result type:', type(answer))


# By default function return none.

def MyFunction():
    print('Hello Python')

result = MyFunction()
print('Output', result)
