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


# Now we get rid of some outliers and stupid mistakes.
print('Finding some outliers. See progress bar.')
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


df.groupby('ein')[total_keys].progress_apply(get_outliers)
print('Removing found outliers.')
df.drop(rows_to_remove, inplace=True)


# To train the neural network, we input two years worth of data to predict the
# total revenue of the following year. We need three consecutive years of data
# for each neural network input. We find such items in the df, and remove the
# rest.
print('Finding consecutive year-organization data. See progress bar.')
rows_to_remove = []


def group_contains_three_consecutive(grp):
    """Determine if group contains three consecutive years ending in year."""

    mask = pd.Series(False, index=grp.index)
    for year in range(2012, 2020):
        if (grp == year).any() & (grp == year - 1).any() & (grp == year - 2).any():
            mask = mask | (grp == year) | (grp == year - 1) | (grp == year - 2)

    for item in mask[mask].index:
        rows_to_remove.append(item)


df.groupby('ein')['year'].progress_apply(group_contains_three_consecutive)
print('Removing nonconsecutive year-organization data.')
df.drop(rows_to_remove, inplace=True)


print('Done deleting bad rows. Now starting to populate processed DataFrame.')
# The processed DataFrame "pdf" to be loaded with data from df.
# Both DataFrames will have the same index set.
pdf = pd.DataFrame(index=df.index)
pdf['year'] = df['year']
pdf['ein'] = df['ein']


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


print('Getting highest compensated officer salary. See progress bar.')


def get_highest_comp(officers):
    officers = literal_eval(officers)
    highest = 0
    for officer in officers:
        if officer[1] > highest:
            highest = officer[1]
    return highest


pdf['highest'] = df['officers'].progress_apply(get_highest_comp)
# Transforming the highest compensated into a proportion of total expenses.
pdf['highest'] = pdf['highest'] / df['total_expense']


print('Saving processed DataFrame to file.')
if not os.path.exists('NN/'):
    os.mkdir('NN/')
pdf.to_csv('NN/year_to_year_data.csv', index=False)


# Finding year founded and mission data.
print('Starting to gather year-independent organization data.')
g = df.groupby('ein')
founded_df = pd.DataFrame()  # indexed by ein


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
founded_df['founded'] = g.progress_apply(clean_founded)
# We normalize. Now values are between [-4.0, 0.2], and mostly close to 0.
founded_df['founded'] = (founded_df['founded'] - 2000) / 100

# Pulling out keywords from mission statement.
# The file "mission_keywords.txt" was built using code from "examples" notebook,
# then modified by hand to take common root of nearly identical words.
with open('mission_keywords.txt') as f:
    mission_keywords = f.read().splitlines()

# Replacing column with NaN as mission with an empty string.
df['mission'] = df['mission'].fillna('')

print('Parsing mission statement for keywords.')
list_of_one_hot_dicts = []


def make_mission_one_hot(grp):
    """Encode mission as one-hot dict."""

    # Longest string is organization's mission.
    i = grp['mission'].str.len().idxmax()
    mission = grp['mission'][i]

    # Encode key words in the mission statement as one-hot vectors.
    one_hot_dict = {word: 0 for word in mission_keywords}
    one_hot_dict['ein'] = grp['ein'].iloc[0]

    mission = mission.lower()  # convert to lowercase
    # Strip out anything that's not a letter or space.
    stripped = ''.join(e for e in mission if e.isalnum())
    for word in mission_keywords:
        if word in stripped:
            one_hot_dict[word] = 1  # not counting multiplicity

    list_of_one_hot_dicts.append(one_hot_dict)


g.progress_apply(make_mission_one_hot)
print('Adding discovered keywords to the DataFrame.')
mission_df = pd.DataFrame(list_of_one_hot_dicts)  # indexed by ein
mission_df.set_index('ein', inplace=True)

odf = pd.concat([founded_df, mission_df], axis=1)  # indexed by ein
print('Saving organization DataFrame to file.')
odf.to_csv('NN/organization_data.csv', index=True)
