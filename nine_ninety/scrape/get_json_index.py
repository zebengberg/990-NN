"""Get index json files from AWS."""

import os
import json
import requests
from nine_ninety.scrape.utils import get_data_path


INDEX_PATH = os.path.join(get_data_path(), 'index')


def get_json_index(year):
  """Download 990 index file from AWS and save to disk."""

  if not os.path.exists(get_data_path()):
    os.mkdir(get_data_path())
  if not os.path.exists(INDEX_PATH):
    os.mkdir(INDEX_PATH)

  local_path = os.path.join(INDEX_PATH, f'index_{year}.json')
  if os.path.exists(local_path):
    print(f'Index file for {year} already saved.')
    return None

  url = f'https://s3.amazonaws.com/irs-form-990/index_{year}.json'
  print('Requesting data from AWS ...')
  r = requests.get(url)
  if r.ok:
    data = r.json()  # data is a dict with a single key
    data = data['Filings' + str(year)]  # data is a list of dicts
    # ignoring 990EZs and 990PFs
    data = [d for d in data if d['FormType'] == '990']
    print('Writing data to file.')
    with open(local_path, 'w') as f:
      json.dump(data, f)
    return None

  raise FileNotFoundError(f'Index file for {year} not found on AWS.')


def get_all_json_index():
  """Get index files for all available years."""

  year = 2011
  while True:
    try:
      print(f'Getting index file for {year}')
      get_json_index(year)
      year += 1
    except FileNotFoundError:
      print(f'AWS does not yet have index file for {year}!')
      break
