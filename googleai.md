AI have 3 domain 
one for structure data and rest of two for un structure data 


1. Problem statement
like list of users and machine in which they logged in 

2. Resarch
- like how to sort lists in python in google

3. finding
- we may use sort() or sorted() function
sort - will mofiy the list its executed on 
sorted - it will return the new list that's been sorted 


numbers = [4,6,9,10,20]
numbers.sort()
print(numbers


numbers = [4,2,6,29,37,13]
numbers.sort()
print(numbers)

names = ['danial', 'Le', 'mack', 'bob']
print("Without sorted function:", names)
print("Using sorted function output:", sorted(names))
print("Using sorted+lenth function output:", sorted(names, key=len))
# now we know how to order elemets of list based on return value of function


4. planning
- what tools we have aviabled and which arebet for the job
- now plan the approch 

- we know our events will be list of events and we will sort them by time
ex: numbers of users is list of events and when they login or log out sort by time 

- each events include machine name, username or event is login or logout 
- script to track such

- ifits login we want to add it in to group of users logged in that machine machine_users=[john, bob]

- its its logout we want to remot it machine_users=[john] # here bob logged out 

- for this we will use set() function to adding and removing as per login/log out time 

- But if current users stored in machine in a set, how do we know which set corresponds to the machien w are looking for?
 - the easiest way to do this storage this information in dictionary  
 - we will use name of the machine as the key and  and user of that machine as value ex - webserver: [user]

- so each event will check the event if machine is already there.
- we have to check this as we may checking the event for this machine as firtime 

- if that machine not there we will create entry if it is, we will update exiting entry w.r.t to action i.e add or remove user while either login or logout

- recommented to have two different function to process the data and  print the function.


# define helper function to sort the list by event date
def get_event_date(event):
    return event.date


# process the events - define current_users 
def current_users(events):
    # sort events in chronological order
    events.sort(key=get_event_date)
    
    # before iterating through the list of events, we create a dictionary 
    # where keys = machine names, values = sets of active users on that machine
    machines = {}
    
    for event in events:
        # check if the machine affected by this event is already in the dictionary
        # if not, add it with an empty set as the value
        if event.machine not in machines:  
            machines[event.machine] = set()
        
        # for login events, we add the user to the set
        # for logout events, we remove the user from the set
        if event.type == "login":
            machines[event.machine].add(event.user)
        elif event.type == "logout":
            machines[event.machine].remove(event.user)
    
    # once we finish iterating over the events,
    # the dictionary will contain all machines we have seen,
    # with values being the set of users currently logged into each machine
    return machines


# create a new function to print the results - generate_report
def generate_report(machines):
    # in the report we want to iterate over the keys and values of the dictionary
    # for that, we will use the items() method which returns both keys and values
    for machine, users in machines.items():
        # only print machines where one or more users are logged in
        if len(users) > 0:  
            # generate a comma-separated string of users logged into the machine
            users_list = ", ".join(users)
            
            # print machine name followed by the users currently logged in
            print("{}: {}".format(machine, users_list))

