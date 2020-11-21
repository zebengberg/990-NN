"""Make asynchronous requests with aiohttp."""

import os
import json
import math
import asyncio
import aiohttp
from tqdm import trange
from utils import clean_year, parse, save_as_csv, verify, bundle_year, confirm_year


SESSIONS_PER_BATCH = 20
SESSION_SIZE = 50


async def fetch(org, session):
  """Request 990 XML data from org."""
  async with session.get(org['URL'], ssl=False) as response:
    try:
      assert response.status == 200
      xml = await response.read()
      data = parse(xml)
      verify(data, org)
      return data

    except Exception as e:
      print(e)
      print(org)
      raise e


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
  batch = []
  for _ in trange(SESSIONS_PER_BATCH):
    loop = asyncio.get_event_loop()
    asyncio.set_event_loop(loop)
    task = asyncio.ensure_future(run_session(orgs))
    loop.run_until_complete(task)
    result = task.result().result()
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
  total_n_batch = math.ceil(len(index) / (SESSION_SIZE * SESSIONS_PER_BATCH))
  assert len(str(total_n_batch)) < 4  # for left padding below

  if batches:
    highest_n_batch = int(batches[-1].split('.')[0])
    assert len(str(highest_n_batch)) < 4
  else:
    highest_n_batch = -1

  for n_batch in range(highest_n_batch + 1, total_n_batch + 1):
    print(f'Running batch {n_batch} / {total_n_batch} in year {year}')
    csv_name = f'{n_batch:03}' + '.csv'
    csv_path = os.path.join(path, csv_name)
    orgs = index[n_batch * SESSION_SIZE: (n_batch + 1) * SESSION_SIZE]
    run_batch(orgs, csv_path)
  print(f'Fetched all data from {year}!')
