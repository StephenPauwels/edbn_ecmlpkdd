# -*- coding: utf-8 -*-
"""
Created on Wed Nov 21 21:23:55 2018

@author: Manuel Camargo
"""
import os
import csv
import math
import itertools

import keras.utils as ku

import pandas as pd
import numpy as np

from nltk.util import ngrams

from models import model_specialized as msp
from models import model_concatenated as mcat
from models import model_shared as msh
from models import model_shared_cat as mshcat
from models import model_joint as mj

from support_modules.readers import log_reader as lr
from support_modules import role_discovery as rl
from support_modules import nn_support as nsup
from support_modules import support as sup


def training_model(full_log, log_train, log_test, outfile, args):
    """Main method of the training module.
    """

    # Index creation
    # ac_index = {}
    # index_ac = {}
    # i = 1
    # for val in log_train.values[log_train.activity]:
    #     ac_index[val] = i
    #     index_ac[i] = val
    #     i += 1
    # ac_index["None"] = 0
    # index_ac[0] = "None"
    #
    # rl_index = {}
    # index_rl = {}
    # i = 1
    # for val in log_train.values["role"]:
    #     rl_index[val] = i
    #     index_rl[i] = val
    #     i += 1
    # rl_index["None"] = 0
    # index_rl[0] = "None"

    ac_index = create_index(full_log.data, 'event')
    ac_index['start'] = 0
    ac_index['end'] = len(ac_index)
    index_ac = {v: k for k, v in ac_index.items()}

    rl_index = create_index(full_log.data, 'role')
    rl_index['start'] = 0
    rl_index['end'] = len(rl_index)
    index_rl = {v: k for k, v in rl_index.items()}

    # Load embedded matrix
    ac_weights = load_embedded(index_ac, os.path.join(outfile, 'event.emb'))
    rl_weights = load_embedded(index_rl, os.path.join(outfile, 'role.emb'))
    # Calculate relative times
    log_df_train = add_calculated_features(log_train.data, ac_index, rl_index)
    log_df_test = add_calculated_features(log_test.data, ac_index, rl_index)
    # Split validation datasets
    # log_df_train, log_df_test = nsup.split_train_test(log_df, 0.3) # 70%/30%
    # Input vectorization
    vec = vectorization(log_df_train, ac_index, rl_index, args)
    # Parameters export
    output_folder = os.path.join(outfile, args['model_type'])
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    parameters = {}
    parameters['event_log'] = args['file_name']
    parameters['exp_desc'] = args
    parameters['index_ac'] = index_ac
    parameters['index_rl'] = index_rl
    parameters['dim'] = dict(samples=str(vec['prefixes']['x_ac_inp'].shape[0]),
                             time_dim=str(vec['prefixes']['x_ac_inp'].shape[1]),
                             features=str(len(ac_index)))

    sup.create_json(parameters, os.path.join(output_folder,
                                             'model_parameters.json'))
    # sup.create_csv_file_header(log_df_test.to_dict('records'),
    #                            os.path.join(output_folder,
    #                                         'data',
    #                                         'test_log.csv'))
    # sup.create_csv_file_header(log_df_train.to_dict('record'),
    #                            os.path.join(output_folder,
    #                                         'data',
    #                                         'train_log.csv'))

    if args['model_type'] == 'joint':
        mj.training_model(vec, ac_weights, rl_weights, output_folder, args)
    elif args['model_type'] == 'shared':
        msh.training_model(vec, ac_weights, rl_weights, output_folder, args)
    elif args['model_type'] == 'specialized':
        msp.training_model(vec, ac_weights, rl_weights, output_folder, args)
    elif args['model_type'] == 'concatenated':
        mcat.training_model(vec, ac_weights, rl_weights, output_folder, args)
    elif args['model_type'] == 'shared_cat':
        mshcat.training_model(vec, ac_weights, rl_weights, output_folder, args)

    return output_folder

# =============================================================================
# Load embedded matrix
# =============================================================================

def load_embedded(index, filename):
    """Loading of the embedded matrices.
    Args:
        index (dict): index of activities or roles.
        filename (str): filename of the matrix file.
    Returns:
        numpy array: array of weights.
    """
    weights = list()
    with open(filename, 'r') as csvfile:
        filereader = csv.reader(csvfile, delimiter=',', quotechar='"')
        for row in filereader:
            cat_ix = int(row[0])
            if str(index[cat_ix]) == row[1].strip():
                weights.append([float(x) for x in row[2:]])
        csvfile.close()
    return np.array(weights)

# =============================================================================
# Pre-processing: n-gram vectorization
# =============================================================================
def vectorization(log_df, ac_index, rl_index, args):
    """Example function with types documented in the docstring.
    Args:
        log_df (dataframe): event log data.
        ac_index (dict): index of activities.
        rl_index (dict): index of roles.
        args (dict): parameters for training the network
    Returns:
        dict: Dictionary that contains all the LSTM inputs.
    """
    if args['norm_method'] == 'max':
        log_df = reformat_events(log_df, ac_index, rl_index)
    elif args['norm_method'] == 'lognorm':
        log_df = reformat_events(log_df, ac_index, rl_index)

    vec = {'prefixes':dict(), 'next_evt':dict()}
    # n-gram definition
    for i, _ in enumerate(log_df):
        ac_n_grams = list(ngrams(log_df[i]['ac_order'], args['n_size'],
                                 pad_left=True, left_pad_symbol=0))
        rl_n_grams = list(ngrams(log_df[i]['rl_order'], args['n_size'],
                                 pad_left=True, left_pad_symbol=0))

        st_idx = 0
        if i == 0:
            vec['prefixes']['x_ac_inp'] = np.array([ac_n_grams[0]])
            vec['prefixes']['x_rl_inp'] = np.array([rl_n_grams[0]])
            vec['next_evt']['y_ac_inp'] = np.array(ac_n_grams[1][-1])
            vec['next_evt']['y_rl_inp'] = np.array(rl_n_grams[1][-1])
            st_idx = 1
        for j in range(st_idx, len(ac_n_grams)-1):
            vec['prefixes']['x_ac_inp'] = np.concatenate((vec['prefixes']['x_ac_inp'],
                                                          np.array([ac_n_grams[j]])), axis=0)
            vec['prefixes']['x_rl_inp'] = np.concatenate((vec['prefixes']['x_rl_inp'],
                                                          np.array([rl_n_grams[j]])), axis=0)
            vec['next_evt']['y_ac_inp'] = np.append(vec['next_evt']['y_ac_inp'],
                                                    np.array(ac_n_grams[j+1][-1]))
            vec['next_evt']['y_rl_inp'] = np.append(vec['next_evt']['y_rl_inp'],
                                                    np.array(rl_n_grams[j+1][-1]))


    vec['next_evt']['y_ac_inp'] = ku.to_categorical(vec['next_evt']['y_ac_inp'],
                                                    num_classes=len(ac_index))
    vec['next_evt']['y_rl_inp'] = ku.to_categorical(vec['next_evt']['y_rl_inp'],
                                                    num_classes=len(rl_index))
    return vec

def add_calculated_features(log_df, ac_index, rl_index):
    """Appends the indexes and relative time to the dataframe.
    Args:
        log_df: dataframe.
        ac_index (dict): index of activities.
        rl_index (dict): index of roles.
    Returns:
        Dataframe: The dataframe with the calculated features added.
    """
    # ac_idx = lambda x: ac_index[x['task']]
    # log_df['ac_index'] = log_df.apply(ac_idx, axis=1)
    log_df['ac_index'] = log_df['event']

    # rl_idx = lambda x: rl_index[x['role']]
    # log_df['rl_index'] = log_df.apply(rl_idx, axis=1)
    log_df['rl_index'] = log_df['role']

    log_df['tbtw'] = 0
    log_df['tbtw_norm'] = 0

    log_df = log_df.to_dict('records')

#    log_df = sorted(log_df, key=lambda x: (x['caseid'], x['end_timestamp']))
#    for _, group in itertools.groupby(log_df, key=lambda x: x['caseid']):
#        trace = list(group)
#        for i, _ in enumerate(trace):
#            if i != 0:
#                trace[i]['tbtw'] = (trace[i]['end_timestamp'] -
#                                    trace[i-1]['end_timestamp']).total_seconds()

    return pd.DataFrame.from_records(log_df)

def reformat_events(log_df, ac_index, rl_index):
    """Creates series of activities, roles and relative times per trace.
    Args:
        log_df: dataframe.
        ac_index (dict): index of activities.
        rl_index (dict): index of roles.
    Returns:
        list: lists of activities, roles and relative times.
    """
    log_df = log_df.to_dict('records')
    print(rl_index)
    temp_data = list()
#    log_df = sorted(log_df, key=lambda x: (x['caseid'], x['end_timestamp']))
    for key, group in itertools.groupby(log_df, key=lambda x: x['case']):
        trace = list(group)
        ac_order = [x['ac_index'] for x in trace]
        rl_order = [x['rl_index'] for x in trace]
        tbtw = [x['tbtw_norm'] for x in trace]
        ac_order.insert(0, ac_index[('start')])
        ac_order.append(ac_index[('end')])
        rl_order.insert(0, rl_index[('start')])
        rl_order.append(rl_index[('end')])
        tbtw.insert(0, 0)
        tbtw.append(0)
        temp_dict = dict(caseid=key,
                         ac_order=ac_order,
                         rl_order=rl_order,
                         tbtw=tbtw)
        temp_data.append(temp_dict)

    return temp_data


# =============================================================================
# Support
# =============================================================================


def create_index(log_df, column):
    """Creates an idx for a categorical attribute.
    Args:
        log_df: dataframe.
        column: column name.
    Returns:
        index of a categorical attribute pairs.
    """
    temp_list = log_df[[column]].values.tolist()
    subsec_set = {(x[0]) for x in temp_list}
    subsec_set = sorted(list(subsec_set))
    alias = dict()
    for i, _ in enumerate(subsec_set):
        alias[subsec_set[i]] = i + 1
    return alias

def max_serie(log_df, serie):
    """Returns the max and min value of a column.
    Args:
        log_df: dataframe.
        serie: name of the serie.
    Returns:
        max and min value.
    """
    max_value, min_value = 0, 0
    for record in log_df:
        if np.max(record[serie]) > max_value:
            max_value = np.max(record[serie])
        if np.min(record[serie]) > min_value:
            min_value = np.min(record[serie])
    return max_value, min_value

def max_min_std(val, max_value, min_value):
    """Standardize a number between range.
    Args:
        val: Value to be standardized.
        max_value: Maximum value of the range.
        min_value: Minimum value of the range.
    Returns:
        Standardized value between 0 and 1.
    """
    std = (val - min_value) / (max_value - min_value)
    return std
