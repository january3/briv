import re

# read the whole file test.txt into var cont

with open('test.txt', 'r') as file:
    cont = file.read()

match = re.search(r'^\[(.*)\].*\n((([^[\n]+) *= *(\w+)\n?)*)', cont)

print(match.groups())


