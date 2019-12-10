import os
import pandas as pd
import numpy as np
from ast import literal_eval
from parse_data import Parser
from tqdm import tqdm
tqdm.pandas()

print('Loading data from file.')
df = pd.read_csv('data.csv')

print('Starting to drop and clean data from the 990 DataFrame.')
# There is a value of in the year column that is mistyped.
# It reads 210805 and should read 201805.
df.loc[1596658, 'year'] = 201805

# Stripping away the month part of the year.
df['year'] = np.int64(df['year'] / 100)

# Some organizations have repeated tax forms in a given year.
# Only keep most recently submitted copy.
print('Keeping one tax form per organization per year.')
df = df.groupby(['ein', 'year']).last().reset_index()

# Some entries in DataFrame are NaN. We need to fix this.
# Replacing NaN mission entries with an empty string.
df['mission'] = df['mission'].fillna('')


# To train the NN, we input an entire year's worth of data in order to predict
# the total revenue of the following year. We get the total revenue for the next
# year (the NN target) and remove rows not containing this information. If we
# want to include additional years of data as NN input, this is the place to do
# so.
def get_next_year_total_revenue(row):
    """Get next year total revenue and collect rows without it."""

    total_revenue = df[(df['ein'] == row['ein'])
                       & (df['year'] == row['year'] + 1)]['total_revenue']

    if total_revenue.empty:
        return np.nan
    else:
        return total_revenue.values[0]


print('Getting the total revenue of the next year. See progress bar.')
df['next_year_total_revenue'] = df.progress_apply(get_next_year_total_revenue,
                                                  axis=1)
print('Removing rows without next year total revenue.')
df.dropna(inplace=True)


# Now we get rid of some outliers and stupid mistakes.
total_keys = ['total_revenue', 'total_expense', 'total_assets',
              'total_liabilities', 'current_endowment']
rows_to_remove = []


def get_outliers(grp):
    """Removing outliers that cannot be readily fixed by hand."""

    # No values should be negative.
    mask = (grp < 0).any(axis=1)

    # Finding values that are too extreme.
    for key in total_keys:
        # If grp median is small but max is huge, possible typo, sure outlier.
        if grp[key].median() < 10 ** 6:
            mask = mask | (grp[key] > 10 ** 7)
        else:
            mask = mask | (grp[key] > 10 * grp[key].median())

    for item in mask[mask].index:
        rows_to_remove.append(item)


print('Finding some outliers. See progress bar.')
df.groupby('ein')[total_keys].progress_apply(get_outliers)
print('Removing found outliers.')
df.drop(rows_to_remove, inplace=True)


print('Done removing bad rows. Now starting to populate processed DataFrame.')
# The processed DataFrame "pdf" to be loaded with data from df.
# Both DataFrames will have the same index set.
pdf = pd.DataFrame(index=df.index)
pdf['next_year_total_revenue'] = df['next_year_total_revenue']
# Some scaling applied; to obtain original, take exp.
pdf['next_year_total_revenue'] = np.log(pdf['next_year_total_revenue']\
                                 .mask(pdf['next_year_total_revenue'] <= 0))\
                                 .fillna(0)

# Encoding the year as a one-hot.
for year in range(2010, 2020):
    pdf['year_is_' + str(year)] = np.where(df['year'] == year, 1, 0)


def clean_count_of(grp):
    """Clean up various df numeric columns."""

    # If grp median is small but max is huge, possible typo.
    if grp.median() < 10:
        mask = grp > 1000
    else:
        mask = grp > 10 * grp.median()

    # Replace all these bad masked entries with the group median.
    grp[mask] = grp.median()
    return grp


for col in ['board', 'employees', 'volunteers']:
    print('Cleaning count of ' + col + '.')
    pdf[col] = df.groupby('ein')[col].progress_apply(clean_count_of)
    # Normalize by taking log if value nonzero, and setting to -1 if zero value.
    # This makes data appear somewhat more uniformly distributed.
    pdf[col] = np.log(pdf[col].mask(pdf[col] <= 0)).fillna(-1)
    # Rescaling to condense the range to the interval [-1, 1]
    pdf[col] /= pdf[col].max()
    # Setting groups without any people back to -1. The purpose of this it to
    # create somewhat of a gap in the data here -- the NN might appreciate it.
    pdf.loc[pdf[col] < 0, col] = -1


# Grabbing some useful dictionaries already implemented in the Parser class.
parser = Parser()
category_dict = parser.category_dict
type_dict = parser.type_dict

# Now getting boolean-style values from organization, such as "has_hospital".
# These are all encoded as one-hot data within the DataFrame.
print('Adding boolean information.')
keys = [key for key, value in type_dict.items() if value == 'bool']
for key in keys:
    pdf[key] = df[key]


# Most of the tax data values are a numeric subset of a larger category.
# We turn these into ratios by dividing by the category total.
# No information is "lost", and the NN might have more success with ratios.
# Ignoring endowment data at present.
categories_and_totals = {'revenue': 'total_revenue',
                         'expense': 'total_expense',
                         'assets': 'total_assets',
                         'liabilities': 'total_liabilities'}

print('Cleaning numeric information.')
for category_name, total_key in categories_and_totals.items():
    keys = [key for key, value in category_dict.items()
            if value == category_name]
    for key in keys:
        pdf.loc[df[total_key] == 0, key] = 0
        pdf.loc[df[total_key] != 0, key] = df[key] / df[total_key]
        # Sometimes numbers can be negative. Mostly due to human mistake.
        pdf[key] = pdf[key].abs()
        pdf[key] = pdf[key].clip(upper=1)  # forcing some impossibilities out


# Now getting the total amounts. Clipping typos / outliers and scaling.
print('Cleaning total amounts.')
total_keys = ['total_revenue', 'total_expense', 'total_assets',
              'total_liabilities', 'current_endowment']
for col in total_keys:
    pdf[col] = np.log(df[col].mask(df[col] <= 0)).fillna(0)
    # Rescaling to condense the range to the interval [-1, 1]
    pdf[col] /= pdf[col].max()


def get_highest_comp(officers):
    officers = literal_eval(officers)
    highest = 0
    for officer in officers:
        if officer[1] > highest:
            highest = officer[1]
    return highest


print('Getting highest compensated officer salary. See progress bar.')
pdf['highest'] = df['officers'].progress_apply(get_highest_comp)
# Transforming the highest compensated into a proportion of total expenses.
pdf['highest'] = pdf['highest'] / df['total_expense']


# Finding year founded and mission data.
print('Starting to gather year-independent organization data.')
pdf['ein'] = df['ein']
g = df.groupby('ein')


def clean_founded(grp):
    """Clean up the year an organization was founded."""

    # Get the mode. If its between 1600 and 2020, set it as founded.
    mode = pd.Series.mode(grp['founded'])[0]
    if 1600 <= mode <= 2020:
        return mode
    else:  # Try setting max as founded.
        biggest = grp['founded'].max()
        if 1600 <= biggest <= 2020:
            return biggest
        else:  # Just set the founded to 2000.
            return 2000


print('Cleaning the year founded.')
founded_grouped = g.apply(clean_founded)
founded_grouped.name = 'founded'
# Broadcast this Grouped object back to full DataFrame.
pdf = pdf.join(founded_grouped, on='ein')
# Dropping the 'ein' column. The NN does not need this.
pdf.drop('ein', axis=1, inplace=True)
# We normalize. Now values are between [-4.0, 0.2], and mostly close to 0.
pdf['founded'] = (pdf['founded'] - 2000) / 100


# Pulling out keywords from mission statement.
# The file "mission_keywords.txt" was built using code from "examples" notebook,
# then modified by hand to take common root of nearly identical words.

with open('mission_keywords.txt') as f:
    mission_keywords = f.read().splitlines()

# Empty list to be appended with one-hot dicts. This approach is much faster
# than modifying pdf inplace for every row.
list_of_one_hot_dicts = []


def convert_mission_to_one_hot(row):
    """Encode mission keywords with one-hot vector."""

    # Encode key words in the mission statement as one-hot vectors.
    one_hot_dict = {word: 0 for word in mission_keywords}
    one_hot_dict['index'] = row.name

    mission = row['mission']
    mission = mission.lower()  # convert to lowercase
    # Strip out anything that's not a letter or space.
    stripped = ''.join(e for e in mission if e.isalnum())
    for word in mission_keywords:
        if word in stripped:
            one_hot_dict[word] = 1  # not counting multiplicity

    list_of_one_hot_dicts.append(one_hot_dict)


print('Searching mission statement for keywords.')
df.progress_apply(convert_mission_to_one_hot, axis=1)

print('Adding discovered keywords to the DataFrame.')
mission_df = pd.DataFrame(list_of_one_hot_dicts)
mission_df.set_index('index', inplace=True)
pdf = pd.concat([pdf, mission_df], axis=1)

print('Done with pre-processing data.')
print('Saving processed DataFrame to file.')
if not os.path.exists('NN/'):
    os.mkdir('NN/')
pdf.to_csv('NN/processed_data.csv', index=False)
