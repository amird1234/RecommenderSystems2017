from theano_bpr.utils import load_data_from_csv
from theano_bpr.bpr import BPR
import sys
import csv
if len(sys.argv) != 3:
    print("Usage: ./example.py training_data.csv testing_data.csv")
    sys.exit(1)

# Loading train data
train_data, users_to_index, items_to_index = load_data_from_csv(sys.argv[1])
# Loading test data
test_data, users_to_index, items_to_index = load_data_from_csv(sys.argv[2], users_to_index, items_to_index)
index_to_items = {v:k for k,v in items_to_index.items()}
index_to_users = {v:k for k,v in users_to_index.items()}
#dataSize = len(data)
#train_data = data[:int(dataSize*0.9)]
#test_data = data[int(dataSize*0.9):]
items2vec = {}
with open('items.csv', newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter='\t')
    next(reader, None)
    for row in reader:
        val = [int(x) for x in row[2:5] if x != '']
        items2vec[row[0]] = val
# Initialising BPR model, 10 latent factors
bpr = BPR(10, len(users_to_index.keys()), len(items_to_index.keys()))
# Training model, 30 epochs
bpr.train(train_data, epochs=1)
# Testing model
print(bpr.test(test_data,items2vec,index_to_items,index_to_users))
