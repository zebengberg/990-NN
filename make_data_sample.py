import os
import json
import random
from tqdm import tqdm
import shutil


def get_sample(n):
    """Grab a random sample of n index files and copy them into directory."""
    
    # Making directory to hold data
    if not os.path.exists('sample_data'):
        os.mkdir('sample_data')
    
    if os.path.isfile('index.json'):
        print('Reading index from local directory.')
        with open('index.json') as f:
            index = json.load(f)
        print('Reading success.')
    else:
        print('Cannot find index file.')
        raise FileNotFoundError
    
    index_sample = []
    for _ in tqdm(range(n)):
        # Checking if xml file exists.
        while True:
            org = random.choice(index)
            url = org['URL']
            file_name = url.rsplit('/')[-1]
            file_address = 'data/{}'.format(file_name)
            if os.path.isfile(file_address):
                break
        shutil.copy(file_address, 'sample_data/')
        index_sample.append(org)
        
    # Writing sample_index as json dump.
    with open('index_sample.json', 'w') as f:
        print('Writing index of samples to local directory.')
        json.dump(index_sample, f)
        print('Writing success.')

    
# To run from command line
if __name__ == "__main__":
    get_sample(1000)
