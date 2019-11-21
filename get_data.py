import os
import json
import requests
import datetime as dt
import time
from tqdm import tqdm


# See https://docs.opendata.aws/irs-990/readme.html for
# AWS 990 Filings instructions.
class Data:
    """Get AWS XML 990 data."""

    def __init__(self):
        self.data_directory = 'data/'  # change to local path with data
        # Making directory to hold data
        if not os.path.exists(self.data_directory):
            os.mkdir(self.data_directory)

        # Check to see if local index exists.
        # If a local one does exist, we will use it.
        # To update local index in the future, just delete local copy first.
        self.index = None
        if os.path.isfile('index.json'):
            self.set_index_to_local()
        else:
            self.get_index()

    def set_index_to_local(self):
        """Set index as local index file."""

        print('Reading index from local directory.')
        with open('index.json') as f:
            self.index = json.load(f)
        print('Reading success.')

    def get_index(self):
        """Download 990 index files from AWS server and save to disk."""

        # AWS index starts with 2011 (earliest available year)
        year = 2011
        self.index = []
        while True:
            print('Getting {} json index from AWS.'.format(year))
            url = 'https://s3.amazonaws.com/irs-form-990/index_{}.json'\
                .format(year)
            r = requests.get(url)
            if r.ok:
                data = r.json()
                # data has a single element of list-type which we extract
                data = data['Filings' + str(year)]
                self.index += data
                year += 1
            else:  # index file does not exist on amazon server
                print('The {} index does not yet exist.'.format(year))
                break

        # Just restricting to 990s; ignoring 990EZs and 990PFs.
        self.index = [d for d in self.index if d['FormType'] == '990']

        # Write index list to a file
        with open('index.json', 'w') as f:
            print('Writing index to local directory.')
            json.dump(self.index, f)
            print('Writing success.')

    def get_data(self):
        """Download and cache 990 xml files from AWS server."""

        # Keeping various relevant things.
        bad_orgs = []
        last_bad_cleanup = dt.datetime.now()
        data_size = 0

        # Downloading files from massive index.
        print('')
        print('Starting the massive data download.')
        t = tqdm(self.index)
        for org in t:
            url = org['URL']
            file_name = url.rsplit('/')[-1]
            file_address = self.data_directory + file_name
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

            # Update the index to remove the bad file from it if at least 5
            # minutes have elapsed since last update.
            if bad_orgs and (dt.datetime.now() > last_bad_cleanup +
                             dt.timedelta(minutes=5)):
                self.cleanup_bads(bad_orgs)
                bad_orgs = []
                last_bad_cleanup = dt.datetime.now()

            # Updating status bar
            data_display = round(data_size / (10 ** 9), 2)
            t.set_description('{}GB // {} bad'.format(data_display,
                                                      len(bad_orgs)))

        # One final removal of files in bad_org.
        if bad_orgs:
            self.cleanup_bads(bad_orgs)

    def cleanup_bads(self, bad_orgs):
        """Remove organizations with bad XML files from index."""

        # Make a copy of index list since we're iterating over original
        # index and simultaneously modifying updated_index below.
        updated_index = self.index.copy()
        print('Update index to remove {} bad files.'.format(len(bad_orgs)))
        for bad_org in bad_orgs:
            updated_index.remove(bad_org)
        # This should create new index file.
        with open('index.json', 'w') as f:
            print('Rewriting index to local directory.')
            json.dump(updated_index, f)
        print('Writing success.\n')

    def check_data(self):
        """Check that all index files are indeed stored locally."""

        self.set_index_to_local()
        print('\nChecking that all index files have been stored locally.')
        for org in tqdm(self.index):
            url = org['URL']
            file_name = url.rsplit('/')[-1]
            file_address = 'data/{}'.format(file_name)
            is_xml_cached = os.path.isfile(file_address)
            if not is_xml_cached:
                raise Exception('Cannot find file {}'.format(file_name))
        print('All index files are stored locally.')


# To run from command line
if __name__ == '__main__':
    data_object = Data()
    data_object.get_data()
    data_object.check_data()
