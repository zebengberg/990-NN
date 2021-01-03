"""Predict an organization's class from its mission statement and detect
possible human errors on tax form."""


import tensorflow as tf
from tensorflow.keras.layers.experimental.preprocessing import TextVectorization
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_curve
import matplotlib.pyplot as plt
from nine_ninety.scrape.utils import get_boolean_keys, load_data


def prepare_data(full_df):
  """Prepare data to use in model."""
  grouped = full_df.groupby('ein')
  # for each EIN, take the tax year with the longest mission statement
  idx = grouped['mission'].agg(lambda x: x.str.len().idxmax())
  df = full_df.iloc[idx.values].set_index('ein')
  mask = df['mission'].str.len() < 40
  print(f'Removing {sum(mask)} organization with short missions.')
  df = df[~mask]
  return df[['mission'] + get_boolean_keys()]


def print_size(df, category):
  """Print the proportions of the two class sizes."""
  neg, pos = np.bincount(df[category])
  total = neg + pos
  neg = round(100 * neg / total, 2)
  pos = round(100 * pos / total, 2)
  print('Category:', category)
  print(f'Negatives: {neg}%\nPositives: {pos}%')


def split_data(df, category, over_sample=False):
  """Split data into train and test sets."""
  df_train, df_test = train_test_split(df, test_size=0.2)
  x_train = df_train['mission']
  y_train = df_train[category]
  x_test = df_test['mission']
  y_test = df_test[category]
  if over_sample:
    positives = y_train[y_train == 1].index
    n_extras = (y_train == 0).sum() - (y_train == 1).sum()
    idx = np.random.choice(positives, n_extras)
    extras = df_train.loc[idx]
    df_train = pd.concat([df_train, extras])
    df_train = df_train.sample(frac=1)
    x_train = df_train['mission']
    y_train = df_train[category]
  return x_train, y_train, x_test, y_test


def build_encoder(vocab_size, sequence_length, x_train):
  """Build and fit TensorFlow TextVectorization object."""
  encoder = TextVectorization(max_tokens=vocab_size,
                              output_sequence_length=sequence_length)
  encoder.adapt(x_train.values)
  return encoder


def sample_encoder_vocab(encoder, x_train):
  """Print several mission statements using encoder vocabulary."""
  vocab = np.array(encoder.get_vocabulary())
  missions = x_train.sample(10)
  for v in encoder(missions):
    encoded = [vocab[word] for word in v if word]
    print(' '.join(encoded) + '\n')


def determine_class_weights(y_train):
  """Determine imbalance in training set."""
  neg, pos = np.bincount(y_train)
  total = neg + pos
  output_bias = tf.keras.initializers.Constant(np.log([pos / neg]))
  class_weight = {0: total / neg, 1: total / pos}
  return output_bias, class_weight


def build_model(encoder, output_bias, embedding_dim):
  """Build Sequential model."""

  model = tf.keras.Sequential([
      encoder,
      tf.keras.layers.Embedding(
          input_dim=encoder.get_config()['max_tokens'] + 1,
          output_dim=embedding_dim),
      tf.keras.layers.GlobalAveragePooling1D(),
      # tf.keras.layers.Bidirectional(tf.keras.layers.LSTM(64)),
      tf.keras.layers.Dropout(0.2),
      tf.keras.layers.Dense(256, activation='relu'),
      tf.keras.layers.Dropout(0.2),
      tf.keras.layers.Dense(1, activation='sigmoid', bias_initializer=output_bias)])

  optimizer = tf.keras.optimizers.Adam(lr=1e-4)
  loss = 'binary_crossentropy'
  metrics = [tf.keras.metrics.TruePositives(name='tp'),
             tf.keras.metrics.FalsePositives(name='fp'),
             tf.keras.metrics.TrueNegatives(name='tn'),
             tf.keras.metrics.FalseNegatives(name='fn'),
             tf.keras.metrics.BinaryAccuracy(name='accuracy'),
             tf.keras.metrics.Precision(name='precision'),
             tf.keras.metrics.Recall(name='recall'),
             tf.keras.metrics.AUC(name='auc')]

  model.compile(optimizer=optimizer, loss=loss, metrics=metrics)
  return model


def plot_training_metrics(history, category, eval_results):
  """Plot training metrics."""

  plt.figure(figsize=(12, 8))
  for m in ['accuracy', 'precision', 'recall']:
    plt.plot(history.epoch, history.history[m], label=m + ' training data')
    plt.plot(history.epoch, history.history['val_' + m],
             label=m + ' validation data', linestyle='--')
    plt.axhline(y=eval_results[m], linestyle='-.',
                label=m + ' evaluation data')

  plt.title(f'Metrics for mission --> {category} classifier')
  plt.xlabel('epoch')
  plt.legend()
  plt.show()


def prob_human_error(full_df, df, ein, category):
  """Determine if there is a possible human error on the 990 form."""
  all_marked = full_df[full_df['ein'] == ein][category]
  specific_marked = df[category][ein]
  n_agree = (all_marked == specific_marked).sum()
  assert n_agree  # since specific_marked is included in all_marked
  return 1.0 - n_agree / len(all_marked)


def print_initial_rows(data_frame, full_df, df, category):
  for ein, row in data_frame.iterrows():
    print('ein:', ein)
    print('prediction:', row['pred'])
    print('actual:', row['actual'])
    print('probability human error:',
          prob_human_error(full_df, df, ein, category))
    print('mission:', row['mission'])
    print('')


def explore_model_misclassified(model, x_test, y_test, full_df, df, category):
  """Explore test data in which model incorrectly identifies class."""
  for i, class_name in enumerate(['POSITIVES', 'NEGATIVES']):
    d = pd.DataFrame(x_test[y_test == i])
    d['pred'] = model.predict(d)
    d['actual'] = i
    d = d.sort_values('pred', ascending=i)
    d = d.iloc[:10]
    print('TOP FALSE ' + class_name + '\n')
    print_initial_rows(d, full_df, df, category)


def explore_model_ambiguity(model, x_test, y_test, full_df, df, category):
  """Explore test data in which model cannot identify class."""
  y_pred = model.predict(x_test)
  d = pd.DataFrame(
      {'mission': x_test, 'actual': y_test, 'pred': y_pred.flatten()})
  d['ambiguity'] = (d['pred'] - 0.5).abs()
  d = d.sort_values('ambiguity').drop(columns=['ambiguity'])
  d = d.iloc[:20]
  print_initial_rows(d, full_df, df, category)


def plot_roc(actual, pred):
  """Plot ROC with sklearn roc_curve."""
  fp, tp, _ = roc_curve(actual, pred)
  plt.figure(figsize=(8, 8))
  plt.plot(fp, tp, linewidth=2)
  plt.xlabel('False positives')
  plt.ylabel('True positives')
  plt.grid(True)
  ax = plt.gca()
  ax.set_aspect('equal')
  plt.show()


if __name__ == '__main__':
  full_df = load_data()
  df = prepare_data(full_df)
  category = 'is_school'
  print_size(df, category)
  x_train, y_train, x_test, y_test = split_data(df, category, over_sample=True)

  print('Sampling from the encoder vocabulary ...')
  vocab_size = 3000
  sequence_length = 100
  encoder = build_encoder(vocab_size, sequence_length, x_train)
  sample_encoder_vocab(encoder, x_train)

  embedding_dim = 32
  batch_size = 64
  epochs = 5
  output_bias, class_weight = determine_class_weights(y_train)
  print('output bias:', output_bias)
  print('class weights:', class_weight)
  model = build_model(encoder, output_bias, embedding_dim)

  # tracing computation in order to print summary of network
  model(x_train.iloc[:batch_size])
  print(model.summary())
  print('Training ...')
  history = model.fit(x_train, y_train, batch_size=batch_size,
                      epochs=epochs, class_weight=class_weight,
                      validation_split=0.1)

  print('Evaluating ...')
  eval_results = model.evaluate(x_test, y_test, verbose=1)
  metric_keys = list(history.history.keys())
  metric_keys = metric_keys[:len(metric_keys) // 2]
  eval_results = dict(zip(metric_keys, eval_results))
  plot_training_metrics(history, category, eval_results)

  print('Exploring mistakes ...')
  explore_model_misclassified(model, x_test, y_test, full_df, df, category)
  explore_model_ambiguity(model, x_test, y_test, full_df, df, category)

  print('Plotting ROC ...')
  plot_roc(y_test, model.predict(x_test))
