empnum = list(range(1,15))
print('List without lambda function', empnum)
print('With Lambda function')

# Corrected filter with lambda for even numbers
even_list = list(filter(lambda num: num % 2 == 0, empnum))
print('Even List:', even_list)
