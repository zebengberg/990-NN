# nine-ninety

> Predict with nonprofit tax returns.

- [Install](#install)
- [Basic Usage](#basic-usage)
- [Background](#background)
- [Models](#models)
- [Results](#results)
- [License](#license)

## Install

This package requires Python 3.8. If using conda, you can create a new environment to install the correct Python version.

```sh
conda create --name py38 python=3.8
```

Clone or download this repository locally. Install with pip.

```sh
git clone https://github.com/zebengberg/nine-ninety
pip install nine-ninety
```

## Basic Usage

This package can be used for two purposes.

- Download and parse publicly available 990 tax forms.
- Explore and model with the tax form data.

AWS hosts an S3 bucket containing individual XML files representing 990 tax forms filed with the IRS. As of January 2021, there were 1.9 million such files, all of which can be accessed through an HTTPS endpoint. The `nine_ninety.scrape` module provides tools for indexing and asynchronously requesting XML files. As these files arrive, the tree-like XML data is parsed and converted into table form. Specifically, values associated to [specific xpaths](nine_ninety/xpath_headers.csv) are extracted and saved as CSV files (totaling ~1.5GB of disk space). The entire scrape can be completed overnight even with slow internet speeds. The scrape can be interrupted and resumed without losing progress. To begin scraping, run `python nine_ninety/scrape/scrape.py`.

## Background

The IRS requires nonprofit tax-exempt organizations to make their 990 tax returns available for public viewing. With the growing prevalence of electronic-filing, the IRS already had many of these tax forms in a digital format. To facilitate public access, the [IRS released a huge collection](https://www.irs.gov/newsroom/irs-makes-electronically-filed-form-990-data-available-in-new-format) of these e-filed tax returns in 2016. Prior to this release, nonprofit tax forms were only digitally available as image files such as PDFs. Partnering with the hosting service [AWS](https://registry.opendata.aws/irs990/), the IRS released 990 tax returns as XML files dating as far back as 2009. This repository is constantly being updated as nonprofits submit annual tax forms.

Even more than the paper version of the 990 tax forms, these XML files are unwieldy and difficult to decipher. To make matters worse, the IRS made significant changes to the naming structure of 990 XML paths in 2013. Anyone interested in exploring the full 990 xml data set will need to find some way to address these inconsistencies.

Many open source projects already exist to access and explore this data set. [IRSx](https://github.com/jsfenfen/990-xml-reader) is an actively maintained repository with tools for downloading and parsing 990 XML data. While this library has some functionality for pre-2013 returns, it is best used with forms following the 2013 schema change. In 2017, the Nonprofit Open Data Collective put significant energy into reconciling the inconsistent 990 schemas to allow for easier data extraction from 990 XML files. This group created a so-called [master concordance file](https://github.com/Nonprofit-Open-Data-Collective/irs-efile-master-concordance-file) to map inconsistent xpaths to a common data dictionary.

[Open990](https://www.open990.org/) founder David Bruce wrote an excellent introductory [article](https://appliednonprofitresearch.com/posts/2018/06/the-irs-990-e-file-dataset-getting-to-the-chocolatey-center-of-data-deliciousness/) on the 990 data set. The [AWS header page](https://registry.opendata.aws/irs990/) for the 990 data set contains links to many other tools and applications exploring this data set.

## Models

### Text data

### Growth

### Organization Classification

## License
