'''
this script takes as input the LSTM or RNN weights found by train.py
change the path in line 176 of this script to point to the h5 file
with LSTM or RNN weights generated by train.py

Author: Niek Tax
'''

from __future__ import division
from keras.models import load_model
import csv
import copy
import numpy as np
import distance
from jellyfish._jellyfish import damerau_levenshtein_distance
import unicodecsv
from sklearn import metrics
from math import sqrt
import time
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from collections import Counter

train_eventlog = "../../Camargo/output_files/HELPDESK_20000000_0_0_0_0_1/shared_cat/data/train_log.csv"
test_eventlog = "../../Camargo/output_files/HELPDESK_20000000_0_0_0_0_1/shared_cat/data/test_log.csv"
eventlog_name = "HELPDESK"
caseid_col = 1
role_col = 3
task_col = 4

csvfile = open(test_eventlog, 'r')
spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
next(spamreader, None)  # skip the headers
ascii_offset = 161

lastcase = ''
line = ''
firstLine = True
lines = []
caseids = []
numlines = 0
for row in spamreader:
    if row[caseid_col]!=lastcase:
        caseids.append(row[caseid_col])
        lastcase = row[caseid_col]
        if not firstLine:        
            lines.append(line)
        line = ''
        times = []
        numlines+=1
    line+=chr(int(row[task_col])+ascii_offset)
    firstLine = False

# add last case
lines.append(line)
numlines+=1

step = 1
sentences = []
softness = 0
next_chars = []
lines = list(map(lambda x: x+'!',lines))
maxlen = max(map(lambda x: len(x),lines))

chars = map(lambda x : set(x),lines)
chars = list(set().union(*chars))
chars.sort()
target_chars = copy.copy(chars)
chars.remove('!')
print('total chars: {}, target chars: {}'.format(len(chars), len(target_chars)))
char_indices = dict((c, i) for i, c in enumerate(chars))
indices_char = dict((i, c) for i, c in enumerate(chars))
target_char_indices = dict((c, i) for i, c in enumerate(target_chars))
target_indices_char = dict((i, c) for i, c in enumerate(target_chars))
print(indices_char)

lastcase = ''
line = ''
firstLine = True
lines = []
caseids = []
numlines = 0

csvfile = open(test_eventlog, 'r')
spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
next(spamreader, None)  # skip the headers
for row in spamreader:
    if row[caseid_col]!=lastcase:
        caseids.append(row[caseid_col])
        lastcase = row[caseid_col]
        if not firstLine:        
            lines.append(line)
        line = ''
        times = []
        numlines+=1
    line+=chr(int(row[task_col])+ascii_offset)
    firstLine = False

# add last case
lines.append(line)
numlines+=1

# set parameters
predict_size = 1

# load model, set this to the model generated by train.py
model = load_model('output_files/models/model_05-0.50.h5')

# define helper functions
def encode(sentence, maxlen=maxlen):
    num_features = len(chars)+5
    X = np.zeros((1, maxlen, num_features), dtype=np.float32)
    leftpad = maxlen-len(sentence)
    for t, char in enumerate(sentence):
        multiset_abstraction = Counter(sentence[:t+1])
        for c in chars:
            if c==char:
                X[0, t+leftpad, char_indices[c]] = 1
        X[0, t+leftpad, len(chars)] = t+1
    return X

def getSymbol(predictions):
    maxPrediction = 0
    symbol = ''
    i = 0
    for prediction in predictions:
        if(prediction>=maxPrediction):
            maxPrediction = prediction
            symbol = target_indices_char[i]
        i += 1
    return symbol

one_ahead_gt = []
one_ahead_pred = []

two_ahead_gt = []
two_ahead_pred = []

three_ahead_gt = []
three_ahead_pred = []


# make predictions
with open('output_files/results/next_activity_and_time_%s' % eventlog_name, 'w') as csvfile:
    spamwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
    spamwriter.writerow(["CaseID", "Prefix length", "Groud truth", "Predicted", "Levenshtein", "Damerau", "Jaccard", "Ground truth times", "Predicted times", "RMSE", "MAE"])
    for prefix_size in range(2,maxlen):
        print(prefix_size)
        for line, caseid in zip(lines, caseids):
            cropped_line = ''.join(line[:prefix_size])
            if '!' in cropped_line:
                continue # make no prediction for this case, since this case has ended already
            ground_truth = ''.join(line[prefix_size:prefix_size+predict_size])
            predicted = ''
            predicted_t = []
            for i in range(predict_size):
                if len(ground_truth)<=i:
                    continue
                enc = encode(cropped_line)
                y = model.predict(enc, verbose=0)
                y_char = y[0]
                prediction = getSymbol(y_char)
                cropped_line += prediction
                if prediction == '!': # end of case was just predicted, therefore, stop predicting further into the future
                    break
                predicted += prediction
            output = []
            if len(ground_truth)>0:
                output.append(caseid)
                output.append(prefix_size)
                output.append(str(ground_truth))
                output.append(str(predicted))
                output.append(1 - distance.nlevenshtein(predicted, ground_truth))
                dls = 1 - (damerau_levenshtein_distance(str(predicted), str(ground_truth)) / max(len(predicted),len(ground_truth)))
                if dls<0:
                    dls=0 # we encountered problems with Damerau-Levenshtein Similarity on some linux machines where the default character encoding of the operating system caused it to be negative, this should never be the case
                output.append(dls)
                output.append(1 - distance.jaccard(predicted, ground_truth))
                output.append(' ')
                output.append(' ')

                output.append('')
                output.append('')
                output.append('')
                spamwriter.writerow(output)