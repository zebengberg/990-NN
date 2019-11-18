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







IRSx structures, standardizes, and documents the raw 990 tax filings released as xml documents, but what to do with that data is up to you. If you just want to load everything into a database, look at [990-xml-db](https://github.com/jsfenfen/990-xml-database/), which includes management command loading scripts.

IRSx can be used as a command line tool or from within a python library. 


Let's start with the command line usage.

We're using the "object_id" 201533089349301428 assigned by the IRS to the Dec. 2014 annual nonprofit tax return (990) filed by "Sutter Health Sacramento Region", which is one of quite a few returns disclosed in the [2016 index file](https://s3.amazonaws.com/irs-form-990/index_2016.csv). See more in [finding an object id](#getting-an-object-id)  

To dump the xml as a human-readable .csv file at the command line, use: 

	$ irsx --format=csv 201533089349301428

Which gives a csv file [like this](samples/201533089349301428.csv) with IRS form, line number and variable descriptions (as well as the value entered in this return). To make the file readable in a text editor / on a screen, use the txt format option, and only display one schedule (the complete command line usage is available with --help). 

	$ irsx --format=txt --schedule=IRS990ScheduleJ 201533089349301428

You can omit the schedule and it will print out information about each part of the filing, but adding it can help zero in on whatever part you are interested in. 

Allowed output formats are 'csv', 'txt', and 'json'. [See the results as [.csv](samples/201533089349301428_ScheduleJ.csv), [.txt](samples/201533089349301428_ScheduleJ.txt)., or [.json](samples/201533089349301428_ScheduleJ.json) files]. CSV and TXT are "flat" formats for human readibility, whereas the json is nested like the original tax forms (although only available for schema years 2013 and forwards).

The JSON file output is 'standardized' in that it uses the same variable name to refer to the same quantity across tax versions, whereas the csv and txt representations just display the xpath, line numbers and variable descriptions assigned to them in the tax version they've used.

The resulting txt file from the command above should be a line by line reconstruction of the tax form that includes the IRS' text describing the 'Line' and 'Description' of the variable, as well as the 'xpath' used, the repeating group name and the group_index if applicable. It should look something like this:

		Schedule IRS990ScheduleJ
	
		... [ lengthy output of many, many variables] ...
	
		****************
		  Value: '191624'
		Form: IRS990ScheduleJ
		Line:Part II Column (B)(ii)
		Description:Part II contents; Bonus and incentive compensation ($) from related organizations
		Group: SkdJRltdOrgOffcrTrstKyEmpl group_index 16
		
		... [ truncated ]
	

We can also it as a python library to pull out specific pieces of data, across versions

	>>> from irsx.xmlrunner import XMLRunner
	>>> xml_runner = XMLRunner()
	>>> parsed_filing = xml_runner.run_sked(201533089349301428, 'IRS990ScheduleJ')
	>>> key_employees = parsed_filing.get_result()[0]['groups']['SkdJRltdOrgOffcrTrstKyEmpl']
	>>> for employee in key_employees:
	...  print("Name:%s, Base Compensation, related orgs $%s" % (employee['PrsnNm'], employee['CmpnstnBsdOnRltdOrgsAmt']))
	... 
	Name:John Boyd, Base Compensation, related orgs $268967
	Name:Thomas Blinn, Base Compensation, related orgs $468913
	... 



## About

IRSx is a python library and command line tool to simplify working with nonprofit tax returns [released](https://aws.amazon.com/public-datasets/irs-990/) by the IRS in XML format. The library currently standarizes returns submitted in formats dating from 2013 and forwards into consistently named datastructures that follow the same format as the "paper" 990. Repeating elements, such as the salary disclosed for best compensated employees, appear at the end of each schedule. We plan to release updated metadata that will allow processing of earlier forms. For a higher level view, see the [roadmap](https://github.com/jsfenfen/990-xml-reader/blob/master/roadmap.md) and [project architecture](https://github.com/jsfenfen/990-xml-reader/blob/master/architecture.md).

Forms from schema years ranging from 2010 to the present are 'viewable' in CSV and TXT mode via the command line tool.

Forms 990, 990EZ, 990PF and all lettered schedules A-O and R are all supported (although schedule B--donor information, which doesn't have to be disclosed--is typically marked as 'restricted').

From the command line, xml files can be output as machine readable json, csv or human readable text. From within a python program, the results are returned as native data structures. 

Filers are allowed to leave blank tax lines not applicable to them. IRSx returns only schedules and lines that have been completed by filers.

The tax returns are complex--the easiest way to understand them is to consult the [metadata csv files](https://github.com/jsfenfen/990-xml-reader/tree/master/irs_reader/metadata), and cross reference these to the forms in [sample\_schedules](https://github.com/jsfenfen/990-xml-reader/tree/master/irs_reader/sample_schedules) (which contains recent pdf versions of the schedules).  The data returned for each schedule read contains schedule parts (see the [schedule\_parts.csv](https://github.com/jsfenfen/990-xml-reader/tree/master/irs_reader/metadata/schedule_parts.csv) for all possible parts) and repeating groups (see [groups.csv](https://github.com/jsfenfen/990-xml-reader/tree/master/irs_reader/metadata/groups.csv)) that occur within that schedule. Both repeating groups and schedule\_parts contain variables, which are documented in the [variables.csv](https://github.com/jsfenfen/990-xml-reader/tree/master/irs_reader/metadata/variables.csv) table. 


## Hype

10/15/2019: [Kaiser Health News](https://khn.org/news/patients-eligible-for-charity-care-instead-get-big-bills/) used data dumped with IRSx to find that among hospital in the US, "nearly half (45 percent) of nonprofit hospital organizations are routinely sending medical bills to patients whose incomes are low enough to qualify for charity care." Cross published with the [Washington Post](https://www.washingtonpost.com/business/economy/free-or-discounted-care-is-available-at-some-hospitals-but-they-dont-make-it-easy/2019/10/10/8ad4c540-e92a-11e9-9c6d-436a0df4f31d_story.html). 

12/3/18: [Tweetstorm](https://twitter.com/TimBroderick/status/1069387919608160256) from @TimBroderick, who used IRSx while working on an "analysis of about 100 Illinois hospitals' tax forms \[which\] revealed that measuring community benefit spending through Form 990 filings can provide an inconsistent and distorted view of a hospital's impact." [Related Article](https://www.modernhealthcare.com/article/20181201/NEWS/181119965)

## Cookbook

A collection of IRSx and related "recipes" is [online here](https://github.com/jsfenfen/irsx_cookbook). If you're looking for examples, that might be a good place to start.

## Command line IRSx
Installing the library will also install the irsx command line tool, which uses the IRS' object\_ids to reference a particular filing. By default results are printed to the terminal, but can be saved to a specific file with the `--file` option. Using the `--verbose` flag will display a bit more information about what's happening, but should not be used if you're trying to capture the output into a file (as it won't follow the format needed). 

## CLI Output formats: json, csv, txt

The command line tool supports three styles of 'displaying' a filing. The output can also be written out to a file specified with the `--file` option. 

For browsing and human-reference, csv or text is often easier to understand, because it maintains the order of the original filing. For bulk use or database entry, json is probably more relevant, because the "structure" of the original database--broken into parts, some repeating--is better replicated in those. 

The csv output is "transposed" from a normal csv--in other words, each *row* represents a variable. Repeating variables may appear multiple times (though the 'group_index' should increment with each new occurence).

JSON output is only available for schema versions from 2013 and later. CSV and TXT output are available for 2010 schemas and later. 

- __JSON__ The first is a nested-json structure that provides a consistent way of describing variables for all schema versions from 2013 and forwards. The down side of this is that json is not ordered, so it can be confusing for humans to view. The description and line number fields are for the "canonical" version--2016v3.0--and so may vary from those seen on the form. 
- __CSV__ This isn't a 'real' csv file, it's really a listing of all the different variables found, along with metadata like line number and description. It's available for versions 2010 and forwards. This doesn't attempt to restructure the content, it just spits it out in the order that it appears. This is often more human readable than json. Because it's a listing of all variables, the xpaths to those variables may repeat. A group_index column keeps count of which repeating group each variable belongs to. Both CSV and TXT formats use line numbers and descriptions that are specific to the version (these can both change over time) so these come from the line_number.csv and description.csv that are version specific.
- __TXT__ There's also a txt format output that is very similar to csv in that it prints the rows it finds in an ordered dump, but makes it slightly more readable. CSV is intended to be viewed in a spreadsheet program, whereas TXT format translates better to a text editor / wider than normal terminal window.

### CSV / TXT examples


CSV and TXT are often more useful for browsing a file--we can eyeball the whole filing, but sometimes it's handy to zero in on just one schedule. Irsx has a shortcut, the --list_schedules option to show you what's available.
		 
	
		$ irsx --list_schedules 201533089349301428
	
		['ReturnHeader990x', 'IRS990', 'IRS990ScheduleA', 'IRS990ScheduleB', 'IRS990ScheduleC', 'IRS990ScheduleD', 'IRS990ScheduleG', 'IRS990ScheduleH', 'IRS990ScheduleI', 'IRS990ScheduleJ', 'IRS990ScheduleK', 'IRS990ScheduleL', 'IRS990ScheduleM', 'IRS990ScheduleO', 'IRS990ScheduleR']
	
Now let's look at a human readable text version of schedule J

	$ irsx --format=txt --schedule=IRS990ScheduleJ 201533089349301428

Note that the --schedule argument also works in json or csv mode.

The output is lengthy, but let's look at an excerpt:

	****************
	  Value: '296489'
	Form: IRS990ScheduleJ
	Line:Part II Column (B)(ii)
	Description:Part II contents; Bonus and incentive compensation ($) from related organizations
	Group: SkdJRltdOrgOffcrTrstKyEmpl group_index 1
	
	****************
	  Value: 'CEO, Reg Amb Care, SRR'
	Form: IRS990ScheduleJ
	Line:Part II Column (A)
	Description:Part II contents; Title of Officer
	Group: SkdJRltdOrgOffcrTrstKyEmpl group_index 1
 
 Note the "Group" variable. This corresponds to the db_name in the groups.csv file in the metadata directory. It is only listed if a variable is part of a "repeating group" (like officers / trustees / key employees). The "group\_index" variable represents the number of times this variable has been seen.
 


### JSON examples



	$ irsx 201533089349301428
	[{"schedule_name": "ReturnHeader990x", "groups": {}, "schedule_parts": {"returnheader990x_part_i": {"object_id": 201533089349301428, "ein": "941156621", "RtrnHdr_RtrnTs": "2015-11-04T20:09:01-06:00",...

This will just spit out a json representation of the entire filing. See more about how to get an IRS object_id and how to read the data format that's returned below.


The general structure of the return is an array of schedules:

	[
	      {
	        "schedule_name": <Schedule Name>,
	        "schedule_parts": {
	                "<schedule_part name>": { dictionary of variables in this part },
	                	...
	        "groups": {
	        	"<group name>":
	        		[ Array of groups of this name that were found
	        			{ dictionary of variables in this group }
	        		]
	        }, ... 
	]
	        
	
Each schedule part or repeating group includes the original object\_id and ein of the filing as well as all the IRS variables. The schedule\_part name and the group name are the values that appear in those respective .csv files in the [metadata directory](https://github.com/jsfenfen/990-xml-reader/tree/master/irs_reader/metadata). If a particular schedule, schedule part or repeating group has no values, it is not included.

Note that IRSX will download the file if it hasn't already--for more information about the location, use the --verbose option. IRSX by default will retrieve the file from the IRS' public Amazon S3 bucket. If you plan to work with a large collection of files, you may want to host xml on your own bucket, and use bulk tools like AWS CLI's sync to move many documents at once.



### Complete command line usage
This is available with the --help option

	usage: irsx [-h] [--verbose]
	            [--schedule {IRS990,IRS990EZ,IRS990PF,IRS990ScheduleA,IRS990ScheduleB,IRS990ScheduleC,IRS990ScheduleD,IRS990ScheduleE,IRS990ScheduleF,IRS990ScheduleG,IRS990ScheduleH,IRS990ScheduleI,IRS990ScheduleJ,IRS990ScheduleK,IRS990ScheduleL,IRS990ScheduleM,IRS990ScheduleN,IRS990ScheduleO,IRS990ScheduleR,ReturnHeader990x}]
	            [--no_doc] [--format {json,csv,txt}] [--file FILE]
	            [--list_schedules]
	            object_ids [object_ids ...]
	
	positional arguments:
	  object_ids            object ids
	
	optional arguments:
	  -h, --help            show this help message and exit
	  --verbose             Verbose output
	  --schedule {IRS990,IRS990EZ,IRS990PF,IRS990ScheduleA,IRS990ScheduleB,IRS990ScheduleC,IRS990ScheduleD,IRS990ScheduleE,IRS990ScheduleF,IRS990ScheduleG,IRS990ScheduleH,IRS990ScheduleI,IRS990ScheduleJ,IRS990ScheduleK,IRS990ScheduleL,IRS990ScheduleM,IRS990ScheduleN,IRS990ScheduleO,IRS990ScheduleR,ReturnHeader990x}
	                        Get only that schedule
	  --no_doc              Hide line number, description, other documentation
	  --format {json,csv,txt}
	                        Output format
	  --file FILE           Write result to file
	  --list_schedules      Only list schedules




### Getting an object id

The IRS releases one xml file per 990 filing, which is identified by a unique object id. Irsx uses that unique id as well, so we need to know it to extract data. To find the object\_id, look at the annual index files from the IRS (also have a look at irsx_index, a helper command described below).

The files are available at: [https://s3.amazonaws.com/irs-form-990/index_2017.csv](https://s3.amazonaws.com/irs-form-990/index_2017.csv). Other years, from 2011 forward, are available at similar URLs, just replace '2017' with the year you want [Note that the year is the year the return was received by the IRS]. Some years have >300,000 filings in them, so the index files might not open in older versions of excel.

You can use command line tools, like [csvkit](https://csvkit.readthedocs.io/en/1.0.2/), to search through the file pretty quickly to find the id you want. These are the headers:

	$ head -n 1 index_2016.csv 
	RETURN_ID,FILING_TYPE,EIN,TAX_PERIOD,SUB_DATE,TAXPAYER_NAME,RETURN_TYPE,DLN,OBJECT_ID

Using csvcut we can just spit out the EIN, TAX\_PERIOD, TAXPAYER\_NAME and the OBJECT\_ID we need by identifying the column numbers 

		$ csvcut -c 3,4,6,9 index_2016.csv | head -n 3
	EIN,TAX_PERIOD,TAXPAYER_NAME,OBJECT_ID
	742661023,201412,HARRIET AND HARMON KELLEY FOUNDATION FOR THE ARTS,201543159349100344
	562629114,201412,BROWN COMMUNITY DEVELOPMENT CORPORATION,201543109349200219


I'm looking for filings from "Sutter Health" (though note I use all caps to search). 

		$ csvcut -c 3,4,6,9 index_2016.csv | grep 'SUTTER HEALTH'
	941156621,201412,SUTTER HEALTH SACRAMENTO SIERRA REGION,201533089349301428
	990298651,201412,SUTTER HEALTH PACIFIC,201523039349301087
	942788907,201412,SUTTER HEALTH,201543089349301429

Let's use Sutter Health Sacramento Sierra Region's 12/2014 filing, which has an object id number of 201533089349301428 [ and an EIN of 941156621]. You can find the relevant filing via nonprofit explorer [here](https://projects.propublica.org/nonprofits/organizations/941156621). 


## Configuring the file cache directory

IRSx ships with a default location to which each xml file is downloaded. But if you're dealing with these files in bulk you may wish to sync specific folders directly, and point irsx' default cache *at that folder*. That way you could download the files in bulk, and then runs irsx without it ever having to download the files, because they were already on disk.

### Environment variables ###

You can set the `IRSX_CACHE_DIRECTORY` environment variable in order to control where
IRSx saves and looks for data files. For example, on Linux and OS X, you could
run the following before you run `irsx` or `irsx_index`:

        $ export IRSX_CACHE_DIRECTORY=/absolute/path/to/arbitrary/directory/irsx

        $ irsx --format=csv 201533089349301428
        # XML will end up at /absolute/path/to/arbitrary/directory/irsx/XML/201533089349301428_public.xml

        $ irsx_index --year 2017
        # CSV will end up at /absolute/path/to/arbitrary/directory/irsx/CSV/index_2017.csv

If you don't like the forced `XML` and `CSV` directories, you can have even more control by setting two other environment variables instead:

*   Set `IRSX_WORKING_DIRECTORY` to an absolute path where tax returns' XML files will be stored.
*   Set `IRSX_INDEX_DIRECTORY` to an absolute path where yearly indexes' CSV files will be stored.

For example:

        $ export IRSX_WORKING_DIRECTORY=/absolute/path/to/working/directory
        $ irsx --format=csv 201533089349301428
        # XML will end up at /absolute/path/to/working/directory/201533089349301428_public.xml

        $ export IRSX_INDEX_DIRECTORY=/absolute/path/to/index/directory
        $ irsx_index --year 2017
        # CSV will end up at /absolute/path/to/index/directory/index_2017.csv


### Legacy configuration ###

You also can configure IRSx's cache location by setting the local_settings.py file. To figure out where that settings file is, log in to a terminal and type:

	>>> from irsx.settings import IRSX_SETTINGS_LOCATION
	>>> IRSX_SETTINGS_LOCATION
	'/long/path/to/lib/python3.6/site-packages/irsx/settings.py'

[ If you get an error, try upgrading irsx with `pip install irsx --upgrade` -- this feature was added in 0.1.1. ]


Go to that directory. You can either modify the settings.py file or the local_settings.py file. To do the latter, first `cd` into the directory where the settings files live and run:

	$ cp local_settings.py-example local_settings.py

Then edit local_settings.py to set WORKING\_DIRECTORY to where the raw xml files are found. 


## IRSx from python 

Much broader functionality is available by running from within python.


	>>> from irsx.xmlrunner import XMLRunner
	>>> xml_runner = XMLRunner()
	>>> parsed_filing = xml_runner.run_filing(201533089349301428)
	>>> result = parsed_filing.get_result()  # An array of parsed schedules
	>>> schedule_list = parsed_filing.list_schedules() # an array of form names

Result is an array of parsed form schedules; each schedule's name can be accessed as result[i]['schedule_name']. 

    >>> import json  # to format output
	>>> for sked in result:
	...  print("Schedule: %s" % sked['schedule_name'])  
	...  print(json.dumps(sked, indent=4, sort_keys=True))   # make json more readable
	
	Schedule: ReturnHeader990x
	{
	    "csv_line_array": [],
	    "groups": {},
	    "schedule_name": "ReturnHeader990x",
	    "schedule_parts": {
        "returnheader990x_part_i": {
	            "BsnssNm_BsnssNmLn1Txt": "SUTTER HEALTH SACRAMENTO SIERRA REGION",
	 		... [ full output is quite lengthy... ]

	


Note that this filing has *3* different schedule K's in it. 

	>>> skedk = parsed_filing.get_parsed_sked('IRS990ScheduleK')
	>>> len(skedk)  # Bond schedule fits 4 entries/form; all must be listed
	3
	
Only schedule K is allowed to repeat--all other lettered schedules (i.e. Schedules A-O and R) may only appear once. If we only care about one schedule we can extract only it (though note that the result will still be an array of schedules). 

	>>> parsed_filing = xml_runner.run_sked(201533089349301428, 'IRS990ScheduleJ')
	>>> resultskedj = parsed_filing.get_result() # an array of ScheduleJ forms
	>>> len(resultskedj)   # only schedule J's are returned.
	1


Show the repeating groups that are present this schedule:

	>>> print(result[0]['groups'].keys())
	dict_keys(['SkdJRltdOrgOffcrTrstKyEmpl', 'SkdJSpplmntlInfrmtnDtl'])

	
Show the schedule parts that are present:

	>>> print(result[0]['schedule_parts'].keys())
	dict_keys(['skedj_part_i'])
	
Delve into one:	
	
	>>> key_employees = result[0]['groups']['SkdJRltdOrgOffcrTrstKyEmpl']
	>>> print(len(key_employees))
	20
	>>> key_employees[0].keys()
	
	dict_keys(['object_id', 'ein', 'PrsnNm', 'TtlTxt', 'BsCmpnstnFlngOrgAmt', 'CmpnstnBsdOnRltdOrgsAmt', 'BnsFlngOrgnztnAmnt', 'BnsRltdOrgnztnsAmt', 'OthrCmpnstnFlngOrgAmt', 'OthrCmpnstnRltdOrgsAmt', 'DfrrdCmpnstnFlngOrgAmt', 'DfrrdCmpRltdOrgsAmt', 'NntxblBnftsFlngOrgAmt', 'NntxblBnftsRltdOrgsAmt', 'TtlCmpnstnFlngOrgAmt', 'TtlCmpnstnRltdOrgsAmt', 'CmpRprtPrr990FlngOrgAmt', 'CmpRprtPrr990RltdOrgsAmt'])
	
	>>> for employee in key_employees:                                                                
		  print("[%s] [%s] $%s" % (employee['PrsnNm'], employee['TtlTxt'], employee['TtlCmpnstnRltdOrgsAmt']) )

	[John Boyd] [CAO, MNTL HLTH & CONT CARE SSR] $493297
	[Thomas Blinn] [CEO, Reg Amb Care, SRR] $1007654
	[Pat Brady] [CEO, Sutter Roseville Med. Ctr] $989398
	[James Conforti] [Regional President, SHSSR] $1406818
	[Dennie Conrad] [REG VP, PLNNG & BUS DEV SHSSR] $486103
	[Patrick Fry] [Trustee, President & CEO SH] $6354697
	[Terry Glubka] [CEO, Sutter Solano Medical Ctr] $705442
	[Mitch Hanna] [CAO, SAFH] $647751
	[Sarah Krevans] [COO Sutter Health] $2186723
	[Shelly McGriff] [CNE Sutter Med Ctr Sac.] $477144
	[John Mesic MD] [CMO, Sac Sierra Region] $968939
	[Carrie Owen-Plietz] [CEO, Sutter Med Ctr Sacramento] $934648
	[Anne Platt] [CEO, SUTTER AMADOR HOSPITAL] $579266
	[Thomas Ream II] [Reg CIO, Sac Sierra Region] $424847
	[Jeffrey Sprague] [CFO, Sac Sierra Region (Pt Yr)] $1454430
	[Jeffrey Szczesny] [Reg VP HR, Sac Sierra Region] $633383
	[Paige Terra] [CFO (Part Year)] $657288
	[Janet Wagner] [CAO, Sutter Davis Hospital] $745985
	[PENNY WESTFALL] [VP & REG COUNSEL, SSR] $638189
	[BARBARA NELSON] [CNE, SUTTER ROSEVILLE MED. CTR] $450466


### IRSX reference

There are many, many variables; they are described in greater depth at [http://irsx.info/](http://irsx.info/)

### Variable errors and deprecated values

In normal operation variable errors--where tax returns specify a value that's not defined in the schema files--should not be a frequent occurrence, and can be suggestive of larger problems. This section is intended mainly for testing, development, or adding new schema versions. 

To understand which variables are not recorded, or missed, you need to know a bit about how xml is represented. Consider this snipped:

		<PreparerFirmGrp>
	      <PreparerFirmEIN>820343828</PreparerFirmEIN>
	      <PreparerFirmName>
	        <BusinessNameLine1Txt>COOPER NORMAN</BusinessNameLine1Txt>
	      </PreparerFirmName>
	      <PreparerUSAddress>
	        <AddressLine1Txt>PO BOX 5399</AddressLine1Txt>
	        <CityNm>TWIN FALLS</CityNm>
	        <StateAbbreviationCd>ID</StateAbbreviationCd>
	        <ZIPCd>833035399</ZIPCd>
	      </PreparerUSAddress>
	    </PreparerFirmGrp>
	    
The individual variables can be referred to by the "xpath" to them (a slash-separated record of the element hierarchy), so for instance, the name of the business that completed this return is /PreparerFirmGrp/PreparerFirmName/BusinessNameLine1Txt . That assumes this element is the "root", but the full path to this element (which is in the returnheader section) is this: /Return/Returnheader/PreparerFirmGrp/PreparerFirmName/BusinessNameLine1Txt.

Imagine the return includes a BusinessNameLine3Txt -- in other words, a value with the xpath /PreparerFirmGrp/PreparerFirmName/BusinessNameLine3Txt . That's unlikely to happen--the IRS has validation software that would likely prevent this from being submitted. If irsx encounters a variable that's not defined in variables CSV it simply ignores it and logs it as a keyerror. You can retrieve the keyerrors from any filing using the library.   

	 
	completed_filing  = self.xml_runner.run_filing(FILING_ID)
	if completed_filing.get_keyerrors(): # Returns True / False
        keyerrors = completed_filing.get_keyerrors()
        

The return value should be a list of dictionaries like this:  

	[ 'schedule_name': NAME, 
	  'keyerrors':
	  		['element_path': XPATH_ERROR, 
	  		 'element_path': XPATH_ERROR, 
	  		 ...
	
	  		]
	 ]

By far the biggest source of keyerrors are tax return items that no longer occur on current forms. 

Irsx works by turning a version-specific representation of a tax return (the original xml filing) into a standardized representation modeled on 2016v3.0. In other words, it tries to transform prior year tax forms into a canonical version.  For variables that have been removed, there's no canonical version. In the future, these variables will be tracked in a separate location.  



## irsx_index 

### Get the index files, --year[ly]

The IRS maintains annual index files, from 2011 forwards, of what filings have been received electronically and approved for release. Use the utility command, '$ irsx_index' to retrieve them all, or use the --year option to pick just one. Here we just grab 2017. Note that the --verbose flag is on, so that it'll say where the file is saved to. 

	$ irsx_index --year 2017 --verbose
	Getting index file for year: 2017
	Beginning streaming download of https://s3.amazonaws.com/irs-form-990/index_2017.csv
	Total file size: 18.18 MB
	Download completed to /Users/jfenton/github-whitelabel/envs/irsreader_env/lib/python2.7/site-packages/irs_reader/CSV/index_2017.csv in 0:00:02.934290

The location is specified in the settings file, but by default it'll go into a subdirectory of wherever the code is installed called /CSV/. You could set that by modifying the .settings file, but we'll save that for later.

 You could look at the file in a spreadsheet program, and you might want to keep it in your own database, but here I'll just use csvkit (`$ pip install csvkit`) to find something. Note that I'm doing this in the same directory as the file is in, to save typing. 
 
	cd /path/to/virtualenv/lib/python2.7/site-packages/irs_reader/CSV/
	


# Developer directions

#### To use without installing via pip

From the directory with the readme in it, instead of the irsx command, use `$ python -m irs_reader.irsx_cli` so that the command line tools are run as modules and python doesn't freak out. 
You can still add command line args, like this:

nd suggesting improvements. 
