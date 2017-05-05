import matplotlib.pyplot as plt
import sys
import argparse


#sys.argv[1] if sys.argv[1] is not None else

filename = '/Users/amirdahan/Downloads/data/amir_tmp.txt'
parser = argparse.ArgumentParser()
parser.add_argument('--file', help='an absolute path input file with "user item score" pattern')
args = parser.parse_args()
print args.file

f = open(args.file, 'r')
lines = f.read().splitlines()
f.close()
lines = map(int, lines)

i=0
myDict = {}
for line in lines:
    i+=1
    if line in myDict.keys():
        myDict[line] += 1
    else:
        myDict[line] = 1
    if i%1000 == 0:
        print i
print 'done'

plt.hist(myDict.values())
plt.show()
