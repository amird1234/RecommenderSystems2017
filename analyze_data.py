import matplotlib.pyplot as plt
import sys
import argparse
import numpy


#sys.argv[1] if sys.argv[1] is not None else

parser = argparse.ArgumentParser()
parser.add_argument('inFile', help='an absolute path input file with "user item interaction" pattern')
parser.add_argument('outFile', help='an absolute path output file with dictionary')
args = parser.parse_args()
print(args.inFile)
print(args.outFile)

f = open(args.inFile, 'r')
lines = f.read()
f.close()
lines = lines.splitlines()

count = 0
myDict = {}
for line in lines:
    count+=1

    #skip header
    if count is 1:
        continue

    tokens = line.split()
    key, interaction = tokens[0] + ' ' + tokens[1], int(tokens[2])

    if key in myDict.keys():
        print("already seen this key")
    else:
        myDict[line] = {}

    myDict[line][interaction] = 1

    if count%1000 == 0:
        print(count)

print('woohhoo')

desired_action = {2,3,5}
count = 0
for key,value in myDict.items():
    count += 1
    if set(desired_action).issubset(value):
        myDict[key] = 1
    else:
        myDict[key] = 0

    if count%1000 == 0:
        print(count)

numpy.save(args.outFile, myDict)
print('done')
