#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A fetcher module to download a bundle over HTTP.
"""

__author__ = "Bruce Duncan"
__copyright__ = "Copyright 2010, Bruce Duncan, University of Edinburgh"
__licence__ = "GPL"
__version__ = "trunk"
__maintainer__ = "Bruce Duncan"
__email__ = "Bruce.Duncan@ed.ac.uk"
__status__ = "Development"


import sys


class fetcher(object):
    def __init__(self, config, transport):
        self.config = config
        self.transport = transport

    def fetch(self, bundle):
        pass

def main(args):
    pass


if __name__ == '__main__':
    main(sys.argv[1:])
