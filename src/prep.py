import numpy as np
import math

import logging

from functions import debug_print, debug_print_dict
from keras.preprocessing.text import Tokenizer
from keras.preprocessing.sequence import pad_sequences

class Preprocessor():

    def __init__(self, 
        texts, 
        Y,
        debug=False, 
        clipping_value=18,
        markup=False):
        self.tokenizer = Tokenizer()
        self.tokenizer.fit_on_texts(texts)
        self.texts = texts
        self.nom1_idx = self.tokenizer.word_index['e1']
        self.nom2_idx = self.tokenizer.word_index['e2']
        self.clipping = True
        self.debug = debug
        self.markup = markup
        self.Y = Y
        self.n_values = []
        self.clipping_value = clipping_value

    def sequence(self, texts):
        return self.tokenizer.texts_to_sequences(texts)

    def find_n(self, nominal_relations):
        if not self.clipping: 
            n_values = [ x[1] - x[0] for x in nominal_relations]
            if not self.markup:
                n_values = [n-2 for n in n_values]
            self.n = max(n_values)
        else:
            self.n = self.clipping_value

    def nominal_positions_and_clip(self, sequences):
        nominal_heads = []
        nominal_relations = []
        self.idx_to_keep = []
        for seq_idx, seq in enumerate(sequences):
            nom1_head = -1
            nom2_head = -1
            nom2_tail = -1
            for token_idx, token in enumerate(seq):
                if token == self.nom1_idx and nom1_head == -1:
                    nom1_head = token_idx + 1
                if token == self.nom2_idx:
                    if nom2_head == -1:
                        nom2_head = token_idx + 1
                    else:
                        nom2_tail = token_idx - 1
            ### clipping experiment
            if self.clipping and nom2_head - nom1_head + 1 <= self.clipping_value:
                self.idx_to_keep.append(seq_idx)

            nominal_relations.append((nom1_head, nom2_tail))
            nominal_heads.append([nom1_head, nom2_head])
        if self.clipping:
            self.Y = np.asarray(self.Y)[self.idx_to_keep]
            nominal_relations_clipped = np.asarray(nominal_relations)[self.idx_to_keep]
            nominal_heads_clipped =  np.asarray(nominal_heads)[self.idx_to_keep] 
            sequences_clipped = np.asarray(sequences)[self.idx_to_keep]
            return nominal_relations_clipped, nominal_heads_clipped, sequences_clipped 

        else:
            return nominal_relations, nominal_heads, sequences

    def word_idx(self):
        if self.markup:
            return self.tokenizer.word_index
        else:
            return {k: v-2 for k, v in self.tokenizer.word_index.iteritems()
            if v != self.nom1_idx and v != self.nom2_idx  } 


    def pad_and_heads(self, sequences, nominal_relations, nominal_heads):
        padded_sequence = []
        for seq_idx, seq in enumerate(sequences):
            head, tail = nominal_relations[seq_idx]
            h = head
            t = tail + 1
            n_rest = max(0, self.n - (t - h))
            switch = True
            while n_rest > 0 and (h > 0 or t < len(seq)):
                if switch and h > 0:
                    h -= 1
                    n_rest -= 1
                elif t < len(seq):
                    t += 1
                    n_rest -= 1
                switch = not switch

            padded_sequence.append( seq[h:t])
            old_head1, old_head2 = nominal_heads[seq_idx]
            nominal_heads[seq_idx] = old_head1 - h, old_head2 - h
        return pad_sequences(padded_sequence, maxlen=self.n)

    def nominal_positions(self, X_pad, X_nom_heads):
        nominal_positions1 = []
        nominal_positions2 = []
        for seq_idx, seq in enumerate(X_pad):
            tmp_nom_pos1 = []
            tmp_nom_pos2 = []
            for token_idx, token in enumerate(seq):
                head1, head2 = X_nom_heads[seq_idx]
                nom_pos1 = (head1 - token_idx) + self.n - 1 
                nom_pos2 = (head2 - token_idx) + self.n - 1
                tmp_nom_pos1.append(nom_pos1)
                tmp_nom_pos2.append(nom_pos2)
            nominal_positions1.append(tmp_nom_pos1)
            nominal_positions2.append(tmp_nom_pos2)
        return np.array(nominal_positions1), np.array(nominal_positions2)

    def reverse_sequence(self, seqs):
        inv_map = {v: k for k, v in self.tokenizer.word_index.iteritems()}
        return [[inv_map[s] for s in xs if s != 0] for xs in seqs]        

    def clean_markups(self,seqs):
        rev_seq = self.reverse_sequence(seqs)
        new_idx = self.word_idx()
        cleaned_seq = []
        for seq in rev_seq:
            cleaned_seq.append([new_idx[tok] for tok in seq if 
                tok != 'e1' and tok != 'e2'])
        return cleaned_seq

    def make_att_dict(self, seqs, nominals):
        attentions_idx = {}
        att_list_1 = []
        att_list_2 = []

        def add_to_dict_and_list(pair, att_list, att_dict):
            if pair not in att_dict: 
                att_dict[pair] = len(att_dict) + 1 
            att_list.append(att_dict[pair])

        for seq_idx, seq in enumerate(seqs):
            att_sub_list_1 = []
            att_sub_list_2 = []
            for tok_idx, tok in enumerate(seq):
                nominal_idx_1, nominal_idx_2 = nominals[seq_idx]
                pair_1 = min(tok, nominal_idx_1), max(tok, nominal_idx_1)
                pair_2 = min(tok, nominal_idx_2), max(tok, nominal_idx_2)

                add_to_dict_and_list(pair_1, att_sub_list_1, attentions_idx)
                add_to_dict_and_list(pair_2, att_sub_list_2, attentions_idx)
            att_list_1.append(att_sub_list_1)
            att_list_2.append(att_sub_list_2)


        return attentions_idx, np.asarray(att_list_1), np.asarray(att_list_2)

    def preprocess(self, X):

        sequences = self.sequence(X)
        
        nominal_relations, nominal_heads, sequences_clip = self.nominal_positions_and_clip(sequences)

        self.find_n(nominal_relations)
        print "Maximum nominal distance: " , self.n

        if not self.markup:
            ## shift nominal relations to the left due to markups being removed
            nominal_relations = [(x[0]-1, x[1]-3) for x in nominal_relations]
            nominal_heads = [(x[0]-1, x[1]-3) for x in nominal_heads]
            sequences_clip = self.clean_markups(sequences_clip)

        padded_sequences = self.pad_and_heads(sequences_clip, nominal_relations, nominal_heads)
        nominal_positions1, nominal_positions2 = self.nominal_positions(padded_sequences, nominal_heads)         
        
        logging.info("Attention dictionarys created with nominal HEADS only")

        att_idx, att_list_1, att_list_2 = self.make_att_dict(padded_sequences, nominal_heads)

        debug_print(att_idx, "Attention Indices")
        debug_print(att_list_1, "Attention pair list 1")
        debug_print(att_list_2, "Attention pair list 2")

        
        return (padded_sequences, 
            nominal_positions1, nominal_positions2, 
            att_idx, att_list_1, att_list_2,
            self.Y)


