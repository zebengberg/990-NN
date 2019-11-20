import csv
import xml.etree.ElementTree as ElementTree
from tqdm import tqdm
import random
import json
import pandas as pd


class Parser:
    """Parse data on 990 tax form."""

    def __init__(self):
        self.data_directory = 'data/'  # change to local path with data
        self.ns = '{http://www.irs.gov/efile}'  # namespace for XML parsing
        self.data = []  # a list of parsed dicts to be converted to pd df
        self.org = None  # to be assigned with current organization for parsing
        self.root = None  # to be assigned from XML tree associated to org

        # Getting xpath key-value dictionaries needed for parsing XML files.
        xpath_table = '990_xpath_table.csv'
        with open(xpath_table) as f:
            next(f)  # skips over column names
            reader = csv.reader(f)
            rows = list(reader)
        self.pre_2013_dict = {row[1]: row[2] for row in rows}
        self.post_2013_dict = {row[1]: row[3] for row in rows}
        self.category_dict = {row[1]: row[0] for row in rows}
        self.type_dict = {row[1]: row[4] for row in rows}

    def insert_ns(self, xpath):
        """Put in the required 990 XML namespace into xpath address."""

        segments = xpath.split('/')
        xpath_ns = ''
        for segment in segments:
            xpath_ns += self.ns + segment + '/'
        xpath_ns = xpath_ns[:-1]  # deleting final forward slash
        return xpath_ns

    def parse(self, org):
        """Parse XML file associated to an organization."""

        # Starting to fill self.org with data from organization.
        # First use "meta-data" from index file, then get into XML tree.
        self.org = {'name': org['OrganizationName'],
                    'url': org['URL'],
                    'year': org['TaxPeriod']}

        file_name = org['URL'].rsplit('/')[-1]
        tree = ElementTree.parse(self.data_directory + file_name)
        self.root = tree.getroot()

        # If the XML file is intact, the root tag should not be Error.
        if self.root.tag == 'Error':
            raise Exception('The XML file is bad -- perhaps file DNE on AWS?')
        # If the XML file is intact, the EIN should match that from the index.
        ein_xpath = 'ReturnHeader/Filer/EIN'
        ein_xpath = self.insert_ns(ein_xpath)
        xml_ein = self.root.find(ein_xpath).text
        if org['EIN'] != xml_ein:
            print('Index EIN: {}   XML EIN: {}'.format(org['EIN'], xml_ein))
            raise Exception('EINs do not match between XML file and index.!')

        # Getting the XML 990 version. This is necessary for parsing xpaths.
        version = self.root.attrib['returnVersion']
        self.org['version'] = int(version[:4])
        # Choosing the dictionary to use based on the XML 990 version.
        if self.org['version'] < 2013:
            xpath_dict = self.pre_2013_dict
        else:
            xpath_dict = self.post_2013_dict

        for key in xpath_dict:
            xpath = xpath_dict[key]
            xpath_ns = self.insert_ns(xpath)
            try:
                self.org[key] = self.root.find(xpath_ns).text
            except AttributeError:
                self.org[key] = 0
            # Change data into a python type.
            # Need a custom function for booleans.
            types = {'int': int, 'str': str, 'float': float,
                     'bool': lambda x: 1 if (x == '1') or (x == 'true') else 0}
            self.org[key] = types[self.type_dict[key]](self.org[key])

        self.parse_officers()
        # Putting organization data into big list of dicts.
        self.data.append(self.org)

    def parse_officers(self):
        """Get officer and trustee data from current XML file."""

        officer_data = []
        xpath = 'ReturnData/IRS990/Form990PartVIISectionA'
        if self.org['version'] >= 2013:
            xpath += 'Grp'
            tags = ['PersonNm', 'BusinessName', 'ReportableCompFromOrgAmt']
        else:
            tags = ['NamePerson', 'NameBusiness',
                    'ReportableCompFromOrganization']
        xpath = self.insert_ns(xpath)
        officers = self.root.findall(xpath)

        for officer in officers:
            name = officer.find(self.ns + tags[0])
            if name is None:
                # In this case, officer is listed as a business.
                name = officer.find(self.ns + tags[1])
                if name is None:
                    print('See XML file: ' + self.org['url'])
                    raise AttributeError('Cannot find officer name.')
                else:
                    # Businesses have two lines of names so grab first line
                    name = name[0]
            name = name.text

            comp = officer.find(self.ns + tags[2])
            comp = 0 if comp is None else int(comp.text)
            # Could put related comp or other comp (403b) here.

            officer_data.append([name, comp])
        self.org['officers'] = officer_data


def parse_data(n=0):
    """Parse XML files and export csv."""

    print('Opening index file.')
    with open('index.json') as f:
        index = json.load(f)
    if n:
        orgs = random.sample(index, n)
    else:
        orgs = index
    parser = Parser()
    for org in tqdm(orgs):
        parser.parse(org)

    print('Successfully parsed. Writing to csv.')
    df = pd.DataFrame(parser.data)
    df.to_csv('data.csv', index=False)
    print('Successfully written.')


# To run from command line
if __name__ == "__main__":
    parse_data()
