"""Make asynchronous requests with aiohttp."""

import os
import json
import time
import asyncio
import aiohttp
from tqdm import trange
from utils import parse, save_as_csv, verify, empty_data
from utils import bundle_year, confirm_year, clean_year


SESSIONS_PER_BATCH = 20
SESSION_SIZE = 50


async def fetch(org, session):
  """Request 990 XML data from org."""

  async with session.get(org['URL'], ssl=False) as response:
    if response.status == 404:
      return empty_data()

    if response.status != 200:
      print(f'Received response with status: {response.status}')
      raise aiohttp.ClientConnectionError

    xml = await response.read()
    data = parse(xml)
    verify(data, org)
    return data


async def run_session(orgs):
  """Run a single asynchronous request session."""
  try:
    tasks = []
    async with aiohttp.ClientSession() as session:
      for org in orgs:
        task = asyncio.ensure_future(fetch(org, session))
        tasks.append(task)
      responses = asyncio.gather(*tasks)
      await responses
    return responses
  except aiohttp.ClientConnectionError as e:
    print(e)
    time.sleep(10)
    run_session(orgs)


def run_batch(orgs, csv_path):
  """Fetch and save data from orgs."""
  batch = []
  for j in trange(SESSIONS_PER_BATCH):
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    orgs_slice = orgs[j * SESSION_SIZE: (j + 1) * SESSION_SIZE]
    task = asyncio.ensure_future(run_session(orgs_slice))
    loop.run_until_complete(task)
    if task.result() is not None:
      result = task.result().result()
    else:
      run_batch(orgs, csv_path)
    batch += result
  save_as_csv(batch, csv_path)


def run_year(year):
  """Fetch and save data from a specific year."""
  path = os.path.join('data', str(year))
  if not os.path.exists(path):
    os.mkdir(path)
  batches = os.listdir(path)
  batches.sort()
  with open(f'data/index/index_{year}.json') as f:
    index = json.load(f)
  total_n_batch = len(index) // (SESSION_SIZE * SESSIONS_PER_BATCH)
  assert len(str(total_n_batch)) < 4  # for left padding below

  if batches:
    if batches == [str(year) + '.csv']:
      print(f'Already have data for {year}')
      return None
    highest_n_batch = int(batches[-1].split('.')[0])
    assert len(str(highest_n_batch)) < 4
  else:
    highest_n_batch = -1

  for n_batch in range(highest_n_batch + 1, total_n_batch + 1):
    print(f'Running batch {n_batch} / {total_n_batch} in year {year}')
    csv_name = f'{n_batch:03}' + '.csv'
    csv_path = os.path.join(path, csv_name)
    batch_size = SESSION_SIZE * SESSIONS_PER_BATCH
    orgs = index[n_batch * batch_size: (n_batch + 1) * batch_size]
    run_batch(orgs, csv_path)
  print(f'Fetched all data from {year}!')
  bundle_year(year)
  confirm_year(year)
  clean_year(year)
  return None
