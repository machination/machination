"Worker for Machination itself"

from lxml import etree
from machination import context
from machination import utils
from machination import xmltools
import os
import errno
import sys
import copy
import re

class Worker(object):
    """Operate on Machination configuration

    """

    def __init__(self):
        # auto determine worker name
        self.name = self.__module__.split('.')[-1]
        # load up the correct worker description
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        tmp_dispatch = [
            [r'^Windows$', r'^7$', r'.*', r'.*', '_gen_installed_win7'],
            [r'^Linux$', r'^Ubuntu', r'.*', r'.*', '_gen_installed_dpkg'],
            ]
        self.installed_dispatch_table = []
        # compile all the regexes
        for line in tmp_dispatch:
            newline = []
            for item in line[:4]:
                newline.append(re.compile(item))
            newline.append(line[4])
            self.installed_dispatch_table.append(newline)

    def generate_status(self):
        # The current status of machination is just what desired
        # status says it is, apart from installedVersion.

        # Copy the __machination__ worker element as our starting point.
        w_elt = copy.deepcopy(context.get_worker_elt(self.name))

        # Find installedVersion information
        w_elt.append(getattr(self, self.get_installed_func())())

        return w_elt

    def get_installed_func(self):
        """Return the name of the correct function to generate installedVersion.
        """
        osinf = utils.os_info()
        for line in self.installed_dispatch_table:
            if (
                line[0].search(osinf[0]) and
                line[1].search(osinf[1]) and
                line[2].search(osinf[2]) and
                line[3].search(str(osinf[3]))
                ):
                return line[4]
        raise Exception("Don't know how to generate installedVersion for {}".format(str(osinf)))

    def _gen_installed_dpkg(self):
        # just lie for debugging purposes
        return etree.fromstring(
            '''
<installedVersion>
  <machinationFetcherBundle id="machination-core-2.0.0-hash"/>
  <machinationFetcherBundle id="machination-worker-w1-2.0.0-hash"/>
  <machinationFetcherBundle id="machination-worker-w2-2.0.0-hash"/>
</installedVersion>
'''
            )

    def _gen_installed_win7(self):
        elt = etree.Element("installedVersion")
        import wmi
        con = wmi.WMI()
        prods = con.query(
            "select * from Win32_Product where Name like 'Python machination-core%' or Name like 'Python machination-worker%'"
            )
        for prod in prods:
            elt.append(etree.Element("bundle", id=prod.Name[7:]))
        return elt
        

    def do_work(self, wus):
        results = []
