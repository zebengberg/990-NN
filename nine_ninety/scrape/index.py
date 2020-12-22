"""Get index json files from AWS."""

import os
import json
import requests


def get_data_path():
  """Return the absolute path of the `data` directory holding 990 data."""
  cur_dir = os.path.dirname(__file__)
  return os.path.join(cur_dir, '..', 'data')


def get_index_path(year):
  """Return path for index file from year."""
  if not os.path.exists(get_data_path()):
    os.mkdir(get_data_path())

  index_dir = os.path.join(get_data_path(), 'index')
  if not os.path.exists(index_dir):
    os.mkdir(index_dir)

  return os.path.join(index_dir, f'index_{year}.json')


def get_json_index(year, overwrite=False):
  """Download 990 index file from AWS and save to disk."""

  if os.path.exists(path := get_index_path(year)):
    print(f'Index file for {year} already saved.')
    with open(path) as f:
      data = json.load(f)
      print(f'File contains data for {len(data)} organizations.')
    if overwrite:
      print('Overwriting ...')
  else:
    overwrite = True

  if overwrite:
    url = f'https://s3.amazonaws.com/irs-form-990/index_{year}.json'
    print('Requesting data from AWS ...')
    r = requests.get(url)
    if r.ok:
      data = r.json()  # data is a dict with a single key
      data = data['Filings' + str(year)]  # data is a list of dicts
      # ignoring 990EZs and 990PFs
      data = [d for d in data if d['FormType'] == '990']
      print('Writing data to file.')
      print(f'File contains data for {len(data)} organizations.')
      with open(path, 'w') as f:
        json.dump(data, f)
    else:
      raise FileNotFoundError(f'Index file for {year} not found on AWS.')


def get_all_json_index(overwrite=False):
  """Get index files for all available years."""

  year = 2011
  while True:
    try:
      print(f'Getting index file for {year}')
      get_json_index(year, overwrite)
      print('')
      year += 1
    except FileNotFoundError:
      print(f'AWS does not yet have index file for {year}!')
      break


def get_index_years():
  """Return list of years corresponding to cached index files."""

  index_path = os.path.join(get_data_path(), 'index')
  years = os.listdir(index_path)
  years.sort()
  return [int(y.split('_')[1][:4]) for y in years]


if __name__ == '__main__':
  get_all_json_index(True)
