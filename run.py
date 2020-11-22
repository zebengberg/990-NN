"""Run entire scrape pipeline."""

from get_json_index import get_all_json_index
from utils import get_index_years, bundle_year, confirm_year, clean_year
from fetch import run_year

get_all_json_index()
for year in get_index_years():
  run_year(year)
  bundle_year(year)
  confirm_year(year)
  clean_year(year)
