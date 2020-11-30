"""Explore words found in missions."""

import os
import string
from tqdm import tqdm
import nltk
import pandas as pd
import matplotlib.pyplot as plt
from utils import load_data, get_index_years

TABLE = str.maketrans('', '', string.punctuation)
STOP_WORDS = set(nltk.corpus.stopwords.words('english'))
STEMMER = nltk.stem.snowball.SnowballStemmer('english')
LEMMATIZER = nltk.stem.WordNetLemmatizer()
FIGSIZE = (16, 8)


def tokenize(mission):
  """Extract list of stemmed words from a single mission string."""
  tokens = nltk.tokenize.word_tokenize(mission)
  tokens = [w.lower() for w in tokens]
  tokens = [w.translate(TABLE) for w in tokens]
  tokens = [w for w in tokens if w.isalpha()]
  tokens = [w for w in tokens if not w in STOP_WORDS]
  tokens = [LEMMATIZER.lemmatize(w) for w in tokens]

  def full_stem(word):
    """Apply stem until arriving at a fixed point."""
    stemmed = STEMMER.stem(word)
    while stemmed != word:
      word = stemmed
      stemmed = STEMMER.stem(word)
    return word

  tokens = [full_stem(w) for w in tokens]
  return [w for w in tokens if len(w) > 1]


def build_freq_dists():
  """Build FreqDist for each year and store them in dictionary."""
  fd_dict = {}
  for year in get_index_years():
    print(f'Analyzing {year}.')
    df = load_data(year)
    fd = nltk.FreqDist()
    for m in tqdm(df['mission']):
      fd.update(tokenize(m))
    fd_dict[year] = fd
  return fd_dict


def total_freq_dist(fd_dict):
  """Build FreqDist by combining all years."""
  total_fd = nltk.FreqDist()
  for fd in fd_dict.values():
    total_fd.update(fd)
  return total_fd


def determine_common_words(total_fd, n_words):
  """Determine most common words used in missions."""
  keys = total_fd.most_common(n_words)
  return [k[0] for k in keys]


def build_freq_df(fd_dict, keys):
  """Build DataFrame containing word use data by year."""
  rows = []
  for year, fd in fd_dict.items():
    row = {'tax_year': year, 'total': fd.N()}
    for k in keys:
      assert k not in row  # do not mix up keys
      row[k] = fd[k]
    rows.append(row)
  df = pd.DataFrame(rows)
  return df.set_index('tax_year', drop=True)


def build_area_plots(freq_df):
  """Build area plots showing increase and decrease of specific word use."""
  ratios = {}
  for k in freq_df.columns:
    year0, year1 = freq_df.index[0], freq_df.index[-1]
    # considering first three years and last three years
    start = freq_df.loc[year0: year0 + 2, k].sum()
    end = freq_df.loc[year1 - 2: year1, k].sum()
    # converting totals to proportions
    start /= freq_df.loc[year0: year0 + 2, 'total'].sum()
    end /= freq_df.loc[year1 - 2: year1, 'total'].sum()

    ratios[k] = start / end

  ratios = sorted(ratios.items(), key=lambda item: item[1])
  gaining_keys = [item[0] for item in ratios[:20]]
  losing_keys = [item[0] for item in ratios[-20:]]

  # plotting proportions
  freq_df[gaining_keys].multiply(
      1 / freq_df['total'], axis=0).plot.area(figsize=FIGSIZE)
  plt.legend(loc='left')
  plt.show()

  freq_df[losing_keys].multiply(
      1 / freq_df['total'], axis=0).plot.area(figsize=FIGSIZE)
  plt.legend(loc='right')
  plt.show()


def build_histograms():
  """Build histograms displaying length of missions over time."""
  years = get_index_years()
  fig, axs = plt.subplots(len(years), figsize=(16, 12))

  for i, year in enumerate(tqdm(years)):
    df = load_data(year)
    l = df['mission'].apply(len)
    l.hist(bins=100, ax=axs[i])
    axs[i].set(xlabel='Number of characters in mission', title=year)

  fig.tight_layout()
  plt.show()


def build_plots():
  """Build plots."""
  fd_dict = build_freq_dists()
  total_fd = total_freq_dist(fd_dict)
  keys = determine_common_words(total_fd, 1000)
  freq_df = build_freq_df(fd_dict, keys)
  build_area_plots(freq_df)

  plt.figure(figsize=FIGSIZE)
  total_fd.plot(50)
  plt.show()

  build_histograms()


def mission_to_one_hot(mission, keys):
  """Convert mission to one-hot vector according to keys."""
  words = set(tokenize(mission))
  common = set(keys) & words
  d = {k: 0 for k in keys}
  for k in common:
    d[k] = 1
  return list(d.values())


def write_keywords(n_words):
  """Write common mission keywords to disk."""
  fd_dict = build_freq_dists()
  total_fd = total_freq_dist(fd_dict)
  keys = determine_common_words(total_fd, n_words)
  with open('keywords.txt', 'w') as f:
    for k in keys:
      f.write(k + '\n')


def load_keywords():
  """Read common mission keywords from disk."""
  if not os.path.exists('keywords.txt'):
    raise FileNotFoundError(
        'Cannot find existing keywords.txt file. Run write_common_words().')
  with open('keywords.txt') as f:
    keywords = f.read().split()
  print(f'Reading {len(keywords)} keywords from file.')
  return keywords


if __name__ == '__main__':
  write_keywords(10000)
  # build_plots()
