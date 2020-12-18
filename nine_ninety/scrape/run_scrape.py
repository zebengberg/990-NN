"""Run entire scrape pipeline."""

from nine_ninety.scrape.get_json_index import get_all_json_index
from nine_ninety.scrape.utils import get_index_years
from nine_ninety.scrape.scrape import run_year

get_all_json_index()
for year in get_index_years():
  run_year(year)
