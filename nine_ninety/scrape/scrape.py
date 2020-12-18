"""Make asynchronous requests with aiohttp."""

import os
import json
import time
import asyncio
import aiohttp
from tqdm import trange
from nine_ninety.scrape.utils import parse, save_as_csv, verify, empty_data
from nine_ninety.scrape.utils import bundle_year, confirm_year, clean_year


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
  tasks = []
  async with aiohttp.ClientSession() as session:
    for org in orgs:
      task = asyncio.ensure_future(fetch(org, session))
      tasks.append(task)
    responses = asyncio.gather(*tasks)
    await responses
  return responses


def run_batch(orgs, csv_path):
  """Fetch and save data from orgs."""

  try:
    batch = []
    for j in trange(SESSIONS_PER_BATCH):
      loop = asyncio.get_event_loop()
      asyncio.set_event_loop(loop)
      orgs_slice = orgs[j * SESSION_SIZE: (j + 1) * SESSION_SIZE]
      task = asyncio.ensure_future(run_session(orgs_slice))
      loop.run_until_complete(task)
      result = task.result().result()
      batch += result
    assert len(batch) == len(orgs)
    save_as_csv(batch, csv_path)

  except aiohttp.ClientError as e:
    print(e)
    time.sleep(10)
    run_batch(orgs, csv_path)


def determine_missing_batches(year, total_n_batch):
  """Determine the batch files currently missing."""

  path = os.path.join('data', str(year))
  if not os.path.exists(path):
    os.mkdir(path)
  batches = os.listdir(path)

  batches = [int(b.split('.')[0]) for b in batches]
  if year in batches:
    print(f'Seem to already have data for {year}')
    return []

  return [i for i in range(total_n_batch + 1) if i not in batches]


def run_year(year):
  """Fetch and save data from a specific year."""
  with open(f'data/index/index_{year}.json') as f:
    index = json.load(f)
  total_n_batch = len(index) // (SESSION_SIZE * SESSIONS_PER_BATCH)
  assert len(str(total_n_batch)) < 4  # for left padding below

  missing_batches = determine_missing_batches(year, total_n_batch)
  for n_batch in missing_batches:
    print(f'Running batch {n_batch} / {total_n_batch} in year {year}')
    csv_name = f'{n_batch:03}' + '.csv'
    csv_path = os.path.join('data', str(year), csv_name)
    batch_size = SESSION_SIZE * SESSIONS_PER_BATCH
    orgs = index[n_batch * batch_size: (n_batch + 1) * batch_size]
    run_batch(orgs, csv_path)
  if missing_batches:
    print(f'Fetched all data from {year}!')
    bundle_year(year)
    confirm_year(year)
    clean_year(year)
