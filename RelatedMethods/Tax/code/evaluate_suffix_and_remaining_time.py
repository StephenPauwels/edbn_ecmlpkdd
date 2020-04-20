'''
this script takes as input the LSTM or RNN weights found by train.py
change the path in line 178 of this script to point to the h5 file
with LSTM or RNN weights generated by train.py

Author: Niek Tax
'''

from __future__ import division

import copy
import csv
import os

import distance
import numpy as np
from jellyfish._jellyfish import damerau_levenshtein_distance
from keras.models import load_model


def evaluate(train_log, test_log, model_folder, model_file):
    caseid_col = 0
    role_col = 2
    task_col = 1

    csvfile = open(train_log, 'r')
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
            numlines+=1
        line+=chr(int(row[task_col])+ascii_offset)
        firstLine = False

    # add last case
    lines.append(line)
    numlines+=1

    csvfile = open(test_log, 'r')
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
    next(spamreader, None)  # skip the headers
    ascii_offset = 161

    for row in spamreader: #the rows are "CaseID,ActivityID,CompleteTimestamp"
        if row[caseid_col]!=lastcase:  #'lastcase' is to save the last executed case for the loop
            lastcase = row[caseid_col]
            if not firstLine:
                lines.append(line)
            line = ''
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
    csvfile = open(test_log, 'r')
    spamreader = csv.reader(csvfile, delimiter=',', quotechar='|')
    next(spamreader, None)  # skip the headers
    for row in spamreader:
        if row[caseid_col]!=lastcase:
            caseids.append(row[caseid_col])
            lastcase = row[caseid_col]
            if not firstLine:
                lines.append(line)
            line = ''
            numlines+=1
        line+=chr(int(row[task_col])+ascii_offset)
        firstLine = False

    # add last case
    lines.append(line)
    numlines+=1

    # set parameters
    predict_size = maxlen

    # load model, set this to the model generated by train.py
    model = load_model(os.path.join(model_folder, model_file))

    # define helper functions
    def encode(sentence, maxlen=maxlen):
        num_features = len(chars)+1
        X = np.zeros((1, maxlen, num_features), dtype=np.float32)
        leftpad = maxlen-len(sentence)
        for t, char in enumerate(sentence):
            for c in chars:
                if c==char:
                    X[0, t+leftpad, char_indices[c]] = 1
            X[0, t+leftpad, len(chars)] = t+1
        return X

    def getSymbol(predictions):
        maxPrediction = 0
        symbol = ''
        i = 0;
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
    with open(os.path.join(model_folder, "suffix_predictions.csv"), 'w') as csvfile:
        spamwriter = csv.writer(csvfile, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        spamwriter.writerow(["CaseID", "Prefix length", "Groud truth", "Predicted", "Levenshtein", "Damerau", "Jaccard", "Ground truth times", "Predicted times", "RMSE", "MAE"])
        for prefix_size in range(2,maxlen):
            print(prefix_size)
            for line, caseid in zip(lines, caseids):
                cropped_line = ''.join(line[:prefix_size])
                ground_truth = ''.join(line[prefix_size:prefix_size+predict_size])
                predicted = ''
                for i in range(predict_size):
                    enc = encode(cropped_line)
                    y = model.predict(enc, verbose=0) # make predictions
                    # split predictions into seperate activity and time predictions
                    y_char = y[0]
                    prediction = getSymbol(y_char) # undo one-hot encoding
                    cropped_line += prediction
                    if prediction == '!': # end of case was just predicted, therefore, stop predicting further into the future
                        break
                    predicted += prediction
                output = []
                if len(ground_truth)>0:
                    output.append(caseid)
                    output.append(prefix_size)
                    output.append(str(ground_truth).encode("utf-8"))
                    output.append(str(predicted).encode("utf-8"))
                    output.append(1 - distance.nlevenshtein(predicted, ground_truth))
                    dls = 1 - (damerau_levenshtein_distance(str(predicted), str(ground_truth)) / max(len(predicted),len(ground_truth)))
                    if dls<0:
                        dls=0 # we encountered problems with Damerau-Levenshtein Similarity on some linux machines where the default character encoding of the operating system caused it to be negative, this should never be the case
                    output.append(dls)
                    output.append(1 - distance.jaccard(predicted, ground_truth))
                    output.append('')
                    output.append('')
                    output.append('')
                    output.append('')
                    #output.append(metrics.median_absolute_error([ground_truth_t], [total_predicted_time]))
                    spamwriter.writerow(output)
