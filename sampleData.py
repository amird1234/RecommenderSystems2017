with open("inputFile", 'r') as inF, open("outputFile"", 'w') as outF:
	next(inF) #skip the header
	for line in inF:
		if int(line.split('\t')[0]) % 10 ==0:
			outF.write(line)

