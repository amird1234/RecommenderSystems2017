import argparse
import collections
import pickle
from scipy import spatial

IMPRESSION = 0

class RecSys:
    interactions_db = {}
    interactions_db2 = {}
    positive_feedback = {1, 2, 3}
    evaluation_results = {}
    ctr_results = {}

    def __init__(self, lines):
        ##interactions_db[user][item][interaction_type][timestamp]
        count = 0
        interactions_db = {}
        interactions_db2 = {}
        try:
            print("Loading DB from .txt files")
            with open('interactions.txt', 'rb') as handle:
                self.interactions_db = pickle.loads(handle.read())
            with open('interactions2.txt', 'rb') as handle:
                self.interactions_db2 = pickle.loads(handle.read())
            print("Loaded DB from .txt files")
            return
        except:
            print("Didn't manage to load DB from .txt files, keeping the regular flow")
            self.interactions_db = {}
            self.interactions_db2  = {}

        for line in lines:
            count += 1

            # skip header
            if count is 1:
                continue

            tokens = line.split()
            user, item, interaction, timestamp = int(tokens[0]), int(tokens[1]), int(tokens[2]), int(tokens[3])

            if user not in interactions_db.keys():
                interactions_db[user] = {item: {interaction: {timestamp: 1}}}
            elif item not in interactions_db[user].keys():
                interactions_db[user][item] = {interaction: {timestamp: 1}}
            elif interaction not in interactions_db[user][item].keys():
                interactions_db[user][item][interaction] = {timestamp: 1}
            elif timestamp not in interactions_db[user][item][interaction].keys():
                interactions_db[user][item][interaction][timestamp] = 1

            if user not in interactions_db2.keys():
                interactions_db2[user] = {}
            interactions_db2[user][timestamp] = (item,  interaction)

            if count % 10000 == 0:
                print(count)

        print('done parsing from file to dictionary, found %s elements'% len(interactions_db))
        self.interactions_db = interactions_db
        self.interactions_db2 = interactions_db2
        with open('interactions.txt', 'wb') as handle:
            pickle.dump(interactions_db, handle)
        with open('interactions2.txt', 'wb') as handle:
            pickle.dump(interactions_db2, handle)

    def CTR(self):
        CTR_res = {}

        def CTRu(user):
            numerator = 0
            denominator = 0

            for item in self.interactions_db[user]:
                if 0 in self.interactions_db[user][item].keys():
                    denominator += 1 if len(self.interactions_db[user][item][0]) > 0 else 0
                    numerator += 1 if len(
                        set(self.interactions_db[user][item].keys()) & self.positive_feedback) > 0 else 0
            return float(numerator) / denominator if denominator is not 0 else 0

        for user, value in self.interactions_db.items():
            CTR_res[user] = CTRu(user)
        f = open("userCTR", 'w')
        for k in CTR_res.keys():
            if CTR_res[k] > 0 and CTR_res[k] < 1:
                print(k,CTR_res[k])
            f.write(str(k) + " " + str(CTR_res[k]) + "\n")
        return CTR_res

    def calculate_cosine_similarity(self):
        """
        Calculates the cosine similarity between CTR and the evaluation methods
        :return: cosine similarity between CTR and each of evaluation methods
        """

        similarity = {}
        for method in self.evaluation_results:
            similarity[method] = 1 - spatial.distance.cosine(self.ctr_results, method)
        return similarity

    def splitData(self, trainFileName, testFileName):
        testItems = []
        trainItems = []
        trainFile = open(trainFileName, 'w')
        testFile = open(testFileName, 'w')
        for user in self.interactions_db2:
            impressed_item = {}
            od = collections.OrderedDict(sorted(self.interactions_db2[user].items()))
            last = None

            #find the last interaction that is not impression
            for element in od:
                item = od[element][0]
                timestamp = element
                interaction = od[element][1]

                if interaction == IMPRESSION:
                    impressed_item[item] = 1

                if interaction is not IMPRESSION and item not in impressed_item.keys():
                    #if interaction is not impression & we didn't see an impression of this item so far - put in test
                    last = timestamp

            if (last is  None):
                continue #if we didn't find item, TODO BOM

            #put right tuples in trainItems and testItems
            for element in od:
                item = od[element][0]
                timestamp = element

                if timestamp == last:
                    #Put in test the last (user,item) that has interaction without impression 
                    testItems.append(str(user) + " " + str(item)+ "\n")
                    break #since we don't care about interactions after the last
                else:
                    trainItems.append(str(user) + " " + str(item)+ "\n")

        #remove duplicates
        trainItems = set(trainItems)
        testItems = set(testItems)

        testFile.writelines(item for item in testItems)
        trainFile.writelines(item for item in trainItems)
        trainFile.close()
        testFile.close()


if __name__ == '__main__':
    # grab the arguments when the script is ran
    parser = argparse.ArgumentParser()
    parser.add_argument('inFile', help='an absolute path input file with "user item interaction" pattern')
    parser.add_argument('trainFileName', help='path of train data file')
    parser.add_argument('testFileName', help='path of test data file')
    #add_argument('split', help='should program split input to train/test files [yes/no]')

    args = parser.parse_args()
    print(args.inFile)

    f = open(args.inFile, 'r')
    lines = f.read()
    f.close()
    lines = lines.splitlines()

    # Parse data and init the databases
    recSys = RecSys(lines)

    # Run CTR on the initialized
    recSys.ctr_results = recSys.CTR()

    #We shall split data to train and test if we're ordered to by arguments
    recSys.splitData(args.trainFileName, args.testFileName)
