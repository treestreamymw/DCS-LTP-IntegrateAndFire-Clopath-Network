from brian2 import *
import numpy as np
import pandas as pd
from scipy import stats
import copy
import os


def _load_group_data(directory='', file_name='', df=True):
    """ Load group data from folder
    
    ==Args==
    -directory : directory where group data is stored including /
    -file_name : file name for group data file, including extension (.pkl)
                -file_name cannot contain the string 'data', since this string is used t search for individual data files
    -df : logical, if True group data is stored as a pandas dataframe.  if False group data is stored as nested dictionary


    ==Out==
    -group_data  : typically a dictionary.  If no file is found with the specified string, an empty dictionary is returned

    ==Updates==
    -none

    ==Comments==
    -if brian objects are stored in group data, they cannot be pickled.  convert to numpy arrays before storing group data
    """

    # check if folder exists with experiment name
    if os.path.isdir(directory) is False:
        print 'making new directory to save data'
        os.mkdir(directory)
    
    # all files in directory
    files = os.listdir(directory)

    # if data file already exists
    if file_name in files:
        print 'group data found:', file_name

        # if data stored as pandas dataframe
        if df:
            # load data
            print directory+file_name
            group_data = pd.read_pickle(directory+file_name)
            print 'group data loaded'

        # if stored as dictionary
        else:
            # load data
            with open(directory+file_name, 'rb') as pkl_file:
                group_data= pickle.load(pkl_file)
            print 'group data loaded'

    # otherwise create data structure
    else:
        # data organized as {frequency}{syn distance}{number of synapses}{polarity}[trial]{data type}{tree}[section][segment][spikes]
        print 'no group data found'
        if df:
            group_data = pd.DataFrame()
        else:
            group_data= {}

    return group_data 

def _rec2df(rec, P):
    ''' convert recording objects from brian into pandas dataframe

    ==Args==
    -rec : recording structure containing brian objects.  organized as rec{group_type}{group}.brian_state_monitors.  e.g. rec{'neurons'}{'1'}.u
    -P : parameter object with attributes
            ~simulation, neurons, synapses, input, network, init_neurons, init_synapses
            ~each attribute is a dictionary of groups.  e.g. P.neurons['1'] contains parameters for neuron group 1

    ==Out==
    -df : pandas dataframe with hierarchical multiindexing, with level 0 specifying the variable that was recorded ('u', 'w', 'I_nmda') and level 1 specifying the type of data/info ('data', 'trial_id', 'field_mag')  
    
    ==Updates==
    
    ==Comments==
    -all entries in df are stored as numpy arrays
    -df cannot directly store brian objects, as they cannot be pickled and saved (this may be related to brian objects that are not in the top level namespace. see answers here: https://stackoverflow.com/questions/8804830/python-multiprocessing-pickling-error)
    '''
    group_data={}
    # iterate over type of recorded object
    for group_type_key, group_type in rec.iteritems():
        # if group_type_key not in group_data:
        #     group_data[group_type_key] = {}
        # iterate over groups
        for group_key, group in group_type.iteritems():

            # iterate over recorded variables
            for var in group.record_variables:
                
                # numpy array 
                data_array = getattr(group, var)
                n = data_array.shape[0]

                if group_type_key == 'synapses':
                    pre_index = np.array(group.source.i)
                    post_index = np.array(group.source.j)
                else:
                    pre_index = np.array([np.nan]*n)
                    post_index = np.array([np.nan]*n)

                # numpy array of recorded data (recorded objects x time)
                group_data[(var,'data')]=data_array,

                # index of recorded objects in brian space
                group_data[(var,'brian_index')]=group.record,

                # indices of pre and post synaptic neurons (for synapses only, nan's are entered otherwise)
                group_data[(var,'pre_index')]=pre_index,
                group_data[(var,'post_index')]=post_index,

                # name of brian object
                group_data[(var,'brian_group_name')]=np.array([group.source.name]*n),
                
                # name of object in higher level namespace
                group_data[(var,'group_name')]=np.array([group_key]*n),

                # unique trial identifier
                group_data[(var,'trial_id')]=np.array([P.simulation['trial_id']]*n),

                # parameter dictionary objects
                group_data[(var,'P')]=np.array([P]*n),

                # electric field magnitude
                group_data[(var,'field_mag')]=np.array([P.simulation['field_mag']]*n),

    df = pd.DataFrame(group_data)

    return df

def _rec2dict(rec, P):
    ''' convert recording objects from brian 
    '''
    group_data={}
    # iterate over type of recorded object
    for group_type_key, group_type in rec.iteritems():
        # if group_type_key not in group_data:
        #     group_data[group_type_key] = {}
        # iterate over groups
        for group_key, group in group_type.iteritems():

            # iterate over recorded variables
            for var in group.record_variables:
                
                # numpy array 
                data_array = getattr(group, var)
                n = data_array.shape[0]

                if group_type_key == 'synapses':
                    pre_index = group.source.i
                    post_index = group.source.j
                else:
                    pre_index = np.array([np.nan]*n)
                    post_index = np.array([np.nan]*n)
                
                group_data[var] = {

                # numpy array of recorded data (recorded objects x time)
                'data':data_array,

                # index of recorded objects in brian space
                'index':group.record,

                # indices of pre and post synaptic neurons (for synapses only, nan's are entered otherwise)
                'pre_index':pre_index,
                'post_index':post_index,

                # name of brian object
                'brian_group_name':np.array([group.source.name]*n),
                
                # name of object in higher level namespace
                'group_name':np.array([group_key]*n),

                # unique trial identifier
                'trial_id': np.array([P.simulation['trial_id']]*n),

                # parameter dictionary objects
                'P':np.array([P]*n),

                # electric field magnitude
                'field_mag':np.array([P.simulation['field_mag']]*n),
                }

    return group_data

def _dict2frame(data_dict):
    '''
    '''
    data_frames = {}
    for key, val in data_dict.iteritems():

        data_frames[key] = pd.DataFrame( dict( [(k, pd.Series(list(v))) for k,v in val.iteritems()]))
    return data_frames

def _add_to_group_data(group_data, data_dict):
    '''
    '''
    for variable_key, variable in data_dict.iteritems():
        if variable_key not in group_data:
            group_data[variable_key] = variable
            continue
        for data_key, data in variable.iteritems():
            if data_key not in group_data[variable_key]:
                group_data[variable_key][data_key] = data
            else:
                # print data_key, group_data[variable_key][data_key]
                # print data_key, data
                group_data[variable_key][data_key] = np.append(group_data[variable_key][data_key], data, axis=0)

    return group_data