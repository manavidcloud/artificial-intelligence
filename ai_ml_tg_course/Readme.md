# Day1:
## Install Python
1. Install the python
2. Open command prompt
3. pip install jypter
4. create shortcut key of Jypter notebook
5. change the start in path

- can use collab as well.

## Any code

Input --> process module -> Output

### Input
- user interface 
- csv
- api
- sql

marks = input('Enter your marks :')


### Data structue 
- list
    - Inservtion order preserved - we will get the data what we inservted and set not preserved the data.
    - Duplicate objects are allowed but not in set

    - Heterogenous objestc are allowed (differt type of value - 10, 'apple', 34.5) in list

    - List is mutable, 

    - list is dynamic beacuse base on our requriment we can increase the size or decise the size 

    1st.append(1000)
    1st.pop
1st = [10,20,30,40,50]
print(1st)
output = [10, 20, 30, 40, 50]


- tuple
- set
 set1 =( [10,20,30,40,50])
 print(set1)
 output = {40, 10, 50, 20, 30}

- dictionanry
- Advance data structe
    - Numpy
    - Panda

- we are going to use flash which gives web app


## Process module 
result = 10 + 20
print (result)

result = 10/20
print(result)

result = 22 / 7
print(result)


result = 22 % 7 #% - modules operator which give reminders only
print(result)
output = 1 

result = 2*4
print(result)
output = 8

result = 2**4 (it will be two time multiple)
print(result)
output = 16


what is indexing?
-4  -3  -2 -1 -> negative indexign, start from right to left
[10 30 50 60] - this is your list
0    1  2  3 -> this is index number, this is also call positvie indexing left to right

example:
list(0) = 10
list(-3) = 30

## slice operator
lyntex: list[start : stop : stop]

1st = [10,20,30,50,80,35]
sub_1st =  1st[0:3]
output = 10,20,30 as it always be n-1 when use selective list
print(sub_1st)

## reversee list
rev_list= 1st[::-1]
print(rev_list)


first : - by default start of the list
second : - by default end of list
-1 : - step here 

1st = [10,20,30,50,60]
print(1st[2:5:1])
print(1st[2:5:-1]) - no output

print(1st[5:2:-1]) - then it will be go from -1 from right to left
print(1st[5:2:1]) - it will use positvie 1 from left to right


# Tuple data structue 
- we are not allowed to change the things
- its have packing and unpacking things 
- tuple with single value else it will print like int - t3 = (10) - this is int, t3=(10,) this is tuple

t1 = 10,20,30 - if you have multiple values it will be tuple packing 
x,y,z = t1 - tuple unpacking, where x=10, y=20, z=30 print(x), print(y)

change tuple to any other type
t4=10,20,30
print(t4)
print(type(t4))

t4 = 'Delhi
- one reference object can have one object only but object can have multiple object reference


- byte arrey use for image date like video etc.

# Dictionayr Data structure 
- data which comes from api it generaly comes in json (java script o?? n??), json also gives in json
- its in dictoryny
- no indexing in difcotry 
- we can access values from dictory by keys
- keys are unique 
 - d1 will reference and it create the id=100 
 - d1[101] = mumbai 

how to create discory
d={} or d = dict{}

print(d)
print(type(d))

syntex:
d1 = {key: value, key: value}

d1 = {Name: 'Navid', Age: 40}


print(d1.keys())

print(d1,values())

d1.items()


# find the sunday in calander year
for key.value in d1.items():
   if value == 'Mango':
      print(key,value)


# Set data structe
d1={}
print(d1)
print(type(d1))

s1 = {10,20,30}
print(s1)
print(type(s1))

output = 10,20,30


s2 = set{10,20,30,10,}
print(s2)
print(type(s2))
output = 30,20,10


s1 & s2


# Mathematicla operations on the set 
### x.union(y) => we use this function to retrun all elements present in bohtsents 

s1 | s2 - union
s1 - s2 - difference
s1 ^ s2 - symetic difference either present in s1 or s2 but not in both 


