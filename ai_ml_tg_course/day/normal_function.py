empnum = list(range(1,15))
print('List', empnum)


def if_evn(num):
    if num % 2 == 0:
        return True
    else:
        return False

evn_list = list(filter(if_evn,empnum))
print('Even numbers are:', evn_list)
    