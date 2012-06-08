#!/usr/bin/python

"""Run a Machination update cycle

"""

import sys
import itertools
from machination import utils, xmltools, fetcher, hierarchy, context
import topsort
from lxml import etree

workers = {}


class OLWorker:

    def __init__(self, wid):
        self.wid = wid
        self.progdir = context.config.xpath("/config/workers")[0].get("progdir")
        for f in os.listdir(self.progdir):
            if f == wid or f.startswith(wid + "."):
                self.progfile = f
                self.progpath = os.path.join(self.progdir, self.progfile)
                break
        if self.progfile == None:
            raise Exception("No worker named " + wid)

    def generate_status(self):
        pass

    def do_work(self, wus):
        pass


def main(args):
    # initialise from config
    logger = context.logger

    # get config assertions and compile into desired_status.xml
    ca_list = hierarchy.fetch_calist()
    dst_elt = hierarchy.compile_calist(ca_list)

    cst_elt = generate_base_status()
    # workers: generate_status
    for welt in dst_elt.xpath("/status/worker"):
        w = get_worker(welt)
        wcst_elt = w.generate_status()
        # workers might not implement generate_status() - better be
        # prepared for no status
        if wcst_elt == None:
            wcst_elt = get_previous_status(welt.get("id"))

        # stitch them together into a big status document for later
        # comparison
        cst_elt.append(wcst_elt)

    # find work
    xmlcmp = xmltools.XMLCompare(dst_elt, cst_elt, workerdesc)
    xmlcmp.compare()
    xmlcmp.find_work()
    stdeps = dst_elt.xpath("/status/deps/dep")
    wudeps = xmlcmp.dependencies_state_to_wu(stdeps, xmlcmp.worklist, xmlcmp.byxpath)
    first = True
    previous_failures = set()
    for i_workset in iter(topsort.topsort_levels(wudeps)):
        # wuwus within an 'i_workset' are independent of each other

        # wuwus that aren't mentioned in wudeps should be in the
        # first i_workset
        if first:
            first = False
            i_workset = i_workset.union(find_nodeps(xmlcmp.worklist, wudeps))

        # fetcher: downloads and workers: do_work
        # parallelisation perhaps?
        results = spawn_work(parcel_work(i_workset, previous_failures))

        # mark any failures
        previous_failures = previous_failures.union(results.failures())

    # gather resultant_status


def spawn_work(parcels):
    """Take a work parcels dictionary and do the work"""
    for workername in parcels:
        workerdesc = xmltools.WorkerDescription(os.path.join(context.status_dir(), "workers", workername, "description.xml"))

        # if the worker is ordered:
        # get copy of worker's current status (working_status)
        # apply removes and mods to working status
        # copy final desired_status to cur_des_status
        # loop over siblings at wu level in cur_des_status:
          # if sibling not in cur_des_st and is not to be added:
            # drop from cur_des_st
          # if sibling not in cur_des_st but is to be added:
            # find position arg for add
          # if sibling in both but wrong position:
            # find correct move/reorder instruction


def get_worker(welt):
    wid = welt.get("id")
    if wid in workers:
        return workers[wid]

    try:
        w = __import__("workers." + wid)
    except ImportError as e:
        if e.message.startswith('No module named '):
            # TODO: assume no python module for this worker,
            # try to find and execute an OL worker
            try:
                w = OLWorker(wid)
            except Exception:
                logger.emsg("No worker %s, giving up!" % wid)
                raise


def generate_base_status():
    elt = etree.Element("status")
    return elt


if __name__ == '__main__':
    main(sys.argv[1:])
