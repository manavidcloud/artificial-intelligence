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
