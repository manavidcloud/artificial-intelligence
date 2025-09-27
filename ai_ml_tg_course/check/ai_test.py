c = 0
try:
    a = int(input('Enter any number : '))
    b = int(input('Enter any number : '))
    c = a / b
except (ZeroDivisionError, ValueError) as msg:
    print('Exception Occure :', msg)
finally:
    print('Finally Block : Cleanup Code')

print('Value of c :', c)
print('Thank you ')