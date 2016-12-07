
import numpy as np

from keras.optimizers import Adadelta, SGD
from keras.utils.np_utils import to_categorical
from keras.models import Model
from keras.layers import Dense, Activation, Embedding, Input, merge, Flatten, Reshape
from keras.layers import Merge
from keras.layers import Convolution2D as Conv2D
from keras.layers.core import Dropout
from keras.layers.pooling import GlobalMaxPooling2D
from keras.regularizers import l2
from keras.constraints import maxnorm
from keras import backend as K
from functions import fbetascore, margin_loss


def get_model(
    word_embeddings,
    word_index, 
    n, 
    word_entity_dictionary={},
    WORD_EMBEDDING_DIM=300,
    POS_EMBEDDING_DIM=50,
    L2_NORM_MAX=3,
    INCLUDE_POS_EMB=True,
    INCLUDE_ATTENTION=False,
    ACTIVATION_FUNCTION="tanh",
    optimizer='ada',
    loss=margin_loss,
    DROPOUT_RATE=0.5, 
    NO_OF_CLASSES=19):
    # NOTE TO SELF - Don't let the vector be all-zeroes when the word is not present


    missed_words = 0
    embedding_matrix = np.zeros((len(word_index) + 1, WORD_EMBEDDING_DIM))
    for word, i in word_index.items():
        try:
            embedding_vector = word_embeddings[word]
        except KeyError:
            missed_words += 1
            #embedding_vector = oov_vector
            embedding_vector = np.random.uniform(-0.25, 0.25, WORD_EMBEDDING_DIM)
        finally:
            embedding_matrix[i] = embedding_vector

    #### attention matrix initialization 
    attention_matrix = np.zeros((len(word_entity_dictionary) + 1, 1))
    for (w,e),idx in word_entity_dictionary.iteritems():
        emb1 = embedding_matrix[w]
        emb2 = embedding_matrix[e]
        a_val = np.inner(emb1, emb2)
        attention_matrix[idx] = a_val




    embedding_layer = Embedding(len(word_index) + 1,
                                WORD_EMBEDDING_DIM,
                                weights=[embedding_matrix],
                                input_length=n,
                                trainable=True)



    position_embedding = Embedding(2 * n - 1,
                                   POS_EMBEDDING_DIM,
                                   init='zero',
                                   input_length=n,
                                   trainable=True)

    ### Attention matrice
    att_embbeding = Embedding(len(word_entity_dictionary)+1,
                                1,
                                weights=[attention_matrix],
                                input_length=n,
                                trainable=True)
    


    sequence_input = Input(shape=(n,), dtype="int32")
    position_input_1 = Input(shape=(n,), dtype="int32")
    position_input_2 = Input(shape=(n,), dtype="int32")


    word_embeddings = embedding_layer(sequence_input)
    position_embeddings_1 = position_embedding(position_input_1)
    position_embeddings_2 = position_embedding(position_input_2)

    
    if INCLUDE_ATTENTION:
        attention_input_1 = Input(shape=(n,), dtype="int32")
        attention_input_2 = Input(shape=(n,), dtype="int32")
        attention_score_1 = att_embbeding(attention_input_1)
        attention_score_1 = Activation('softmax')(attention_score_1)
        attention_score_2 = att_embbeding(attention_input_2)
        attention_score_2 = Activation('softmax')(attention_score_2)


    if INCLUDE_POS_EMB:
        CIP = WORD_EMBEDDING_DIM + POS_EMBEDDING_DIM * 2
        conv_input = merge([word_embeddings, 
            position_embeddings_1, 
            position_embeddings_2 ], 
            mode='concat', 
            concat_axis=2)
    else:
        CIP = WORD_EMBEDDING_DIM
        conv_input = word_embeddings


    def att_comp(tensor_list):
        import tensorflow as tf 
        return tf.mul(tensor_list[0],tensor_list[1]) 

    if INCLUDE_ATTENTION:
        ## composition layer
        att_merged = merge([attention_score_1, attention_score_2], 
                            mode="ave")
        

        conv_input = merge([att_merged, conv_input], 
                            mode=att_comp,
                            output_shape=(n, CIP))


    ## activation function according to paper
    g = ACTIVATION_FUNCTION

    #windows = [2,3,4,5]
    windows = [3]

    p_list = []

    for w in windows:
        conv = Reshape((1,n,CIP))(conv_input)
        conv = Conv2D(1000,1, w, 
            border_mode='valid',
            activation=g,
            W_constraint=maxnorm(L2_NORM_MAX), 
            bias=True,
            init='glorot_normal')(conv)
        #conv = GlobalMaxPooling2D()(conv)
        p_list.append(conv)

    import ipdb
    ipdb.sset_trace()

    pooling_concat = p_list[0]
    #pooling_concat = conv_input
    #pooling_concat = merge(p_list, mode="concat", concat_axis=1)

    pooling_concat = K.transpose(pooling_concat)
    pooling_concat = Flatten()(pooling_concat)
    #pooling_concat = Dropout(DROPOUT_RATE)(pooling_concat)

    final_layer = Dense(NO_OF_CLASSES, activation='softmax')(pooling_concat)
        #,activation='softmax', 
        #W_constraint=maxnorm(L2_NORM_MAX))(pooling_concat)
        
    
    input_arr = [sequence_input]
    
    if INCLUDE_POS_EMB:
        input_arr.append(position_input_1)
        input_arr.append(position_input_2)

    if INCLUDE_ATTENTION:
        input_arr.append(attention_input_1)
        input_arr.append(attention_input_2)

    model = Model(input=input_arr, output=[final_layer])
    
    if optimizer == 'ada':
        opt = Adadelta(epsilon=1e-06)
    ### from the att matrix paper
    elif optimizer == 'sgd':
        opt = SGD(lr=0.03)

    model.compile(optimizer=opt, loss=loss, metrics=["accuracy", fbetascore])
    return model
