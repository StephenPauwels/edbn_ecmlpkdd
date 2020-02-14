from keras.layers import Layer
from keras import backend as K

import tensorflow as tf
import sys

REPR_DIM = 100
TIME_STEP = 5

# https://keras.io/layers/writing-your-own-keras-layers/
class Modulator(Layer):

    def __init__(self, attr_idx, num_attrs, **kwargs):
        self.attr_idx = attr_idx
        self.num_attrs = num_attrs  # Number of extra attributes used in the modulator (other than the event)

        super(Modulator, self).__init__(**kwargs)

    def build(self, input_shape):
        self.W = self.add_weight(name="Modulator_W", shape=(self.num_attrs+1, (self.num_attrs + 2) * REPR_DIM), initializer="uniform", trainable=True)
        # self.W = tf.Variable([[1.0,1,1,1,1,1], [1,1,1,1,1,1]])
        self.b = self.add_weight(name="Modulator_b", shape=(self.num_attrs + 1, 1), initializer="zeros", trainable=True)

        #super(Modulator, self).build(input_shape)
        self.built = True

    def call(self, x):
        # split input to different representation vectors
        representations = []
        for i in range(self.num_attrs + 1):
            representations.append(x[:,((i + 1) * TIME_STEP) - 1,:])

        # Calculate z-vector
        tmp = []
        for elem_product in range(self.num_attrs + 1):
            if elem_product != self.attr_idx:
                tmp.append(tf.multiply(representations[self.attr_idx],representations[elem_product], name="Modulator_repr_mult_" + str(elem_product)))
        for attr_idx in range(self.num_attrs + 1):
            tmp.append(representations[attr_idx])
        z = tf.concat(tmp, axis=1, name="Modulator_concatz")
        # Calculate b-vectors
        b = tf.sigmoid(tf.matmul(self.W,tf.transpose(z), name="Modulator_matmulb") + self.b, name="Modulator_sigmoid")

        print(b)

        # Use b-vectors to output
        tmp = tf.transpose(tf.multiply(b[0,:], tf.transpose(x[:,(self.attr_idx * TIME_STEP):((self.attr_idx+1) * TIME_STEP),:])), name="Modulator_mult_0")
        for i in range(1, self.num_attrs + 1):
             tmp = tmp + tf.transpose(tf.multiply(b[i,:], tf.transpose(x[:,(i * TIME_STEP):((i+1) * TIME_STEP),:])), name="Modulator_mult_" + str(i))

        # output = tf.scalar_mul(b[0,0], representations[0])
        # for i in range(1, len(representations)):
        #     output = output + tf.scalar_mul(b[0,i], representations[i])
        return tmp

    def compute_output_shape(self, input_shape):
        return (None, TIME_STEP, REPR_DIM)

    def get_config(self):
        config = {'attr_idx': self.attr_idx, 'num_attrs': self.num_attrs}
        base_config = super(Modulator, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


if __name__ == "__main__":
    from keras.layers import Input, Concatenate
    from keras.models import Model
    import numpy as np
    import tensorflow as tf

    act_input = Input(shape=(TIME_STEP,REPR_DIM))
    role_input = Input(shape=(TIME_STEP,REPR_DIM))

    concat = Concatenate(axis=1)([act_input, role_input])

    mod1 = Modulator(attr_idx=0, num_attrs=1)

    out = mod1(concat)
    model = Model([act_input, role_input], out)

    model.summary()

    input_act = [[[1,2], [3,4], [5,6]], [[100,200], [300,400], [500,600]]]
    input_act = np.array(input_act)
    input_role = [[[11,12], [13,14], [15,16]], [[11,12], [13,14], [15,16]]]
    input_role = np.array(input_role)

    print(model.predict([input_act, input_role]))

    print(mod1.W)
    print(mod1.b)