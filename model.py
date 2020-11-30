"""Modeling with 990 data."""

import tensorflow as tf
import numpy as np
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt
from tqdm import tqdm
from utils import get_boolean_keys, load_grouped_data
from mission import mission_to_one_hot, load_keywords

full_df = load_grouped_data()
keys = load_keywords()
keys = keys[:3000]


category_keys = ['is_lobbying', 'is_school']
mask = full_df[category_keys].sum(axis=1) == 1
df = full_df[mask]

print('Number of organizations by category:')
print(df[category_keys].sum())


X = [mission_to_one_hot(m, keys) for m in tqdm(df['mission'])]
X = np.array(X, dtype=np.int)
y = df[category_keys]
y = y.values
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)


def build_model(input_shape, output_shape):
  """Build Sequential classifier."""
  model = tf.keras.Sequential([
      tf.keras.layers.Input(shape=input_shape),
      tf.keras.layers.Dense(200, activation='relu'),
      tf.keras.layers.Dropout(0.5),
      tf.keras.layers.Dense(200, activation='relu'),
      tf.keras.layers.Dropout(0.5),
      tf.keras.layers.Dense(output_shape)
  ])
  model.compile(optimizer='adam', loss='categorical_crossentropy',
                metrics=['accuracy'])
  print(model.summary())
  return model


model = build_model(X.shape[-1], y.shape[-1])
print('Training:')
model.fit(X_train, y_train, batch_size=32, epochs=5)
print('Evaluation results:')
model.evaluate(X_test, y_test, verbose=1)


# prob_model = tf.keras.Sequential([model, tf.keras.layers.Softmax()])
# preds = prob_model.predict(X_test)


def build_correlation_heatmap():
  """Build heatmap to show correlation between boolean keys."""

  boolean_keys = get_boolean_keys()
  data = []
  for k1 in boolean_keys:
    row = []
    for k2 in boolean_keys:
      mask = (df[k1] == 1) & (df[k2] == 1)
      row.append(df[mask].shape[0] / (df[k1].sum() + df[k2].sum()))
    data.append(row)

  data = np.array(data)
  _, ax = plt.subplots(figsize=(12, 12))
  ax.imshow(data)
  ax.set_xticks(range(len(boolean_keys)))
  ax.set_yticks(range(len(boolean_keys)))
  ax.set_xticklabels(boolean_keys, rotation='vertical')
  ax.set_yticklabels(boolean_keys)
  plt.show()
