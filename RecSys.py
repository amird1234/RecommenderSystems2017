import argparse
import collections
import pickle
from scipy import spatial
import sys
import os
import numpy

IMPRESSION = 0

class RecSys:
    interactions_db = {}
    interactions_db2 = {}
    positive_feedback = {1, 2, 3}
    evaluation_results = {}
    ctr_results = {}

    def __init__(self, lines):
        '''
        Goal of this function is to store hash table of all data together, in the following formats:
            interactions_db[user][item][interaction_type][timestamp] = 1
            interactions_db2[user][timestamp] = (item,  interaction)
        :param lines: list of all usage-points with the pattern 'user item interaction'
        '''
        #
        count = 0
        interactions_db = {}
        interactions_db2 = {}
        try:
            # we try to load hash table from a pickled file
            print("Loading DB from pickled .txt files")
            with open('interactions.txt', 'rb') as handle:
                self.interactions_db = pickle.loads(handle.read())
            with open('interactions2.txt', 'rb') as handle:
                self.interactions_db2 = pickle.loads(handle.read())
            print("Loaded DB from .txt files")
            return
        except:
            print("%s: Didn't manage to load DB from .txt files, keeping the regular flow" % sys.exc_info()[0])
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
        print("Calculating CTR")
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
        for user in CTR_res.keys():
            f.write(str(user) + " " + str(CTR_res[user]) + "\n")
        f.close()
        print("found %d users for CTR" % len(CTR_res))
        self.ctr_results = CTR_res

    def clear_ctr_output(self):
        print('Removing non intersecting users from DB')
        users = []
        # Collect the mutual users list between all algorithms
        for method in self.evaluation_results:
            if len(users) == 0:  # first one
                users = set(self.evaluation_results[method].keys())
            else:
                users &= set(self.evaluation_results[method].keys())
        users &= set(self.ctr_results.keys())
        print("Found %d mutual users between algorithms" % len(users))

        # Remove the non existing users from all evaluation methods results
        tmp_dict = {}
        for method in self.evaluation_results:
            tmp_dict[method] = {}
            for user in users:
                tmp_dict[method][user] = self.evaluation_results[method][user]
        self.evaluation_results = tmp_dict

        # Remove the non existing users from CTR results
        tmp_ctr_dict = {}
        for user in users:
            tmp_ctr_dict[user] = self.ctr_results[user]
        self.ctr_results = tmp_ctr_dict

    def ALGS(self, evaluations_dir):
        """
        go over all algorithm outputs and put them in
        :return:
        """
        for filename in os.listdir(evaluations_dir):
            if filename.endswith('_Store'):
                continue
            print("Fetching %s Evaluation data" % filename)
            algFile = open('evaluations' + '/' + filename, 'r')
            lines = algFile.read().splitlines()
            algFile.close()
            alg_evaluation = {}
            for line in lines:
                tokens = line.split()
                user = int(tokens[0])
                evaluation = float(tokens[1])
                alg_evaluation[user] = evaluation
            self.evaluation_results[filename] = collections.OrderedDict(sorted(alg_evaluation.items()))
            print("found %d users for %s" % (len(self.evaluation_results[filename]), filename))

    def __getattribute__(self, *args, **kwargs):
        return super().__getattribute__(*args, **kwargs)

    def calculate_pierson_similarity(self):
        """
        Calculates the cosine similarity between CTR and the evaluation methods
        :return: cosine similarity between CTR and each of evaluation methods
        """
        print("calculating cosine similarity between ctr and all other evaluation methods")

        self.clear_ctr_output()

        similarity = {}
        for method in self.evaluation_results:
            similarity[method] = abs(numpy.corrcoef(list(self.ctr_results), list(self.evaluation_results[method].values()))[1, 0])
            print("Pierson similarity between CTR and %s is %f" % (method, similarity[method]))
        return similarity

    def calculate_cosine_similarity(self):
        """
        Calculates the cosine similarity between CTR and the evaluation methods
        :return: cosine similarity between CTR and each of evaluation methods
        """
        print("calculating cosine similarity between ctr and all other evaluation methods")

        self.clear_ctr_output()

        similarity = {}
        for method in self.evaluation_results:
            similarity[method] = 1 - spatial.distance.cosine(list(self.ctr_results), list(self.evaluation_results[method].values()))
            print("Cosine similarity between CTR and %s is %f" % (method, similarity[method]))
        return similarity

    def splitData(self, train_filename, test_filename):
        print("splitting data to train and test")

        testItems = []
        trainItems = []
        if (os.path.isfile(train_filename) and  os.path.isfile(test_filename)):
            return
        trainFile = open(train_filename, 'w')
        testFile = open(test_filename, 'w')
        for user in self.interactions_db2:
            impressed_item = {}
            od = collections.OrderedDict(sorted(self.interactions_db2[user].items()))
            last = None

            # find the last interaction that is not impression
            for element in od:
                item = od[element][0]
                timestamp = element
                interaction = od[element][1]

                if interaction == IMPRESSION:
                    impressed_item[item] = 1

                if interaction is not IMPRESSION and item not in impressed_item.keys():
                    # if interaction is not impression & we didn't see an impression of this item so far - put in test
                    last = timestamp

            if (last is  None):
                continue  # if we didn't find item

            # Put right tuples in trainItems and testItems
            for element in od:
                item = od[element][0]
                timestamp = element

                if timestamp == last:
                    # Put in test the last (user,item) that has interaction without impression
                    testItems.append(str(user) + " " + str(item)+ "\n")
                    break  # Since we don't care about interactions after the last
                else:
                    trainItems.append(str(user) + " " + str(item)+ "\n")

        # Remove duplicates
        trainItems = set(trainItems)
        testItems = set(testItems)

        testFile.writelines(item for item in testItems)
        trainFile.writelines(item for item in trainItems)
        trainFile.close()
        testFile.close()


if __name__ == '__main__':
    # Grab the arguments when the script is ran
    parser = argparse.ArgumentParser()
    parser.add_argument('inFile', help='an absolute path input file with "user item interaction" pattern (all data)')
    parser.add_argument('trainFileName', help='path of train data file')
    parser.add_argument('testFileName', help='path of test data file')
    parser.add_argument('evaluationsLib', help='path of evaluations files lib')
    # add_argument('split', help='should program split input to train/test files [yes/no]')

    args = parser.parse_args()

    f = open(args.inFile, 'r')
    lines = f.read()
    f.close()
    lines = lines.splitlines()

    # Parse data and init the databases
    recSys = RecSys(lines)

    # We shall split data to train and test if we're ordered to by arguments
    recSys.splitData(args.trainFileName, args.testFileName)

    # run BPR and bring evaluations of results using several methods
    os.system('python testTheano.py ' + args.trainFileName + ' ' + args.testFileName)

    # Run CTR on the initialized
    recSys.CTR()

    # Get evaluation algorithms
    recSys.ALGS(args.evaluationsLib)

    recSys.calculate_cosine_similarity()
    recSys.calculate_pierson_similarity()


