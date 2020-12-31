"""Predict number of employees based on other tax data."""

import numpy as np
import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error as mse
from sklearn.metrics import mean_absolute_error as mae
from sklearn.metrics import mean_absolute_percentage_error as mape
from tensorflow.keras.layers.experimental import preprocessing
from nine_ninety.models.preprocess import read_scaled_df


def build_df(min_n_employees=2, max_n_employees=7):
  """Read and filter DataFrame."""
  df = read_scaled_df()

  # there are many organizations (~ 35%) without any employees
  filt = df['n_employees'].between(min_n_employees, max_n_employees)
  print(f'Removing {sum(~filt)} organizations.')
  print(f'Keeping {sum(filt)} organizations.')
  df = df[filt]
  df = df.reset_index(drop=True)

  # only keep one row per organization to avoid "cheating"
  # the snippet below is much more performant than df = grouped.sample()
  grouped = df.groupby('ein')
  keeps = [np.random.choice(arr) for arr in grouped.indices.values()]
  df = df.iloc[keeps]
  df = df.reset_index(drop=True)

  # disregard several other columns in addition to already dropped ein
  df = df.drop(columns=['tax_year', 'organization_name'])
  return df


def split_data(df):
  """Split DataFrame into inputs and outputs."""
  df_train, df_test = train_test_split(df, test_size=0.2)

  data = {}

  data['y_train'] = df_train.pop('n_employees')
  data['x_train_text'] = df_train.pop('mission').astype(str)
  data['x_train_numeric'] = df_train

  data['y_test'] = df_test.pop('n_employees')
  data['x_test_text'] = df_test.pop('mission').astype(str)
  data['x_test_numeric'] = df_test

  return data


def build_model(x_train_text, x_train_numeric, **kwargs):
  """Build TF model."""
  print('Considering TF model on both numeric and text data...')

  max_features = 5000
  sequence_length = 100

  encoder = preprocessing.TextVectorization(max_tokens=max_features,
                                            output_sequence_length=sequence_length)
  encoder.adapt(x_train_text.values)

  normalizer = preprocessing.Normalization()
  normalizer.adapt(x_train_numeric.values)

  text_input = tf.keras.Input(shape=(None,), name='text', dtype='string')
  embedded = encoder(text_input)
  embedded = layers.Embedding(input_dim=max_features, output_dim=128)(embedded)
  if kwargs['lstm']:
    embedded = layers.LSTM(128)(embedded)
  else:
    embedded = layers.GlobalAveragePooling1D()(embedded)

  numeric_shape = x_train_numeric.shape[1:]
  numeric_input = tf.keras.Input(shape=numeric_shape, name='numeric')
  normalized = normalizer(numeric_input)

  x = layers.concatenate([embedded, normalized])
  x = layers.Dropout(0.3)(x)
  x = layers.Dense(256, activation='relu')(x)
  x = layers.Dropout(0.3)(x)
  output = layers.Dense(1)(x)

  model = tf.keras.Model(inputs=[text_input, numeric_input], outputs=output)
  model.compile(optimizer='adam', loss='mse', metrics=['mape', 'mae'])
  return model


def run_model(model, data):
  """Train and test TF model."""

  epochs = 10
  batch_size = 32
  model.fit({'text': data['x_train_text'],
             'numeric': data['x_train_numeric']},
            data['y_train'],
            validation_split=0.2,
            batch_size=batch_size,
            epochs=epochs)

  model.evaluate({'text': data['x_test_text'],
                  'numeric': data['x_test_numeric']},
                 data['y_test'],
                 verbose=1)


def linear_model(data):
  """Build, train, and test sklearn linear model."""
  print('Considering sklearn linear model on numeric data ...')
  m = LinearRegression()
  m.fit(data['x_train_numeric'], data['y_train'])
  print('r^2 score:', m.score(data['x_test_numeric'], data['y_test']))
  y_pred = m.predict(data['x_test_numeric'])
  print('MSE:', mse(data['y_test'], y_pred))
  print('MAE:', mae(data['y_test'], y_pred))
  print('MAPE:', 100 * mape(data['y_test'], y_pred))


if __name__ == '__main__':
  df = build_df()
  data = split_data(df)
  linear_model(data)

  model = build_model(**data, lstm=False)
  run_model(model, data)
  model = build_model(**data, lstm=True)
  run_model(model, data)
