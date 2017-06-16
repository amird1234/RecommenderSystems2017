# theano-bpr
#
# Copyright (c) 2014 British Broadcasting Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import theano, numpy
import theano.tensor as T
import time
import sys
from collections import defaultdict
from scipy import spatial

class BPR(object):

    def __init__(self, rank, n_users, n_items, lambda_u = 0.0025, lambda_i = 0.0025, lambda_j = 0.00025, lambda_bias = 0.0, learning_rate = 0.05):
        """
          Creates a new object for training and testing a Bayesian
          Personalised Ranking (BPR) Matrix Factorisation 
          model, as described by Rendle et al. in:

            http://arxiv.org/abs/1205.2618

          This model tries to predict a ranking of items for each user
          from a viewing history.  
          It's also used in a variety of other use-cases, such
          as matrix completion, link prediction and tag recommendation.

          `rank` is the number of latent features in the matrix
          factorisation model.

          `n_users` is the number of users and `n_items` is the
          number of items.

          The regularisation parameters can be overridden using
          `lambda_u`, `lambda_i` and `lambda_j`. They correspond
          to each three types of updates.

          The learning rate can be overridden using `learning_rate`.

          This object uses the Theano library for training the model, meaning
          it can run on a GPU through CUDA. To make sure your Theano
          install is using the GPU, see:

            http://deeplearning.net/software/theano/tutorial/using_gpu.html

          When running on CPU, we recommend using OpenBLAS.

            http://www.openblas.net/

          Example use (10 latent dimensions, 100 users, 50 items) for
          training:

          >>> from theano_bpr import BPR
          >>> bpr = BPR(10, 100, 50) 
          >>> from numpy.random import randint
          >>> train_data = zip(randint(100, size=1000), randint(50, size=1000))
          >>> bpr.train(train_data)

          This object also has a method for testing, which will return
          the Area Under Curve for a test set.

          >>> test_data = zip(randint(100, size=1000), randint(50, size=1000))
          >>> bpr.test(test_data)

          (This should give an AUC of around 0.5 as the training and
          testing set are chosen at random)
        """
        self._rank = rank
        self._n_users = n_users
        self._n_items = n_items
        self._lambda_u = lambda_u
        self._lambda_i = lambda_i
        self._lambda_j = lambda_j
        self._lambda_bias = lambda_bias
        self._learning_rate = learning_rate
        self._train_users = set()
        self._train_items = set()
        self._train_dict = {}
        self._configure_theano()
        self._generate_train_model_function()

    def _configure_theano(self):
        """
          Configures Theano to run in fast mode
          and using 32-bit floats. 
        """
        theano.config.mode = 'FAST_RUN'
        theano.config.floatX = 'float32'

    def _generate_train_model_function(self):
        """
          Generates the train model function in Theano.
          This is a straight port of the objective function
          described in the BPR paper.

          We want to learn a matrix factorisation

            U = W.H^T

          where U is the user-item matrix, W is a user-factor
          matrix and H is an item-factor matrix, so that
          it maximises the difference between
          W[u,:].H[i,:]^T and W[u,:].H[j,:]^T, 
          where `i` is a positive item
          (one the user `u` has watched) and `j` a negative item
          (one the user `u` hasn't watched).
        """
        u = T.lvector('u')
        i = T.lvector('i')
        j = T.lvector('j')

        self.W = theano.shared(numpy.random.random((self._n_users, self._rank)).astype('float32'), name='W')
        self.H = theano.shared(numpy.random.random((self._n_items, self._rank)).astype('float32'), name='H')

        self.B = theano.shared(numpy.zeros(self._n_items).astype('float32'), name='B')

        x_ui = T.dot(self.W[u], self.H[i].T).diagonal()
        x_uj = T.dot(self.W[u], self.H[j].T).diagonal()

        x_uij = self.B[i] - self.B[j] + x_ui - x_uj

        obj = T.sum(T.log(T.nnet.sigmoid(x_uij)) - self._lambda_u * (self.W[u] ** 2).sum(axis=1) - self._lambda_i * (self.H[i] ** 2).sum(axis=1) - self._lambda_j * (self.H[j] ** 2).sum(axis=1) - self._lambda_bias * (self.B[i] ** 2 + self.B[j] ** 2))
        cost = - obj

        g_cost_W = T.grad(cost=cost, wrt=self.W)
        g_cost_H = T.grad(cost=cost, wrt=self.H)
        g_cost_B = T.grad(cost=cost, wrt=self.B)
        self.get_g_cost_B = theano.function(inputs=[u,i,j], outputs=g_cost_B)

        updates = [ (self.W, self.W - self._learning_rate * g_cost_W), (self.H, self.H - self._learning_rate * g_cost_H), (self.B, self.B - self._learning_rate * g_cost_B) ]

        self.train_model = theano.function(inputs=[u, i, j], outputs=cost, updates=updates)

    def train(self, train_data, epochs=30, batch_size=1000):
        """
          Trains the BPR Matrix Factorisation model using Stochastic
          Gradient Descent and minibatches over `train_data`.

          `train_data` is an array of (user_index, item_index) tuples.

          We first create a set of random samples from `train_data` for 
          training, of size `epochs` * size of `train_data`.

          We then iterate through the resulting training samples by
          batches of length `batch_size`, and run one iteration of gradient
          descent for the batch.
        """
        if len(train_data) < batch_size:
            sys.stderr.write("WARNING: Batch size is greater than number of training samples, switching to a batch size of %s\n" % str(len(train_data)))
            batch_size = len(train_data)
        self._train_dict, self._train_users, self._train_items = self._data_to_dict(train_data)
        n_sgd_samples = len(train_data) * epochs
        sgd_users, sgd_pos_items, sgd_neg_items = self._uniform_user_sampling(n_sgd_samples)
        z = 0
        t2 = t1 = t0 = time.time()
        while (z+1)*batch_size < n_sgd_samples:
            self.train_model(
                sgd_users[z*batch_size: (z+1)*batch_size],
                sgd_pos_items[z*batch_size: (z+1)*batch_size],
                sgd_neg_items[z*batch_size: (z+1)*batch_size]
            )
            z += 1
            t2 = time.time()
            sys.stderr.write("\rProcessed %s ( %.2f%% ) in %.4f seconds" %(str(z*batch_size), 100.0 * float(z*batch_size)/n_sgd_samples, t2 - t1))
            sys.stderr.flush()
    def _uniform_user_sampling(self, n_samples):
        """
          Creates `n_samples` random samples from training data for performing Stochastic
          Gradient Descent. We start by uniformly sampling users, 
          and then sample a positive and a negative item for each 
          user sample.
        """
        sys.stderr.write("Generating %s random training samples\n" % str(n_samples))
        sgd_users = numpy.array(list(self._train_users))[numpy.random.randint(len(list(self._train_users)), size=n_samples)]
        sgd_pos_items, sgd_neg_items = [], []
        for sgd_user in sgd_users:
            pos_item = self._train_dict[sgd_user][numpy.random.randint(len(self._train_dict[sgd_user]))]
            sgd_pos_items.append(pos_item)
            neg_item = numpy.random.randint(self._n_items)
            while neg_item in self._train_dict[sgd_user]:
                neg_item = numpy.random.randint(self._n_items)
            sgd_neg_items.append(neg_item)
        return sgd_users, sgd_pos_items, sgd_neg_items

    def predictions(self, user_index):
        """
          Computes item predictions for `user_index`.
          Returns an array of prediction values for each item
          in the dataset.
        """
        w = self.W.get_value()
        h = self.H.get_value()
        b = self.B.get_value()
        user_vector = w[user_index,:]
        return user_vector.dot(h.T) + b

    def prediction(self, user_index, item_index):
        """
          Predicts the preference of a given `user_index`
          for a gven `item_index`.
        """
        return self.predictions(user_index)[item_index]

    def top_predictions(self, user_index, topn=10):
        """
          Returns the item indices of the top predictions
          for `user_index`. The number of predictions to return
          can be set via `topn`.
          This won't return any of the items associated with `user_index`
          in the training set.
        """
        return [ 
            item_index for item_index in numpy.argsort(self.predictions(user_index)) 
            if item_index not in self._train_dict[user_index]
        ][::-1][:topn]
    def getTopPrediction(self, predictions,user):
        maxIdx = 0
        maxVal = 0
        for item in predictions:
            if item not in self._train_dict[user]:
                if predictions[int(item)] > maxVal:
                    maxIdx = item
                    maxVal = predictions[int(item)]
                    print("new val %d" % predictions[int(item)])
        return maxIdx
    def findClosestPos(self,topItems, currentItem, item2vec,index_to_items):
        minV = 1
        minLoc = 0
        for i,item in enumerate(topItems):
            dist =  1-spatial.distance.cosine(item2vec[index_to_items[item]],item2vec[index_to_items[currentItem]])
            if dist < minV:
                minV = dist
                minLoc = i
        return (minLoc,minV)

    def test(self, test_data,items2vec,index_to_items,index_to_users):
        """
          Computes the Area Under Curve (AUC) on `test_data`.

          `test_data` is an array of (user_index, item_index) tuples.

          During this computation we ignore users and items
          that didn't appear in the training data, to allow
          for non-overlapping training and testing sets.
        """
        test_dict, test_users, test_items = self._data_to_dict(test_data)
        auc_values = []
        z = 0
        correct = 0
        ctrItems = {}
        ctrFile = open("userCTR",'r')
        ctr2File = open("userCTRfromBPR",'w')
        for line in ctrFile.readlines():
            ctrLine = line.split()
            totalItems = [int(x) if x != '-' else x for x in ctrLine[2].split(',')]
            recommendedItems = [int(x) if x != '-' else x for x in ctrLine[3].split(',')]
            ctrItems[int(ctrLine[0])] = (totalItems, recommendedItems)
        successF = open("successK",'w')
        MRRf = open("mrrRes",'w')
        MRRsoft = open("mrrSoftRes", 'w')
        totalUsers = len(test_dict.keys())
        for user in test_dict.keys():
            if user in self._train_users:
                auc_for_user = 0.0
                n = 0
                z += 1
                predictions = self.predictions(user)
                topItems = [int(x) for x in self.top_predictions(user,1000)]
                #topItems = [int(index_to_items[int(x)]) for x in self.top_predictions(user,10)]
                #print(test_dict[user][0],topItems)
                #print(ctrItems[int(index_to_users[user])][0])
                #numeratorItems = set(topItems) & set(ctrItems[int(index_to_users[user])][0])
                #denominatorItems = set(topItems) & set(ctrItems[int(index_to_users[user])][1])
                #print(str(index_to_users[user])  + " " + str(numeratorItems) + " " + str(denominatorItems) + "\n")
                #ctr2File.write(str(index_to_users[user])  + " " + str(len(numeratorItems)) + " " + str(len(denominatorItems)) + "\n")
                #print("item for user %d for item %d real item is %d" %(user, int(index_to_items[int(topItem)]),int(index_to_items[test_dict[user][0]])))
                if test_dict[user][0] in topItems:
                    correct +=1
                    successF.write(index_to_users[user] + "\t1\n")
                    print("found corect item for user %s for item %d" %(index_to_users[user], int(index_to_items[test_dict[user][0]])))
                    #print(correct/z)
                else:
                    successF.write(index_to_users[user] + "\t 0\n")
                positions = [i for i,x in enumerate(topItems) if x == test_dict[user][0]]
                if(len(positions) > 0):
                    MRRf.write(index_to_users[user] + "\t"+ str(1/(positions[0]+1)) +"\n")
                    MRRsoft.write(index_to_users[user] + "\t"+ str(1/(positions[0]+1)) +"\n")

                else:
                    closestPos = self.findClosestPos(topItems, test_dict[user][0], items2vec,index_to_items)
                    MRRsoft.write(index_to_users[user] + "\t"+str(1/closestPos[0])+"\n")
                    MRRf.write(index_to_users[user] + "\t0\n")  
                '''for pos_item in test_dict[user]:
                    if pos_item in self._train_items:
                        for neg_item in self._train_items:
                            if neg_item not in test_dict[user] and neg_item not in self._train_dict[user]:
                                n += 1
                                if predictions[pos_item] > predictions[neg_item]:
                                    auc_for_user += 1
                                #else:
                                    #print(index_to_items[int(pos_item)],index_to_items[int(neg_item)])
                                #pos_item_it = index_to_items[int(pos_item)]
                                #neg_item_it = index_to_items[int(neg_item)]  
                                #auc_for_user += 1-spatial.distance.cosine(items2vec[pos_item_it],items2vec[neg_item_it])
                if n > 0:
                    auc_for_user /= n
                    auc_values.append(auc_for_user)
                z += 1
                if z % 100 == 0 and len(auc_values) > 0:
                    sys.stderr.write("\rCurrent AUC mean (%s samples): %0.5f" % (str(z), numpy.mean(auc_values)))
                    sys.stderr.flush()'''
                sys.stderr.write("\r" +str(z/totalUsers))
                sys.stderr.flush()
        sys.stderr.write("\n")
        sys.stderr.flush()
        return numpy.mean(auc_values)

    def _data_to_dict(self, data):
        data_dict = defaultdict(list)
        items = set()
        for (user, item) in data:
            data_dict[user].append(item)
            items.add(item)
        return data_dict, set(data_dict.keys()), items
