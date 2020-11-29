"""Parse and save utilities."""

import os
import json
from lxml import etree
import pandas as pd

xp = pd.read_csv('xpath_headers.csv')
NEW_PATHS = dict(zip(list(xp['key']), list(xp['new_xpath'])))
OLD_PATHS = dict(zip(list(xp['key']), list(xp['old_xpath'])))
DATA_TYPES = dict(zip(list(xp['key']), list(xp['data_type'])))
OFFICERS = [f'officer_{i}' for i in range(5)]
DATA_TYPES.update(dict(zip(OFFICERS, ['int'] * 5)))


def empty_data():
  """Return an dictionary of all 0s."""
  keys = list(NEW_PATHS.keys()) + OFFICERS
  return dict(zip(keys, [0] * len(keys)))


def parse(xml):
  """Grab values from xml based on xpath_headers."""
  data = {}
  root = etree.XML(xml)

  # the year of the schema version
  try:
    version_year = int(root.attrib['returnVersion'].split('v')[0])
  except KeyError as e:
    print(root)
    raise e

  if version_year < 2013:
    paths = OLD_PATHS
  else:
    paths = NEW_PATHS

  for k, p in paths.items():
    try:
      data[k] = root.find(p, namespaces=root.nsmap).text
    except AttributeError:
      data[k] = 0  # can easily be cast to int, float, str, bool
  salaries = parse_officers(root, version_year)
  data.update(salaries)
  return data


def parse_officers(root, version_year):
  """Grab officer information from the xml tree."""

  p = 'ReturnData/IRS990/Form990PartVIISectionA'
  if version_year < 2013:
    p += '/ReportableCompFromOrganization'
  else:
    p += 'Grp/ReportableCompFromOrgAmt'

  salaries = root.findall(p, namespaces=root.nsmap)
  salaries = [int(s.text) for s in salaries]
  salaries.sort(reverse=True)
  salaries = salaries[:len(OFFICERS)]
  # skimming off top salaries
  n_pad = len(OFFICERS) - len(salaries)
  if n_pad > 0:
    salaries += [0] * n_pad  # padding rest with 0
  return dict(zip(OFFICERS, salaries))


def verify(data, org):
  """Verify organization index EIN agrees with xml EIN."""
  if (e1 := data['ein']) != (e2 := org['EIN']):
    raise ValueError(f'EINs {e1} and {e2} do not match!')


def save_as_csv(data, filepath):
  """Cast data to correct type and save as csv."""
  df = pd.DataFrame(data)
  types = {'int': int, 'str': str, 'float': float,
           'bool': lambda x: 1 if x in ('1', 'true') else 0}
  for k in df.columns:
    type_as_string = DATA_TYPES[k]
    type_literal = types[type_as_string]
    if type_as_string == 'bool':
      df[k] = df[k].apply(type_literal)
    else:
      df[k] = df[k].astype(type_literal)

  df.to_csv(filepath, index=False)


def bundle_year(year):
  """Bundle all batched csv from year into a single csv."""
  print('Bundling csv files into single file')
  path = os.path.join('data', str(year))
  batches = os.listdir(path)
  batches.sort()
  batches = [os.path.join(path, batch) for batch in batches]
  batch_dfs = [pd.read_csv(batch) for batch in batches]
  df = pd.concat(batch_dfs)
  csv_path = os.path.join(path, str(year) + '.csv')
  print(f'Saving new csv as {csv_path}')
  df.to_csv(csv_path, index=False)


def confirm_year(year):
  """Confirm index and bundled csv have the same number of entries."""
  csv_path = os.path.join('data', str(year), str(year) + '.csv')
  index_path = os.path.join('data', 'index', 'index_' + str(year) + '.json')

  df = pd.read_csv(csv_path)
  with open(index_path) as f:
    index = json.load(f)

  if len(df) != len(index):
    raise ValueError(f'len(df) = {len(df)} whereas len(index) = {len(index)}')

  print(f'Successfully fetched {len(df)} tax forms from {year}')


def clean_year(year):
  """Remove csv batches after bundling."""
  path = os.path.join('data', str(year))
  batches = os.listdir(path)
  batches.sort()
  bundle = str(year) + '.csv'
  assert bundle in batches
  batches = [os.path.join(path, batch) for batch in batches if batch != bundle]
  for batch in batches:
    os.remove(batch)


def get_index_years():
  """Return list of years corresponding to cached index files."""
  index_path = os.path.join('data', 'index')
  years = os.listdir(index_path)
  years.sort()
  return [int(y.split('_')[1][:4]) for y in years]


def load_data(year=None):
  """Return DataFrame containing all data."""
  years = get_index_years()
  if year is not None:
    if not year in years:
      raise ValueError('Check the parameter year.')
    years = [year]

  dfs = []
  del year
  for year in years:
    path = os.path.join('old_data2', str(year), str(year) + '.csv')
    if os.path.exists(path):
      df = pd.read_csv(path)
      dfs.append(df)
  df = pd.concat(dfs)
  df['mission'] = df['mission'].fillna('')  # converting nan missions to ''
  df = df[df['ein'] != 0]  # to deal with 404s from early years
  return df.reset_index(drop=True)


def load_grouped_data():
  """Load data indexed by EIN."""
  df = load_data()
  return df.groupby(by='ein').last()


def get_boolean_keys():
  """Get key names corresponding to boolean values."""
  xpath_headers = pd.read_csv('xpath_headers.csv')
  filt = xpath_headers['data_type'] == 'bool'
  return list(xpath_headers[filt]['key'])
