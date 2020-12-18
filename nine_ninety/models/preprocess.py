"""Clean and preprocess data."""

from tqdm import tqdm
from nine_ninety.scrape.utils import load_data, XP


def preprocess():
  """Apply scaling and normalization to DataFrame."""
  #df = load_data()
  print(XP['key'])
  print(XP['data_type'])


def include_ratios(df):
  """Include numeric data as ratio of category total."""

  df_copy = df.copy()
  ratio_keys = []
  for category in ['revenue', 'expense', 'assets', 'liabilities']:
    filt = XP['category'] == category
    ratio_keys += [(key, 'total_' + category) for key in XP[filt]['key']]

  for key1, key2 in tqdm(ratio_keys):
    df_copy[key1] = df_copy[key1] / df_copy[key2]
  return df_copy


preprocess()
