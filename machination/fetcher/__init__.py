#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module to fetch "Bundles".

Machination workers call this library to request that a set of bundles be
downloaded.

This library will read a set of configuration files and load appropriate
submodules to fetch the files.

"""

__author__ = "Bruce Duncan"
__copyright__ = "Copyright 2012, Bruce Duncan, University of Edinburgh"
__licence__ = "GPL"
__version__ = "trunk"
__maintainer__ = "Bruce.Duncan"
__email__ = "Bruce.Duncan@ed.ac.uk"
__status__ = "Development"


import sys
import random


class Fetcher(object):
    def __init__(self, config, bundle):
        self.config = config
        self.bundle = bundle

    def __call__(self):
        transport = self.config['settings/sources/list/*/*']

def main(args):
    pass


if __name__ == '__main__':
    main(sys.argv[1:])
