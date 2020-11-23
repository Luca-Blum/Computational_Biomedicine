# HK, 2020 - 11 - 21
import keras
from keras.layers import Dense
from keras.layers import Dropout
from keras.models import Sequential

""" 
taken from https://github.com/bio-ontology-research-group/phenomenet-vp/blob/master/dev/nn_final_training.py
"""


class Phenomenet:
    def __init__(self, input_dim: int):
        self.input_dim = input_dim

    def get_phenomenet(self):
        model = Sequential()
        model.add(Dense(67, input_dim=self.input_dim, kernel_initializer='uniform', activation='relu'))
        model.add(Dropout(0.2))
        model.add(Dense(32, kernel_initializer='uniform', activation='relu'))
        model.add(Dropout(0.2))
        model.add(Dense(256, kernel_initializer='uniform', activation='relu'))
        model.add(Dropout(0.2))
        model.add(Dense(1, kernel_initializer='uniform', activation='sigmoid'))

        adam = keras.optimizers.Adam(lr=0.001)
        model.compile(loss='binary_crossentropy', optimizer=adam, metrics=['accuracy', 'AUC'])

        return model
