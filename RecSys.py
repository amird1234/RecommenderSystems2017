import argparse


class RecSys:
    interactions_db = {}
    positive_feedback = {1, 2, 3}

    def __init__(self, lines):
        ##interactions_db[user][item][interaction_type][timestamp]
        count = 0
        interactions_db = {}
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

            if count % 1000 == 0:
                print(count)
        print('done parsing from file to dictionary, found %s elements', len(interactions_db))
        self.interactions_db = interactions_db

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
            CTR_res[user] = CTRu(user);

        return CTR_res


if __name__ == '__main__':
    # grab the arguments when the script is ran
    parser = argparse.ArgumentParser()
    parser.add_argument('inFile', help='an absolute path input file with "user item interaction" pattern')
    args = parser.parse_args()
    print(args.inFile)

    f = open(args.inFile, 'r')
    lines = f.read()
    f.close()
    lines = lines.splitlines()

    # Parse data and init the databases
    recSys = RecSys(lines)

    # Run CTR on the initialized
    CTR_res = recSys.CTR()
