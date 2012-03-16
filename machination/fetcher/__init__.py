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


class Fetcher(object):
    def __init__(self, config, bundle):
        self.config = config
        self.bundle = bundle

    def __call__(self):
        # Iterate through suitable transports for this download
        for transport in self.config.xpath('worker[@id="fetcher"]/sources/*'):
            # Import a suitable module to handle it
            try:
                f = __import__(__name__ + '.' + transport.tag,
                    fromlist=transport.tag).fetcher(self.config, transport)
            except ImportError as e:
                if e.message.startswith('No module named ') and e.message.split()[3] == transport.tag:
                    continue
                raise
            except AttributeError as e:
                if e.message == "'module' object has no attribute 'fetcher'":
                    continue
                raise

            # Execute it
            res = f.fetch(self.bundle)
            if res:
                return res
            # else: loop to try the next transport
        else:
            raise Exception("Could not find a suitable transport")


def main(args):
    pass


if __name__ == '__main__':
    main(sys.argv[1:])
