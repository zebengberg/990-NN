"""Predict number of employees based on other tax data."""

import pandas as pd
import tensorflow as tf
from tensorflow.keras import layers
from sklearn.model_selection import train_test_split
from tensorflow.keras.layers.experimental.preprocessing import TextVectorization, Normalization

df = pd.read_csv('models/scaled_data.csv')
filt = df['n_employees'] > 0
df = df[filt]
df = df.reset_index(drop=True)
df = df.drop(columns=['ein', 'tax_year', 'organization_name'])


df_train, df_test = train_test_split(df, test_size=0.2)

y_train = df_train.pop('n_employees')
x_train_text = df_train.pop('mission').astype(str)
x_train_numeric = df_train

y_test = df_test.pop('n_employees')
x_test_text = df_test.pop('mission').astype(str)
x_test_numeric = df_test


max_features = 5000
sequence_length = 100

encoder = TextVectorization(max_tokens=max_features,
                            output_sequence_length=sequence_length)
encoder.adapt(x_train_text.values)

normalizer = Normalization()
normalizer.adapt(x_train_numeric.values)


text_input = tf.keras.Input(shape=(None,), name='text', dtype='string')
embedded = encoder(text_input)
embedded = layers.Embedding(input_dim=max_features, output_dim=128)(embedded)
embedded = layers.LSTM(128)(embedded)

numeric_shape = x_train_numeric.shape[1:]
numeric_input = tf.keras.Input(shape=numeric_shape, name='numeric')
normalized = normalizer(numeric_input)

x = layers.concatenate([embedded, normalized])
x = layers.Dropout(0.3)(x)
x = layers.Dense(256, activation='relu')(x)
x = layers.Dropout(0.3)(x)
output = layers.Dense(1)(x)

model = tf.keras.Model(inputs=[text_input, numeric_input], outputs=output)

model.compile(optimizer='adam', loss='mse', metrics=['accuracy'])

epochs = 10
batch_size = 64

model.fit({'text': x_train_text, 'numeric': x_train_numeric}, y_train,
          batch_size=batch_size, epochs=epochs)
