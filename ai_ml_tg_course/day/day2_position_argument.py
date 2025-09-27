def student_info(*kwargs):
    print('kwargs type:', type(kwargs))
    print('\n\nStudent Info')
    for key,value in kwargs.items():
        print(f"{key} : (value)")