# Retrun multiple values from function
# In other langues we can retrun only one value - java
def check_value(a,b):
    sum = a + b 
    sub = a - b 
    
    return sum, sub # this is tuple ex: t1=10,20,30 (tuple use comma, and tuple packing)

x,y = check_value(10,20)

print('Sum of two numbers', x)
print('Substration of two numbers', y)