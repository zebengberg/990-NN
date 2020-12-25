"""Clean, normalize, and engineering new features from scraped data."""

import os
import numpy as np
import pandas as pd
from nine_ninety.scrape.utils import load_data, XP
from tqdm import tqdm
tqdm.pandas()


def scale_founded_year(df):
  """Use organization group to fix and scale founded years."""
  print('Scaling year founded ....')
  grouped = df.copy().groupby('ein')

  def apply_to_group(group):
    mask = group['founded_year'].between(1600, 2030)
    m = group['founded_year'][mask].mode().mean()
    if pd.isnull(m):
      m = 2000  # a default value
    # normalize so values are between [-4.0, 0.2], and mostly close to 0.
    m = (m - 2000) / 100
    group['founded_year'] = m
    return group

  return grouped.progress_apply(apply_to_group)


def include_ratios(df):
  """Include numeric data as ratio of category total."""
  print('Building ratios ....')

  df_copy = df.copy()
  ratio_keys = []
  for category in ['revenue', 'expense', 'assets', 'liabilities']:
    filt = XP['category'] == category
    ratio_keys += [(key, 'total_' + category) for key in XP[filt]['key']]

  for key1, key2 in tqdm(ratio_keys):
    df_copy[key1 + '_ratio'] = (df_copy[key1] / df_copy[key2]).clip(-1, 1)

  for key in ['minus1_endowment', 'minus2_endowment',
              'minus3_endowment', 'minus4_endowment']:
    df_copy[key + '_ratio'] = (df_copy[key] /
                               df['current_endowment']).clip(-1, 1)

  for key in ['officer_1', 'officer_2', 'officer_3', 'officer_4']:
    df_copy[key + '_ratio'] = (df_copy[key] / df['officer_0']).clip(-1, 1)

  df_copy = df_copy.fillna(0.0)
  return df_copy


def log_scale(df):
  """Apply log scaling and normalization to numeric columns."""
  print('Log scaling numeric data ....')

  df_copy = df.copy()
  for key in tqdm(get_numeric_keys(False)):
    s = np.sign(df[key])
    df_copy[key] = s * np.log(df[key] * s + 1)
  return df_copy


def get_numeric_keys(include_floats=True):
  """Determine the keys of numeric categories."""
  keys = []
  for _, row in XP.iterrows():
    key = row['key']
    if row.loc['data_type'] == 'int':
      # masking tax_year and founded_year
      if '_year' not in key:
        keys.append(key)
    elif include_floats and row.loc['data_type'] == 'float':
      keys.append(key)
  return keys


def scale_df():
  """Apply scaling and normalization to loaded DataFrame."""
  df = load_data()
  df = scale_founded_year(df)
  # df = include_ratios(df)
  df = log_scale(df)
  return df


if __name__ == '__main__':
  df = scale_df()
  path = os.path.join(os.path.dirname(__file__), 'scaled_data.csv')
  df.to_csv(path, index=False)
