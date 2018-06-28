#!/usr/bin/env python3
import keras
from keras import backend as K
from tensorflow.python.client import timeline
import tensorflow as tf
import numpy as np
from DataGenerator import DataGenerator
max_len = 10
model_to_save = None
profile = False
run_metadata = None
#Function not used anymore, replaced with DataGenerator.py
def get_train_test_data(train_file,test_file,one_hot=False):
    with open(train_file) as train_f:
        training_lines = [x.lower() for x in train_f.readlines()]
    with open(test_file) as test_f:
        test_lines = [x.lower() for x in test_f.readlines()]
    training_lines_filtered = [line for line in training_lines if len(line) <= max_len]
    test_lines_filtered = [line for line in test_lines if len(line) <= max_len]
    training_lines_filtered = [line + ('\n' * (max_len - len(line))) for line in training_lines_filtered]
    test_lines_filtered = [line + ('\n' * (max_len - len(line))) for line in test_lines_filtered]

    del training_lines
    del test_lines
    global vocab
    all_lines = training_lines_filtered + test_lines_filtered
    counter = 0
    for pass_str in all_lines:
        for char in pass_str:
            if char not in vocab:
                vocab[char] = counter
                counter += 1
    if one_hot:
        train_X = np.zeros(shape=(len(training_lines_filtered), max_len, len(vocab)),dtype=np.int)
        test_X = np.zeros(shape=(len(test_lines_filtered), max_len, len(vocab)),dtype=np.int)
        train_Y = np.zeros(shape=(len(training_lines_filtered), max_len, len(vocab)))
        test_Y = np.zeros(shape=(len(test_lines_filtered), max_len, len(vocab)))
    else:
        train_X = np.zeros(shape=(len(training_lines_filtered), max_len),dtype=np.int)
        test_X = np.zeros(shape=(len(test_lines_filtered), max_len),dtype=np.int)
        train_Y = np.zeros(shape=(len(training_lines_filtered), max_len))
        test_Y = np.zeros(shape=(len(test_lines_filtered), max_len))

    for i, line in enumerate(training_lines_filtered):
        shifted_line = line[1:] + '\n'
        for j, char in enumerate(line):
            if one_hot:
                train_X[i, j, vocab[char]] = 1
                #pass
            else:
                train_X[i, j] = vocab[char]
        for j, char in enumerate(shifted_line):
            if one_hot:
                train_Y[i, j, vocab[char]] = 1
            else:
                train_Y[i, j] = vocab[char]
    for i, line in enumerate(test_lines_filtered):
        shifted_line = line[1:] + '\n'
        for j, char in enumerate(line):
            if one_hot:
                test_X[i, j, vocab[char]] = 1
                #pass
            else:
                test_X[i, j] = vocab[char]
        for j, char in enumerate(shifted_line):
            if one_hot:
                test_Y[i, j, vocab[char]] = 1
            else:
                test_Y[i, j] = vocab[char]

    return [train_X, train_Y, test_X, test_Y]


def tokenize_vocab(trainfile, testfile=None):
    if testfile is not None:
        files = [trainfile] + [testfile]
    else:
        files = [trainfile]
    counter = 0
    local_vocab = {}
    for file in files:
        with open(file, "r") as f:
            for line in f:
                for char in line:
                    if char not in local_vocab:
                        local_vocab[char] = counter
                        counter += 1
    return local_vocab


# def one_hot_to_int(x):
#     w = K.constant(np.stack([np.arange(len(vocab))]*(tf.shape(x)[0])))
#     print(tf.Print(x, [tf.shape(x)]))
#     print(tf.Print(w, [tf.shape(w)]))
#     op = K.batch_dot(x, w, axes=[1, 1])
#     return op

def one_hot_to_int(x, len_vocab):
    print(x)

    v = tf.constant(np.arange(len_vocab),dtype=np.int8)
    #v1 = tf.reshape(len_vocab, 1)
    print(v)
    y = tf.matmul(x, tf.transpose(v))
    print(y)
    return y
def get_model(len_vocab, profile):

    with tf.device('/cpu:0'):
        model = keras.models.Sequential()
        model.add(keras.layers.Embedding(len_vocab, 8, input_length=max_len))
        model.add(keras.layers.LSTM(2048, return_sequences=True))
        model.add(keras.layers.Dropout(0.4))
        model.add(keras.layers.LSTM(512, return_sequences=True))
        model.add(keras.layers.TimeDistributed(keras.layers.Dense(len_vocab, activation="softmax")))
        #model.add(keras.layers.TimeDistributed(keras.layers.Lambda(
        # one_hot_to_int, arguments={"len_vocab": len_vocab})))
        global model_to_save
        model_to_save = model

    model = keras.utils.multi_gpu_model(model, gpus=4)
    if profile:
        global run_metadata
        run_options = tf.RunOptions(trace_level=tf.RunOptions.FULL_TRACE)
        run_metadata = tf.RunMetadata()
        model.compile(loss='MSE', optimizer='Adam', options=run_options, run_metadata=run_metadata)
        model.compile(loss="categorical_crossentropy", optimizer=keras.optimizers.Adam(),
                      metrics=["accuracy"], options=run_options, run_metadata=run_metadata)
    else:
        model.compile(loss="categorical_crossentropy", optimizer=keras.optimizers.Adam(),
                      metrics=["accuracy"], )
    print(model.summary())
    return model


class CheckpointCallback(keras.callbacks.Callback):

    def __init__(self, model, save_path):
        self.model_to_save = model
        self.save_path = save_path

    def on_epoch_end(self, epoch, logs=None):
        self.model_to_save.save("{}.{}".format(self.save_path, epoch))

if __name__ == "__main__":

    trainfile = "data/pwd_100M_train.txt"
    validationfile = "data/pwd_100M_test.txt"
    batch_size = 512

    training_generator = DataGenerator(trainfile, batch_size, max_len)
    validation_generator = DataGenerator(validationfile, batch_size, max_len)
    vocab = training_generator.get_vocab()
    inv_vocab = {v: k for k, v in vocab.items()}
    print("Vocab length = {}".format(len(vocab)))
    print(vocab)
    embeddingsMetadata = {'Embedding_0': 'metadata.tsv'}

    model = get_model(len(vocab), profile)
    global model_to_save
    saver = CheckpointCallback(model_to_save, "./runs/model.h5")
    tensorboard = keras.callbacks.TensorBoard(log_dir='./runs/new_lstm_test')
    model.fit_generator(generator=training_generator, validation_data=training_generator,
                        epochs=3, use_multiprocessing=True, workers=6, callbacks=[tensorboard, saver])
    if profile:
        trace = timeline.Timeline(step_stats=run_metadata.step_stats)
        with open('./runs/new_lstm_test/timeline.ctf.json', 'w') as f:
            f.write(trace.generate_chrome_trace_format())
    op = model.predict_generator(generator=validation_generator)
    max_idx = np.argmax(op, axis=2)
    preds = []
    for wrd in max_idx:
        a = ""
        for idx in wrd:
            a += inv_vocab[idx]
        preds.append(a)
    print(preds[:100])