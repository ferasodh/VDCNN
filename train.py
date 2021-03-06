'''
Training Script for VDCNN Text
'''
import keras
from keras.models import Sequential, load_model, model_from_json
from keras.optimizers import SGD
from keras.callbacks import ModelCheckpoint, TensorBoard
from keras import losses
import keras.backend as K
import numpy as np
from absl import flags
import h5py
import math
import sys
import datetime

from CyclicLR import CyclicLR
from metrics import Metrics
from vdcnn import *
from data_helper import *
import custom_callbacks
from sklearn.utils import class_weight
# Parameters settings
# Data loading params
tf.flags.DEFINE_string("database_path", "data/", "Path for the dataset to be used.")

# Model Hyperparameters
tf.flags.DEFINE_integer("sequence_length", 140, "Sequence Max Length (default: 1024)")
tf.flags.DEFINE_string("pool_type", "max", "Types of downsampling methods, use either three of max (maxpool), k_max (k-maxpool) or conv (linear) (default: 'max')")
tf.flags.DEFINE_integer("depth", 9, "Depth for VDCNN, use either 9, 17, 29 or 47 (default: 9)")
tf.flags.DEFINE_boolean("shortcut", True, "Use optional shortcut (default: False)")
tf.flags.DEFINE_boolean("sorted", False, "Sort during k-max pooling (default: False)")
tf.flags.DEFINE_boolean("use_bias", True, "Use bias for all conv1d layers (default: False)")

# Training parameters
flags.DEFINE_integer("batch_size", 64, "Batch Size (default: 64)")
flags.DEFINE_integer("num_epochs", 200, "Number of training epochs (default: 100)")
flags.DEFINE_integer("evaluate_every", 100, "Evaluate model on test set after this many steps (default: 100)")

FLAGS = flags.FLAGS
FLAGS(sys.argv)
print("\nParameters:")
print("-"*20)
for attr, value in sorted(FLAGS.__flags.items()):
    print("{}={}".format(attr, value.value))
print("")

data_helper = data_helper(sequence_max_length=FLAGS.sequence_length)

def preprocess():
    # Data Preparation
    # ==================================================

    # Load data
    print("Loading data...")
    train_data, train_label, test_data, test_label = data_helper.load_dataset(FLAGS.database_path)
    print("Loading data succees...")

    return train_data, train_label, test_data, test_label

def train(x_train, y_train, x_test, y_test):
    # Init Keras Model here

    # class_weights = class_weight.compute_class_weight('balanced',
    #                                                   np.unique(y_train),
    #                                                   y_train)
    class_weight_dict = {0: 0.7,1: 1.6}

    # class_weight_dict = dict(enumerate(class_weights))

    model = VDCNN(num_classes=y_train.shape[1],#
                  depth=FLAGS.depth, 
                  sequence_length=FLAGS.sequence_length, 
                  shortcut=FLAGS.shortcut,
                  pool_type=FLAGS.pool_type, 
                  sorted=FLAGS.sorted, 
                  use_bias=FLAGS.use_bias)

    model.compile(optimizer=SGD(lr=0.01, momentum=0.9), loss='binary_crossentropy', metrics=['accuracy'])

    model_json = model.to_json()
    with open("vdcnn_model.json","w") as json_file:
        json_file.write(model_json)                    # Save model architecture
    time_str = datetime.datetime.now().isoformat()
    print("{}: Model saved as json.".format(time_str))
    print("")

    # Trainer
    # Tensorboard and extra callback to support steps history
    tensorboard = TensorBoard(log_dir='./logs', histogram_freq=50, batch_size=FLAGS.batch_size, write_graph=True, write_images=True)
    checkpointer = ModelCheckpoint(filepath="./checkpoints/vdcnn_weights_val_acc_{val_acc:.4f}.h5", period=1,
                                   verbose=1, save_best_only=True, mode='max', monitor='val_acc')
    loss_history = custom_callbacks.loss_history(model, tensorboard)
    evaluate_step = custom_callbacks.evaluate_step(model, checkpointer, tensorboard, FLAGS.evaluate_every, FLAGS.batch_size, x_test, y_test)

    clr = CyclicLR(base_lr=0.004, max_lr=0.01, step_size=2000., mode='triangular',
                   gamma=0.99994)
    validation_data=(x_test, y_test)
    metrics = Metrics(validation_data)

    # Fit model
    model.fit(x_train, y_train, batch_size=FLAGS.batch_size, epochs=FLAGS.num_epochs, validation_data=(x_test, y_test), #class_weight=class_weight_dict ,
              verbose=1, callbacks=[checkpointer, tensorboard, loss_history, evaluate_step, metrics])
    print('-'*30)
    time_str = datetime.datetime.now().isoformat()
    print("{}: Done training.".format(time_str))
    K.clear_session()
    print('-'*30)
    print()

if __name__=='__main__':
    x_train, y_train, x_test, y_test = preprocess()
    train(x_train, y_train, x_test, y_test)