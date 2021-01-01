"""Parse and save utilities."""

import os
import json
import pkgutil
import io
from lxml import etree
import pandas as pd
from nine_ninety.scrape.index import get_data_path, get_index_years


xp_bytes = pkgutil.get_data(__name__, '../xpath_headers.csv')
if xp_bytes is None:
  raise FileNotFoundError('Issue reading xpath_headers.csv')
XP = pd.read_csv(io.BytesIO(xp_bytes))
NEW_PATHS = dict(zip(list(XP['key']), list(XP['new_xpath'])))
OLD_PATHS = dict(zip(list(XP['key']), list(XP['old_xpath'])))
DATA_TYPES = dict(zip(list(XP['key']), list(XP['data_type'])))
OFFICERS = [f'officer_{i}' for i in range(5)]
DATA_TYPES.update(dict(zip(OFFICERS, ['int'] * 5)))


def empty_data():
  """Return dictionary of all 0s to use with 404 responses."""
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
    print('Could not find schema version for XML tree below.')
    print(root)
    raise e

  if version_year < 2013:
    paths = OLD_PATHS
  else:
    paths = NEW_PATHS

  for k, p in paths.items():

    try:
      # dealing with xpath issue for 2013
      if version_year == 2013 and k == 'organization_name':
        p = p[:-3]  # removing the Txt from the trail
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
  """Verify organization index data agrees with xml data."""
  if (e1 := data['ein']) != (e2 := org['EIN']):
    raise ValueError(f'EINs {e1} and {e2} do not match!')

  tax_period = org['TaxPeriod']
  year, month = int(tax_period[:4]), int(tax_period[4:])
  if month < 12:
    year -= 1
  if (t := int(data['tax_year'])) not in [year, year + 1]:
    print(f'Warning: Years {t} and {tax_period} do not match!')
    print(org)


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
  path = os.path.join(get_data_path(), str(year))
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
  csv_path = os.path.join(get_data_path(), str(year), str(year) + '.csv')
  index_path = os.path.join(get_data_path(), 'index',
                            'index_' + str(year) + '.json')

  df = pd.read_csv(csv_path)
  with open(index_path) as f:
    index = json.load(f)

  if len(df) != len(index):
    raise ValueError(f'len(df) = {len(df)} whereas len(index) = {len(index)}')

  print(f'Successfully fetched {len(df)} tax forms from {year}')


def clean_year(year):
  """Remove csv batches after bundling."""
  path = os.path.join(get_data_path(), str(year))
  batches = os.listdir(path)
  batches.sort()
  bundle = str(year) + '.csv'
  assert bundle in batches
  batches = [os.path.join(path, batch) for batch in batches if batch != bundle]
  for batch in batches:
    os.remove(batch)


def load_data(year=None):
  """Return DataFrame containing 990 data from specified year."""
  years = get_index_years()
  if year is not None:
    if not year in years:
      raise ValueError('Check the parameter year.')
    years = [year]

  dfs = []
  for y in years:
    path = os.path.join(get_data_path(), str(y), str(y) + '.csv')
    if os.path.exists(path):
      print('Loading data from', y)
      df = pd.read_csv(path)
      dfs.append(df)
    else:
      raise FileNotFoundError(f'Could not find CSV data from {y}.')
  df = pd.concat(dfs)
  print(f'Loaded data from {len(df)} individual tax forms')

  return fix_mistakes(df)


def fix_mistakes(df):
  """Correct obvious mistakes in 990 data."""
  # converting nan missions to empty strings
  print('Converting empty missions to strings ....')
  df['mission'] = df['mission'].fillna('')

  # dealing with 404 errors arrising from outdated index files in early years
  print('Removing empty items ....')
  df = df[df['ein'] != 0]  # to deal with 404s from early years
  mask = df['organization_name'] == '0'
  if s := mask.sum():
    print(f'Found {s} organizations without a name!')
  df = df[~mask]  # removing unnamed

  # some organizations have repeated tax forms in a given year
  # only keep most recently submitted form
  print('Keeping at most one tax form per organization per year ....')
  df = df.groupby(['ein', 'tax_year']).last().reset_index()
  print('Sorting by tax year ....')
  df = df.sort_values('tax_year')
  return df.reset_index(drop=True)


def get_boolean_keys():
  """Get key names corresponding to boolean values."""
  filt = XP['data_type'] == 'bool'
  return list(XP[filt]['key'])
