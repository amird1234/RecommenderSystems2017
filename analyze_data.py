import matplotlib.pyplot as plt
import sys

#sys.argv[1] if sys.argv[1] is not None else

filename = '/Users/amirdahan/Downloads/data/amir_tmp.txt'


f = open(filename, 'r')
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
