import os

test_data_directory = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) + '\\tests\\test_data\\'
# with open(test_data_directory + 'hello.gv', 'w') as f:
#     f.write('hello')
# print("OK")
with open(os.path.abspath(os.path.dirname(os.path.dirname(__file__)))+'hello.txt','w') as f:
    f.write('OK')
print("OK")