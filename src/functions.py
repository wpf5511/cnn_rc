import re
import logging
import numpy as np
import tensorflow as tf
from keras import backend as K
from keras.engine.topology import Layer
from keras import initializations
from functools import partial
import numpy as np


from keras import backend as K


''' accuracy that chooses a class from the class embedding 
and compares with the categorical cross-entropy '''
def accuracy2(class_emb, y_true, y_pred):
    
    # y_pred_max = K.argmax(K.dot(y_pred, K.transpose(class_emb)), axis=-1)
    y_pred_max = K.argmax(K.dot(K.transpose(y_pred), class_emb), axis=-1)


    y_true_max = K.argmax(y_true, axis=-1)

    acc = K.mean(K.equal(y_true_max, y_pred_max))

    return acc
    


''' courtesy of keras.io '''
def fbetascore(y_true, y_pred, beta=1):
    if beta < 0:
        raise ValueError('The lowest choosable beta is zero (only precision).')
    # Count positive samples.
    c1 = K.sum(K.round(K.clip(y_true * y_pred, 0, 1)))
    c2 = K.sum(K.round(K.clip(y_pred, 0, 1)))
    c3 = K.sum(K.round(K.clip(y_true, 0, 1)))
    
    # If there are no true samples, fix the F score at 0.
    if c3 == 0:
        return 0
    # How many selected items are relevant?
    precision = c1 / c2
    # How many relevant items are selected?
    recall = c1 / c3
    # Weight precision and recall together as a single scalar.
    beta2 = beta ** 2
    f_score = (1 + beta2) * (precision * recall) / (beta2 * precision + recall)
    return f_score

def debug_print_dict(input, msg):
    logging.debug("#" * 30)
    logging.debug(msg)
    for k, v in input.iteritems():
        logging.debug(str(k) + " : " + str(v))
    logging.debug(msg + " length: ")
    logging.debug(len(input))
    logging.debug("#" * 30)

def debug_print(input, msg):
    logging.debug("#" * 30)
    logging.debug(msg)
    for line in input:
        logging.debug(line)
    logging.debug("#" * 30)

def clean_classes(dict):
    clean = set([x.split("(")[0] for x in dict])
    count = 0
    o = {}
    for c in clean:
        o[c] = count
        count += 1
    return o

def process_train(line):
    # split on quotes and get the raw text
    stripped = re.sub("\d{0,4}", "", line, count=1).strip()
    return stripped[1:len(stripped)-2]

''' NOVEL DISTANCE FUNCTION EH? '''
def new_dist(actual, embedding):

    import ipdb
    ipdb.sset_trace()

    actual_sum = tf.reduce_sum(actual, keep_dims=True)
    actual_unit = actual / actual_sum

    embedding_sum = tf.reduce_sum(embedding, keep_dims=True)
    embedding_unit = embedding / embedding_sum


    result = tf.sqrt(tf.reduce_sum(K.square(actual_unit - embedding_unit), 2, keep_dims=True))
    return result


def new_dist3(pred, embedding):
    import ipdb
    ipdb.sset_trace()

    pred_sum = tf.reduce_sum(pred, 1, keep_dims=True)
    pred_unit = pred / pred_sum

    embedding_sum = tf.reduce_sum(embedding)
    embedding_unit = embedding / embedding_sum

    internal_dist = pred_unit - embedding_unit  

    squared = K.square(internal_dist)    

    sum_for_dist = tf.reduce_sum(squared, 1, keep_dims=True)

    result = tf.sqrt(sum_for_dist)
    return result


### TODO test this shit!!!! :D ###
def margin_loss(weights, y_true, y_pred):


    nb_clz = weights.get_shape()[0]

    import ipdb
    ipdb.sset_trace()

    distances = new_dist3(y_pred, weights)

    # index_mask = tf.reshape(tf.one_hot(y_true, nb_clz), [-1,nb_clz])

    true_pred = tf.reduce_sum(distances * index_mask,1)

#    partial_dist = partial(new_dist, embedding=weights)
 #   distances = tf.map_fn(partial_dist, y_pred, dtype=tf.float32)


    #correct = tf.gather(w, y_true)
    # tf.cast(y_true, dtype=tf.int32)
    # correct_embeddings = tf.gather(weights, tf.cast(    y_true, dtype=tf.int32))

    best_incorrect_dist_idx = tf.argmax(distances,1)
    incorrect_dist = distances[1] 

    true_dist = new_dist(correct,y_pred)


    return 1.0 + true_dist - incorrect_dist



def new_dist2(weights):
    
    actual_sum = tf.reduce_sum(actual, 1, keep_dims=True)
    unit_actual = actual / actual_sum
    return tf.sqrt(tf.reduce_sum(K.square(unit_actual - weights), 1, keep_dims=True))








def att_comp2(tensor_list):
    from keras import backend as K
    import tensorflow as tf
    return K.batch_dot(tensor_list[0],tensor_list[1]) 














class MultLayer(Layer):
    def __init__(self, output_dim, **kwargs):
        self.init = initializations.get('glorot_uniform')
        self.output_dim = output_dim[1]
        super(MultLayer, self).__init__(**kwargs)

    def build(self, input_shape):
        input_dim = input_shape[2]
        initial_weight_value = np.random.random((input_dim, self.output_dim))
        
        self.W = self.init((input_dim, self.output_dim),
                           name='{}_W'.format(self.name))

        self.trainable_weights = [self.W]
        super(MultLayer, self).build(input_shape)  # be sure you call this somewhere

    def call(self, x, mask=None):
        print "hej"
        return K.dot(x, self.W)

    def get_output_shape_for(self, input_shape):
        import ipdb
        ipdb.sset_trace()
        return (input_shape[0], self.output_dim)
