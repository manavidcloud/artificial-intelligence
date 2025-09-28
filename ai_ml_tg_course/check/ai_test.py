class Bank:
    ifsc_code = 98212  # Static variable (class level variable)

    def __init__(self, an, nm, bal):
        self.accno = an      # Instance variable (object level variable)
        self.name = nm
        self.balance = bal

    def show_acc_info(self):
        print('Account No:', self.accno)
        print('Name of account holder:', self.name)
        print('Balance in the account:', self.balance)  # corrected from self.bal to self.balance
        print('IFSC of your account:', self.ifsc_code) # ???
# Creating objects of Bank class
ac1 = Bank(1001, 'navid', 48592)
ac2 = Bank(1024, 'bob', 48291)
ac3 = Bank(1234, 'yogesh', 1482)

# Calling the method to display account information
ac1.show_acc_info()
ac2.show_acc_info()
ac3.show_acc_info()




Bank.ifsc_code = 2931 # updated ifsc code, here we are chaing the ifsc_code from bank so it will update for all 
ac1.show_acc_info()
ac2.show_acc_info()
ac3.show_acc_info()

# chat gpt share the output here


ac1.ifsc_code = 200
ac1.show_acc_info()
# chatgpt share the output here
### Explanation:
# - `ifsc_code` is a class-level static variable shared by all bank accounts.
# - `accno`, `name`, and `balance` are instance variables unique to each account.
# - The method `show_acc_info()` prints the details of each bank account.

# This example demonstrates how static variables and instance variables coexist and are used inside a Python class.

# If needed, I can provide an extended example showing access to the static variable and how it differs from instance variables!

