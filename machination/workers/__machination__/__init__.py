"Worker for Machination itself"

from lxml import etree
from machination import context
from machination import utils
from machination import xmltools
from machination.xmltools import MRXpath
import os
import errno
import sys
import copy
import re
import shutil

class Worker(object):
    """Operate on Machination configuration

    """

    def __init__(self):
        # auto determine worker name
        self.name = self.__module__.split('.')[-1]
        # load up the correct worker description
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        self.mrx = MRXpath("/status/worker[@id='{}']".format(self.name))

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
        """Generate worker status element.

        Part generated: Everything from desired status is just
        returned, apart from:
          - versionInstalled: auto-generated from installed packages
        """
        # The current status of machination is just what desired
        # status says it is, apart from installedVersion.

        # Copy the __machination__ worker element as our starting point.
        w_elt = copy.deepcopy(context.get_worker_elt(self.name))

        # Delete any installedVersion elements
        for e in w_elt.xpath('installedVersion'):
            w_elt.remove(e)

        # Find installedVersion information
        self.generated_iv = getattr(self, self.get_installed_func())()
        w_elt.append(self.generated_iv)

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
  <machinationFetcherBundle id="machination-client-core-2.0.0"/>
  <machinationFetcherBundle id="machination-client-worker-w1-2.0.0"/>
  <machinationFetcherBundle id="machination-client-worker-w2-2.0.0"/>
</installedVersion>
'''
            )

    def _gen_installed_win7(self):
        elt = etree.Element("installedVersion")
        import wmi
        con = wmi.WMI()
        prods = con.query(
            "select * from Win32_Product where Name like 'Python machination-client%'"
            )
        for prod in prods:
            elt.append(etree.Element("machinationFetcherBundle", id=prod.Name[7:]))
        return elt


    def do_work(self, wus):
        results = []
        for wu in wus:
            wumrx = MRXpath(wu.get('id'))
            if wumrx.name() == 'installedVersion':
                if wu.get('op') == 'add' or wu.get('op') == 'deepmod':
                    self.self_update(wu)
                elif wu.get('op') == 'remove':
                    # pretend success
                    results.append(
                        etree.Element('wu', id=wu.get('id'), status='success')
                        )
                else:
                    raise Exception("shouldn't get {} wu for installedVersion".format(wu.get('op')))
            else:
                # Nothing to do: report success
                results.append(
                    etree.Element('wu', id=wu.get('id'), status='success')
                    )
        return results

    def self_update(self, wu):
        '''Perform a Machination self update.

        Sequence:
          - Copy bin_dir()/self_update to cache_dir()
          - Write installedVersion to cache_dir()/installed_version.xml
          - os.execl() cache_dir()/self_update which will:
            - remove worker packages except __machination__
            - remove core and __machination__ only if changed
            - add core package (if changed)
            - add worker packages
        '''
        # Create a directory in which to store self update material
        sudir = os.path.join(context.cache_dir(), 'selfupdate')
        try:
            os.mkdir(sudir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # Copy the self update script
        su_script_name = 'machination-self-update.py'
        shutil.copy(
            os.path.join(context.bin_dir(), su_script_name),
            sudir
            )
        su_script = os.path.join(sudir, su_script_name)

        # Write installedVersion elements (current and desired)
        iv = etree.Element('iv')
        # Write the location of bundles into iv (at /iv/@bundleDir)
        iv.set(
            'bundleDir',
            os.path.join(context.cache_dir(), 'bundles')
            )
        wu[0].set('version', 'desired')
        self.generated_iv.set('version', 'current')
        iv.append(self.generated_iv)
        iv.append(wu[0])
        iv_file = os.path.join(sudir, 'installed_version.xml')
        with open(iv_file, 'w') as ivf:
            ivf.write(etree.tostring(iv))

        # Hand over to the self update script
        os.execl(
            sys.executable,
            'machination-self-update',
            su_script,
            iv_file)
