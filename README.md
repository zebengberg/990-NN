# 990 NN

>A library for downloading, parsing, cleaning, analyzing, and visualizing data gathered from nonprofit tax returns.

## Table of Contents

- [Background](#background)
- [Scope](#scope)
- [Goals](#goals)
- [Install](#install)
- [Usage](#usage)
- [Examples](#examples)
- [Status](#status)
- [License](#license)

## Background

The IRS requires nonprofit tax-exempt organizations to make their 990 tax returns available for public viewing. With the growing prevalence of electronic-filing, the IRS already had many of these tax forms in a digital format. To facilitate public access, the [IRS released a huge collection](https://www.irs.gov/newsroom/irs-makes-electronically-filed-form-990-data-available-in-new-format) of these e-filed tax returns in 2016. Prior to this release, nonprofit tax forms were only digitally available as image files such as PDFs. Partnering with the hosting service [AWS](https://registry.opendata.aws/irs990/), the IRS released 990 tax returns as XML files dating as far back as 2009. This repository is constantly being updated as nonprofits submit annual tax forms.

Even more than the paper version of the 990 tax forms, these XML files are unwieldy and difficult to decipher. To make matters worse, the IRS made significant changes to the naming structure of 990 XML paths in 2013. Anyone interested in exploring the full 990 xml data set will need to find some way to address these inconsistencies.

Many open source projects already exist to access and explore this data set. [IRSx](https://github.com/jsfenfen/990-xml-reader) is an actively maintained repository with tools for downloading and parsing 990 XML data.  While this library has some functionality for pre-2013 returns, it is best used with forms following the 2013 schema change. In 2017, the Nonprofit Open Data Collective put significant energy into reconciling the inconsistent 990 schemas to allow for easier data extraction from 990 XML files. This group created a so-called [master concordance file](https://github.com/Nonprofit-Open-Data-Collective/irs-efile-master-concordance-file) to map inconsistent xpaths to a common data dictionary.

[Open990](https://www.open990.org/) founder David Bruce wrote an excellent introductory [article](https://appliednonprofitresearch.com/posts/2018/06/the-irs-990-e-file-dataset-getting-to-the-chocolatey-center-of-data-deliciousness/) on the 990 data set. The [AWS header page](https://registry.opendata.aws/irs990/) for the 990 data set contains links to many other tools and applications exploring this data set.

## Scope

Nearly all of the aforementioned projects use the AWS S3 protocol to download the millions of XML files to a local directory. While the files can be obtained individually over HTTPS, it is extremely slow because HTTPS requires significant client-server back and forth through an SSL handshake. Despite this time consuming download method, I wanted to avoid a pay-for AWS tool to download the 990 data set. Instead, I used the AWS provided [index listing](https://docs.opendata.aws/irs-990/readme.html) to download XML files one by one and store them to a local directory. My script required over a week of runtime to obtain the roughly 1.6 million 990 XML files.

With the data in hand, I created some basic tools for parsing the XML files into a `pandas.DataFrame` in order to explore interesting statistics of the 990 data set. I wrote a slimmed-down version of the master concordance file which would allow me to parse certain handpicked variables from XML files both before and after the 2013 XML-schema change. Though this project is very much a DIY endeavor, some of ideas could be extended and merged with the broader projects previously  described.

## Goals

In exchange for certain tax exemptions, nonprofit organizations are constrained in what they do with excess funds. Instead of giving money to shareholders and owners, nonprofit organization must reinvest any earnings back into their programs. In short, a nonprofit exists to enact to a certain mission as opposed to making money.

There are many possible metrics which can be used measure the success of a nonprofit organization. Because a nonprofit should be putting excess resources into its organization, one would expect the organization to grow larger over time. This growth can be approximated from certain data on 990 tax forms. Examples of such variables which track an organization's growth include
- net assets
- total revenue
- number of employees
- program expenses.

An organization's 990 tax forms gives some insight into how an organization allocates certain budgets over a year-long period. If the goal of a nonprofit organization is to grow and expand over time, we would expect that wise budgetary decisions with could lead to future growth. Thinking of future growth as a function of current spending, we might expect this function to be highly nonlinear. For this reason, the 990 data set provides an interesting opportunity to apply machine learning ideas to understand the relationship between current spending and future growth. In particular, in this project I build a neural network which aims to predict a nonprofit's future growth.

The 990 data set provides an interesting example real-world big-data. As far as I know, this is the first example of applying machine learning ideas methods to nonprofit tax data.

## Install

After downloading this repository, open the command line and enter
```shell script
python get_data.py /OPTIONAL/PATH/TO/DIRECTORY/FOR/HOLDING/XML/DATA/
```
to begin downloading data. As of November 2019, there was XX gb of xml files to download, and the entire download took roughly one week of runtime a single computer. Once the XML files are stored locally, run
```shell script
python parse_data.py /OPTIONAL/PATH/TO/DIRECTORY/ALREADY/HOLDING/XML/DATA/
```
## Usage

The module `get_data.py` is responsible for caching XML files. The AWS index files are first gathered, then `requests.get` is used to slowly download individual files over HTTPS. These files are then saved locally and progress resumes after a crash. For all sorts of possible reasons, the HTTPS request can fail. The snippet below shows that the request is repeatedly issued until the file is received.
```python
success = False
while not success:
    try:
        r = requests.get(url, timeout=3)
        success = True
    except requests.exceptions.RequestException as e:
        print('Request failed.  Sleep then try again.')
        print(str(e) + '\n')
        time.sleep(5)
```
In total, this function took over one week to run. Use built-in AWS tools if you want this to go much faster.

The downloaded 990 files contain thousands of individual data entries in tree-like XML structure. The class `Parse` in `parse_data.py` extracts some of this data into a dictionary so that it can be more readily used. At the heart of `Parse`, data is found using the `990_xpath_table.csv` (a mini-version of the master concordance file). Several selected rows of this table are shown below.

|             |                     |                                      |                                         |           |                  |
|-------------|---------------------|--------------------------------------|-----------------------------------------|-----------|------------------|
| CATEGORY    | KEY                 | XPATH BEFORE SCHEMA CHANGE           | XPATH AFTER SCHEMA CHANGE               | DATA TYPE | PART OR SCHEDULE |
| descriptive | ein                 | ReturnHeader/Filer/EIN               | ReturnHeader/Filer/EIN                  | str       | header           |
| descriptive | founded             | ReturnData/IRS990/YearFormation      | ReturnData/IRS990/FormationYr           | int       | header           |
| descriptive | has_lobbying        | ReturnData/IRS990/LobbyingActivities | ReturnData/IRS990/LobbyingActivitiesInd | bool      | 4                |
| revenue     | fundraising_revenue | ReturnData/IRS990/FundraisingEvents  | ReturnData/IRS990/FundraisingAmt        | int       | 8                |
| expense     | insurance_expense   | ReturnData/IRS990/Insurance/Total    | ReturnData/IRS990/InsuranceGrp/TotalAmt | int       | 9                |

For each XML file, a total of 71 of these xpaths are extracted and type casted for python use. In addition, data on highly compensated employees, of which there is not a fixed cardinality, is gathered. Iterating this over all (~1.6M) downloaded XML files, this data set is stored as a `pandas.DataFrame` and saved as a table for later use. Parsing all XML files was slow, but considerably faster than downloading them.

## Examples



See [this](examples.ipynb) jupyter notebook for some basic statistical examples.



## Status

This project is on-going.

TODO:
- Build data.csv file
- Make some basic statistical examples in a jupyter notebook, including visualizations
- Clean the data as necessary, pull apart several additional features (such as mission statement word frequency), normalize data appropriately
- Build and train NN
- Analyze results




## License

This project is licensed under the standard MIT License.





