import os
import json
import requests
import datetime as dt
import time
from tqdm import tqdm


# See https://docs.opendata.aws/irs-990/readme.html for AWS 990 Filings instructions.

def get_index():
    """Download 990 index files from AWS server and return as list."""

    # Check to see if local index exists
    # If a local one does exist, we will use it.
    # To update local index in the future, delete local copy first.
    if os.path.isfile('index.json'):
        print('Reading index from local directory.')
        with open('index.json') as f:
            index = json.load(f)
        print('Reading success.')
        return index

    # AWS index starts with 2011 (earliest available year)
    year = 2011
    index = []
    while True:
        print('Getting {} json index from AWS.'.format(year))
        url = 'https://s3.amazonaws.com/irs-form-990/index_{}.json'.format(year)
        r = requests.get(url)
        if r.ok:
            data = r.json()
            # data has a single element of list-type which we extract 
            data = data['Filings' + str(year)]
            index += data
            year += 1
        else:  # index file does not exist on amazon server
            print('The {} index does not yet exist.'.format(year))
            break
    
    # Just restricting to 990s; ignoring 990EZs and 990PFs.
    index = [d for d in index if d['FormType'] == '990']

    # Write index list to a file
    with open('index.json', 'w') as f:
        print('Writing index to local directory.')
        json.dump(index, f)
        print('Writing success.')
    return index


def get_data(index):
    """Download and cache 990 xml files from AWS server."""

    # Making directory to hold data
    if not os.path.exists('data'):
        os.mkdir('data')

    # Keeping various relevant things.
    bad_orgs = []
    last_bad_write = dt.datetime.now()
    # Make a copy since we're iterating over original index and simultaneously
    # modifying updated_index below.
    updated_index = index.copy()
    data_size = 0

    # Downloading files from massive index.
    print('')
    print('Starting the massive data download.')
    t = tqdm(index)
    for org in t:
        url = org['URL']
        file_name = url.rsplit('/')[-1]
        file_address = 'data/{}'.format(file_name)
        is_xml_cached = os.path.isfile(file_address)

        if not is_xml_cached:
            success = False
            while not success:
                try:
                    r = requests.get(url, timeout=3)
                    success = True
                except requests.exceptions.RequestException as e:
                    print('Request failed.  Sleep then try again.')
                    print(str(e) + '\n')
                    time.sleep(5)
                else:
                    if r.ok:
                        with open(file_address, 'wb+') as f:
                            f.write(r.content)  # writing bytes, not a string
                        data_size += os.path.getsize(file_address)
                    # AWS gave 404 status
                    # response may be a nonexistent XML file mistakenly listed
                    else:
                        bad_orgs.append(org)

        # Update the index to remove the bad file from it if at least 5 minutes
        # have elapsed since last update.
        if bad_orgs and (dt.datetime.now() > last_bad_write +
                         dt.timedelta(minutes=5)):
            print('\nUpdate index to remove {} bad files.'.format(len(bad_orgs)))
            for bad_org in bad_orgs:
                updated_index.remove(bad_org)
            # This should create new index file.
            with open('index.json', 'w') as f:
                print('Rewriting index to local directory.')
                json.dump(updated_index, f)
            print('Writing success.\n')
            bad_orgs = []
            last_bad_write = dt.datetime.now()
            
        # Updating status bar
        t.set_description('{}GB // {} bad'.format(round(data_size / (10**9), 2),
                                                   len(bad_orgs)))


def check_data(index):
    """Check that all index files are stored locally."""

    print('\nChecking that all index files have been stored locally.')
    for org in tqdm(index):
        url = org['URL']
        file_name = url.rsplit('/')[-1]
        file_address = 'data/{}'.format(file_name)
        is_xml_cached = os.path.isfile(file_address)
        if not is_xml_cached:
            raise Exception('Cannot find file {}'.format(file_name))
    print('All index files are stored locally.')


def main():
    index = get_index()
    get_data(index)
    check_data(index)


# To run from command line
if __name__ == '__main__':
    main()
