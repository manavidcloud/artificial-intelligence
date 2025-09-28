import re
file = open('Data.txt') # enter the path of the file, chat gpt give example of if i want file to if stored in azure, aws and google
data = file.read()
#print(data)
pattern = r'[7-9]\d{9}' # we are creating the match here
mobile_numbers = re.findall(pattern,data) # Fin all function findll()
for m in mobile_numbers:
    print(m)
    
