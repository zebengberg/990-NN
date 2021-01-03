"""Install nine-ninety."""
import setuptools

with open('README.md') as f:
  long_description = f.read()
description = 'A library for working with data from nonprofit tax returns.'

install_requires = [
    'numpy',
    'matplotlib',
    'pandas',
    'tqdm',
    'tensorflow',
    'scikit_learn',
    'lxml',
    'requests',
    'aiohttp']


setuptools.setup(
    name='nine-ninety',
    author='Zeb Engberg',
    author_email='zebengberg@gmail.com',
    description=description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/zebengberg/nine-ninety',
    packages=setuptools.find_packages(),
    include_package_data=True,
    python_requires='>=3.8.0',
    install_requires=install_requires,
    version='0.0.1',
    license='MIT')
