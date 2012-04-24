"""Do a machination update"""

from machination import context
from machination.xmltools import XMLCompare
from machination.xmltools import MRXpath
from machination.xmltools import generate_wus
from machination.xmltools import pstring
from machination import utils
from lxml import etree
from lxml.builder import E
import copy
import topsort
import argparse
import os
import importlib
import sys
import pprint

class Update(object):

    def __init__(self, initial_status = None, desired_status = None):
        self.workers = {}
        self._initial_status = initial_status
        self._desired_status = desired_status
        self._previous_status = None

    def do_update(self):
        """Perform an update cycle"""
#        print("desired:\n %s\ninitial:\n %s" % (etree.tostring(self.desired_status(), pretty_print=True).decode(sys.stdout.encoding), etree.tostring(self.initial_status(), pretty_print=True).decode(sys.stdout.encoding)))
        print()
        print('desired:\n%s' % pstring(self.desired_status()))
        print()
        print('initial:\n%s' % pstring(self.initial_status()))

        comp = XMLCompare(copy.deepcopy(self.initial_status()),
                          self.desired_status())
        pprint.pprint(comp.bystate)
        try:
            deps = self.desired_status().xpath('/status/deps')[0]
        except IndexError:
            deps = etree.fromstring('<status><deps/></status>')[0]
        wudeps = comp.wudeps(deps.iterchildren(tag=etree.Element))
        # we need to make all workunits depend on something for
        # topsort to work
        wudeps.extend([['', x] for x in comp.find_work()])
        i = 0
        for lev in iter(topsort.topsort_levels(wudeps)):
            i += 1
            if i == 1:
                # this is the fake workunit '' we put in above
                continue
            print('xpaths for level {}:'.format(i))
            pprint.pprint(lev)
            wus, working_elt = generate_wus(set(lev), comp)
            print('wus for level {}:'.format(i))
            for wu in wus:
                print(pstring(wu))
            wubatch = []
            cur_worker = None
            for wu in wus:
                workername = MRXpath(wu.get('id')).workername(prefix='/status')
                if workername == cur_worker:
                    wubatch.append(wu)
                else:
                    self.worker(workername).do_work(wubatch)
                    wubatch = [wu]
            # do the last batch
            self.worker(workername).do_work(wubatch)

        new_status = self.gather_status()

    def initial_status(self):
        """Get the initial status. Will call gather_status() if necessary."""
        if self._initial_status is None:
            self._initial_status = self.gather_status()
        return self._initial_status

    def desired_status(self):
        """Get the desired status. Will download and compile status if necessary."""
        if self._desired_status is None:
            # TODO(colin): replace this with fetch / compile
            self._desired_status = etree.parse(os.path.join(
                    context.cache_dir(), 'desired-status.xml')).getroot()
        return self._desired_status

    def previous_status(self):
        """Get the status from the previous run."""
        if self._previous_status is None:
            fname = os.path.join(context.cache_dir(), 'previous-status.xml')
            try:
                self._previous_status = etree.parse(fname).getroot()
            except IOError:
                # couldn't read file may be lack of permission or not exists
                # if not exists (first run?) we should make a new status
                if not os.path.isfile(fname):
                    self._previous_status = E.status()
                else:
                    raise
        return self._previous_status

    def gather_status(self):
        """Invoke all workers' generate_status() and gather into one."""
        status = copy.deepcopy(self.previous_status())
        # find all workers
        stelt = status.xpath('/status')[0]
        for welt in status.xpath('/status/worker'):
            # the following should create a worker object and store it
            # in self.workers
            wstatus = self.worker(welt.get("id")).generate_status()
            stelt.remove(welt)
            stelt.append(wstatus)
        for welt in self.desired_status().xpath('/status/worker'):
            if welt.get("id") in self.workers:
                continue
            wstatus = self.worker(welt.get("id")).generate_status()
            stelt.append(wstatus)
        return status

    def worker(self, name):
        """Get the worker object for name."""
        if name in self.workers:
            return self.workers[name]

        try:
            w = importlib.import_module('machination.workers.' + name)
        except ImportError as e:
            if str(e).startswith('No module named '):
                # TODO: assume no python module for this worker,
                # try to find and execute an OL worker
                try:
                    w = OLWorker(name)
                except Exception as eol:
#                    logger.emsg("No worker %s, giving up!" % name)
                    raise WorkerError(name, e, eol)
        self.workers[name] = w
        return w

class WorkerError(Exception):
    def __init__(self, wname, epy, eol):
        Exception.__init__(self, wname, epy, eol)
        self.wname = wname
        self.epy = epy
        self.eol = eol

    def __str__(self):
        return 'Could not load worker "{}" as python module or OL worker:\n\nPython import error:\n{}\n\nOL worker error:\n{}'.format(self.wname, self.epy, self.eol)

class OLWorker(object):
    """Other Language Worker: wrapper for workers not in python."""

    def __init__(self, wid):
        self.wid = wid
        self.progdir = utils.worker_dir(wid)
        self.progfile = None
        for f in os.listdir(self.progdir):
            if f == wid or f.startswith(wid + "."):
                self.progfile = f
                self.progpath = os.path.join(self.progdir, self.progfile)
                break
        if self.progfile is None:
            raise Exception("No OL worker named {} in {}".format(self.wid, self.progdir))

    def generate_status(self):
        """Execute worker with generate_status call and return result from stdout."""
        # TODO(colin): exec worker
        pass

    def do_work(self, wus):
        """Execute worker with do_work call. Return result from stdout."""
        # TODO(colin): exec worker
        pass

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--desired', '-d', nargs='?',
                        help='desired status file')
    parser.add_argument('--desired_xpath', '-dx', nargs='?',
                        help='xpath of status in desired status file')
    parser.add_argument('--initial', '-i', nargs='?',
                        help='initial status file')
    parser.add_argument('--initial_xpath', '-ix', nargs='?',
                        help='xpath of status in initial status file')

    args = parser.parse_args()

    desired = None
    if args.desired is not None:
        desired = etree.parse(args.desired).getroot()
        if args.desired_xpath is not None:
            desired = desired.xpath(args.desired_xpath)[0]
            if 'id' in desired.keys():
                del desired.attrib['id']

    initial = None
    if args.initial is not None:
        initial = etree.parse(args.initial).getroot()
        if args.initial_xpath is not None:
            initial = initial.xpath(args.initial_xpath)[0]
            if 'id' in initial.keys():
                del initial.attrib['id']

    Update(desired_status=copy.deepcopy(desired),
           initial_status=copy.deepcopy(initial)).do_update()
