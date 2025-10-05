class A:
    def m1(self):
        print('A Class Method')

    def m3(self):
        print('A Class Method')

class B(A):
    def m1(self):
        print('B Class Method')
        
    def m3(self):
        print('B Class Method')

class C:
    def m1(self):
        print('C Class Method')

    def m3(self):
        print('C Class Method')

class X(A, B):
    def m1(self):
        print('X Class Method')

    def m2(self):
        print('X Class Method')

class Y(B, C):
    def m1(self):
        print('Y Class Method')

    def m2(self):
        print('Y Class Method')

class P(X, Y, C):
    def m1(self):
        print('P Class Method')


obj = P()
obj.m1()


obj.m2() # this will call x class and override Y class

obj.m3() # this will call A class method

print(P.mro()) # it will show the MRO 