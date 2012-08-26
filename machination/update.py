"""Do a machination update"""

from machination import context
from machination.xmltools import XMLCompare
from machination.xmltools import MRXpath
from machination.xmltools import generate_wus
from machination.xmltools import apply_wu
from machination.xmltools import pstring
from machination.xmltools import AssertionCompiler
from machination import utils
from machination.webclient import WebClient
from lxml import etree
from lxml.builder import E
import copy
import topsort
import argparse
import os
import importlib
import sys
import pprint
import traceback

l = context.logger

class Update(object):

    def __init__(self, initial_status=None, desired_status=None):
        self.workers = {}
        self._initial_status = initial_status
        self._desired_status = desired_status
        self._previous_status = None

    def do_update(self):
        """Perform an update cycle"""
        self.results = None
        if context.desired_status.getroot().get('autoconstructed'):
            raise ValueError('Refusing to use autoconstructed status.')
        l.dmsg('desired:\n%s' % pstring(self.desired_status()), 10)
        l.dmsg('initial:\n%s' % pstring(self.initial_status()), 10)

        comp = XMLCompare(copy.deepcopy(self.initial_status()),
                          self.desired_status())
        l.dmsg('xpaths by state:\n' + pprint.pformat(comp.bystate), 6)
        try:
            deps = self.desired_status().xpath('/status/deps')[0]
        except IndexError:
            deps = etree.fromstring('<status><deps/></status>')[0]
        wudeps = comp.wudeps(deps.iterchildren(tag=etree.Element))
        # Track success/failure of work units.
        #
        # Before a work unit is attempted work_status[wu] should not
        # exist.
        #
        # Afterward, work_status[wu] should contain an array with a
        # status (True = succeeded, False = failed) and either the wu
        # element or an error message as appropriate:
        #
        # {
        #  wu1: [True, wu_elt],
        #  wu2: [False, "Worker 'splat' not available"]
        #  wu3: [False, "Dependency 'wu2' failed"]
        # }
        work_status = {}
        # set up a dictionary:
        # { work_unit: [list, of, units, work_unit, depends, on] }
        work_depends = {}
        for dep in wudeps:
            if work_depends.get(dep[1]):
                # entry for dep[1] already exists, add to it
                work_depends.get(dep[1]).append(dep[0])
            else:
                # entry for dep[1] does not exist, create it
                work_depends.set(dep[1], [dep[0]])
        l.dmsg('work_depends = {}'.format(pprint.pformat(work_depends)))
        # we need to make all workunits depend on something for
        # topsort to work
        wudeps.extend([['', x] for x in comp.find_work()])
        l.dmsg('wudeps = {}'.format(pprint.pformat(wudeps)))
        i = 0
        for lev in iter(topsort.topsort_levels(wudeps)):
            i += 1
            if i == 1:
                # this is the fake workunit '' we put in above
                continue
            l.dmsg('xpaths for level {}:\n'.format(i) + pprint.pformat(lev), 6)
            wus, working_elt = generate_wus(set(lev), comp)

            # collect workunits by worker
            byworker = {}
            for wu in wus:
                # check to make sure any dependencies have been done
                check = self.check_deps(wu, work_depends, work_status)
                if not check[0]:
                    work_status.set(
                        wu.get('id'),
                        [False, "Dependency '{}' failed".format(check[1])]
                        )
                    # don't include this wu in work to be done
                    continue
                workername = MRXpath(wu.get('id')).workername(prefix='/status')
                if workername not in byworker:
                    byworker[workername] = E.wus(worker=workername)
                byworker[workername].append(wu)

            # TODO(colin): parallelise downloads and other work

            # start the downloads
#            if 'fetcher' in byworker:
#                workelt = byworker['fetcher']
#                del byworker['fetcher']
#                l.lmsg('invoking fetcher')
#                l.dmsg('fetching:\n' + pstring(workelt))
#                self.process_results(self.worker('fetcher').do_work(workelt),
#                                     workelt, work_depends, work_status)

            # do the work
            for wname, workelt in byworker.items():
                l.lmsg('dispatching to ' + wname)
                l.dmsg('work:\n' + pstring(workelt))
                worker = self.worker(wname)
                if worker:
                    try:
                        results = self.worker(wname).do_work(workelt)
                    except Exception as e:
                        exc_type, exc_value, exc_tb = sys.exc_info()
                        for wu in workelt:
                            work_status[wu.get('id')] = [
                                False,
                                "Exception in worker {}\n{}".format(
                                    wname, str(e)
                                    )
                                ]
                        l.emsg(
                            "Exception from worker {} - failing its work\n{}".format(
                                wname,
                                ''.join(traceback.format_tb(exc_tb)) + repr(e)
                                )
                            )
                    else:
                        self.process_results(
                            results,
                            workelt,
                            work_status
                            )
                else:
                    # No worker: fail this set of work
                    for wu in workelt:
                        work_status[wu.get('id')] = [
                            False,
                            "No worker '{}'".format(wname)
                            ]

        wu_updated_status = copy.deepcopy(self.initial_status())
        # Gather sucesses and failures
        failures = []
        for wid, completed in work_status.items():
            if completed[0]:
                # Apply successes to wu_updated_status
                wu_updated_status = apply_wu(completed[1], wu_updated_status)
            else:
                failures.append([wid, completed[1]])
        # Report failures.
        l.lmsg(
            'The following work units reported failure:\n{}'.format(
                pprint.pformat(failures)
                )
            )
        # write calculated status to file
        fname = os.path.join(context.status_dir(), 'previous-status.xml')
        with open(fname, 'w') as prev:
            prev.write(etree.tostring(
                    wu_updated_status,
                    pretty_print=True
                    ).decode())

        # see how the status has changed including calls to generate_status()
        new_status = self.gather_status()

        # write this status out as previous_status.xml
        with open(fname, 'w') as prev:
            prev.write(etree.tostring(
                    new_status,
                    pretty_print = True
                    ).decode())

    def check_deps(self, wu, work_depends, work_status):
        """Check status of dependencies of a work unit (wu)

        Returns:
          [True] if all dependencies have been done
          [False, dep_id] is any have failed (dep_id is first discovered failure)
          """
        if work_depends.get(wu.get('id')):
            # this work depends on some other work check to
            # see if any have failed
            for dep_id in work_depends.get(wu.get('id')):
                if work_status.get(dep_id) and not work_status.get(dep_id)[0]:
                    return [False, dep_id]
        return [True]


    def initial_status(self):
        """Get the initial status. Will call gather_status() if necessary."""
        if self._initial_status is None:
            l.lmsg('Working out initial status.')
            self._initial_status = self.gather_status()
        return self._initial_status

    def desired_status(self):
        """Get the desired status. Will download and compile status if necessary."""
        if self._desired_status is None:
            services = context.machination_worker_elt.xpath(
                'services/service'
                )
            # TODO download from all services and merge. For now just
            # do the first one.
#            hurl = services[0].xpath('hierarchy/@id')
            service_id = services[0].get('id')
            l.lmsg('Connecting to service "{}"'.format(service_id))
            # find the machination id for this service
            mid = context.get_id(service_id)
            wc = WebClient(service_id, 'os_instance', 'cert')
#            channel = wc.call("ProfChannel", 'os_instance')
            try:
                data = wc.call('GetAssertionList',
                               'os_instance',
                               mid)
            except:
                # couldn't dowload assertions - go with last desireed status
                self._desired_status = copy.deepcopy(
                    context.desired_status.getroot()
                    )
            else:
                # we do have some assertions - compile them
#                pprint.pprint(data)
                ac = AssertionCompiler(wc)
                self._desired_status, res = ac.compile(data)
                # Save as desired-status.xml
                with open(
                    os.path.join(
                        context.status_dir(),
                        'desired-status.xml'
                        ),
                    'w') as ds:
                    ds.write(etree.tostring(
                            self._desired_status,
                            pretty_print=True).decode())

        return self._desired_status

    def load_previous_status(self):
        """Load previous_status.xml"""
        fname = os.path.join(context.status_dir(), 'previous-status.xml')
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

    def previous_status(self):
        """Get the status from the previous run."""
        if self._previous_status is None:
            return self.load_previous_status()
        return self._previous_status

    def gather_status(self):
        """Invoke all workers' generate_status() and gather into one."""
        l.lmsg('Gathering status from workers.')
        status = copy.deepcopy(self.load_previous_status())
        # find all workers
        stelt = status.xpath('/status')[0]
        done = set()
        for welt in status.xpath('/status/worker'):
            # the following should create a worker object and store it
            # in self.workers
            worker = self.worker(welt.get("id"))
            if worker is not None:
                try:
                    wstatus = worker.generate_status()
                except AttributeError:
                    # No generate_status method: leave the previous
                    # status element intact. This will, in effect,
                    # cause the status to be tracked by do_update()
                    # when it writes sucessful changes to
                    # previous_status.xml
                    pass
                else:
                    stelt.remove(welt)
                    stelt.append(wstatus)
            done.add(welt.get('id'))
        for welt in self.desired_status().xpath('/status/worker'):
            if welt.get("id") in done:
                continue
            worker = self.worker(welt.get("id"))
            if worker is not None:
                try:
                    wstatus = worker.generate_status()
                except AttributeError:
                    # No generate_status method: leave previous status
                    # undefined.
                    pass
                else:
                    stelt.append(wstatus)
        return status

    def worker(self, name):
        """Get the worker object for name."""
        if name in self.workers:
            return self.workers[name]

        l.lmsg('Importing {}'.format(name))
        try:
            wmod = importlib.import_module('machination.workers.' + name)
            w = wmod.Worker()
        except ImportError as e:
            if str(e).startswith('No module named '):
                # TODO: assume no python module for this worker,
                # try to find and execute an OL worker
                try:
                    w = OLWorker(name)
                except Exception as eol:
                    l.wmsg("No worker '%s', storing 'None'!" % name)
                    w = None
        except Exception as e:
            exc_type, exc_value, exc_tb = sys.exc_info()
            l.emsg("Failed to start worker '{}', storing 'None'".format(name))
            l.emsg('Traceback:\n{}'.format(
                    ''.join(traceback.format_tb(exc_tb)) + repr(e)
                    )
                   )
            w = None
        self.workers[name] = w
        if w:
            l.lmsg('Worker {} imported'.format(name))
        return w

    def process_results(self, res, workelt, work_status):
        for ru in res:
            if ru.get("status") == "success":
                wu = workelt.xpath('wu[@id="{}"]'.format(ru.get('id')))[0]
                work_status[ru.get('id')] = [True, wu]
            else:
                work_status[ru.get('id')] = [False, ru.get('message')]

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
    parser.add_argument(
        '--get_desired', '-g', action = 'store_true',
        help='Download and compile desired status, then exit.'
        )
    parser.add_argument(
        '--logging', '-l', action = 'append',
        help='Specify extra logging elements, eg: <stream id="stdout" loglevel="6"/>'
        )
    parser.add_argument('--desired', '-d', nargs='?',
                        help='desired status file')
    parser.add_argument('--desired_xpath', '-dx', nargs='?',
                        help='xpath of status in desired status file')
    parser.add_argument('--initial', '-i', nargs='?',
                        help='initial status file')
    parser.add_argument('--initial_xpath', '-ix', nargs='?',
                        help='xpath of status in initial status file')

    args = parser.parse_args()
    
    if args.logging is None:
        args.logging = []
    for eltstr in args.logging:
        l.add_destination(etree.fromstring(eltstr))
        l.lmsg('added log destination {}'.format(eltstr))

    if args.get_desired:
        u = Update()
        print(
            etree.tostring(
                u.desired_status(),
                pretty_print = True
                ).decode()
            )
        sys.exit()

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
