"""Do a machination update"""

from machination import context
from machination.xmltools import XMLCompare
from machination.xmltools import MRXpath
from machination import utils
from lxml import etree
from lxml.builder import E
import copy
import topsort

class Update(object):

    def __init__(self, initial_status = None, desired_status = None):
        self.workers = {}
        self._initial_status = initial_status
        self._desired_status = desired_status

    def do_update(self):
        comp = XMLCompare(copy.deepcopy(self.initial_status()),
                          self.desired_status())
        deps = self.desired_status.xpath('/status/deps')[0]
        wudeps = comp.wudeps(deps.iterchildren(etree.Element))
        wudeps.extend([['', x] for x in comp.find_work()])
        i = 0
        for lev in iter(topsort.topsort_levels(wudeps)):
            if i == 0:
                i += 1
                continue
            wus, working_elt = generate_wus(set(lev), comp)
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
        if self._initial_status is None:
            self._initial_status = self.gather_status()
        return self._initial_status

    def desired_status(self):
        if self._desired_status is None:
            pass
        return self._desired_status

    def previous_status(self):
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
        status = copy.deepcopy(self.previous_status())
        # find all workers
        stelt = welt.xpath('/status')[0]
        for welt in status.xpath('/status/worker'):
            # the following should create a worker object and store it
            # in self.workers
            wstatus = self.worker(welt.get("id")).generate_status()
            stelt.remove(welt)
            stelt.append(wstatus)
        for welt in self.desired_status().xpath('/status/worker'):
            if welt.get("id") in workers:
                continue
            wstatus = self.worker(welt.get("id")).generate_status()
            stelt.append(wstatus)

    def worker(self, name):
        if name in self.workers:
            return self.workers[name]

        try:
            w = __import__('machination.workers.' + name)
        except ImportError as e:
            if e.message.startswith('No module named '):
                # TODO: assume no python module for this worker,
                # try to find and execute an OL worker
                try:
                    w = OLWorker(name)
                    logger.emsg("No worker %s, giving up!" % name)
                    raise
        self.workers[name] = w

class OLWorker(object):

    def __init__(self, wid):
        self.wid = wid
        self.progdir = utils.worker_dir(wid)
        for f in os.listdir(self.progdir):
            if f == wid or f.startswith(wid + "."):
                self.progfile = f
                self.progpath = os.path.join(self.progdir, self.progfile)
                break
        if self.progfile == None:
            raise Exception("No worker named " + wid)

    def generate_status(self):
        pass

    def do_work(self,wus):
        pass

def main(args):
    # TODO: parse command line args and options?
    Update().do_update()

if __name__ == '__main__':
    main(sys.argv[1:])
