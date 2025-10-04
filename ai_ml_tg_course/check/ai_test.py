class Book:
    def __init__(self, pages, name, cost):
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

# print('Total No. of Pages:', total_cost.pages)
print('Total Cost:', total_cost.cost)