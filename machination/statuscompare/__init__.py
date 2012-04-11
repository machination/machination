#!/usr/bin/python
# vim: set fileencoding=utf-8:

"""A machination module to calculate the difference between profile and status.

Machination (and its workers) will call this library to ask for a 'worklist'
based on differences between the 'local' status.xml and the downloaded profile.

"""

from lxml import etree
from machination import workerdescription
from machination import xmltools


class XMLCompare(object):
    """Compare two etree Elements and store the results"""

    def __init__(self, leftxml, rightxml, workerdesc):
        """XMLCompare constructor

        Args:
          leftxml: an etree Element
          rightxml: an etree Element
          workerdesc: passed to the WorkerDescription constructor
        """
        self.leftxml = leftxml
        self.rightxml = rightxml
        self.leftset = set()
        self.rightset = set()
        self.bystate = {'left': set(),
                        'right': set(),
                        'datadiff': set(),
                        'childdiff': set()}
        self.byxpath = {}
        self.worklist = set()
        self.wd = workerdescription.WorkerDescription(workerdesc)
        self.diff_to_action = {
            'left': 'remove',
            'right': 'add',
            'datadiff': 'modify',
            'childdiff': 'modify'
            }

        self.compare()

    def action_list(self):
        """return list of (xpath, action) tuples"""
        return [(xpath, self.diff_to_action[self.bystate[xpath] for xpath in self.worklist])]

    def compare(self):
        """Compare the xpath sets and generate a diff dict"""

        for elt in self.leftxml.iter():
            self.leftset.add(mrxpath(elt).to_xpath())
        for elt in self.rightxml.iter():
            self.rightset.add(mrxpath(elt).to_xpath())

        for xpath in self.leftset.difference(self.rightset):
            self.bystate['left'].add(xpath)
            self.byxpath[xpath] = 'left'

        for xpath in self.rightset.difference(self.leftset):
            self.bystate['right'].add(xpath)
            self.byxpath[xpath] = 'right'

        self.find_diffs(self.leftset.intersection(self.rightset))
        self.find_work()

    def find_diffs(self, xpathlist):
        """Find differing values in the intersection set"""

        for xpath in xpathlist:
            l = self.leftxml.xpath(xpath)
            r = self.rightxml.xpath(xpath)

            # l[0] or r[0] can be element objects, or attr strings
            # Try to get the text - if it fails, its an attribute
            lval = ""
            rval = ""

            try:
                lval = l[0].text
                rval = r[0].text
            except AttributeError:
                lval = l[0]
                rval = r[0]

            if lval != rval:
                self.bystate['datadiff'].add(xpath)
                self.byxpath[xpath] = 'datadiff'
                for a in xmltools.mrxpath(xpath).ancestors():
                    self.bystate['childdiff'].add(a.to_xpath())
                    self.byxpath[a.to_xpath()] = 'childdiff'

    def find_work(self):
        """Check which xpaths are work_units and return these."""

        for xpath in self.bystate['datadiff'] | self.bystate['left'] | self.bystate['right']:
            if self.wd.is_workunit(xpath):
                self.worklist.add(xpath)
            else:
                parent = self.find_parent_workunit(xpath)
                self.worklist.add(parent)

    def find_parent_workunit(self, xpath):
        """Recurse up an xpath, return the first parent that is a workunit."""

        mrx = mrxpath(xpath)
        pmrx = mrx.parent()
        if pmrx:
            parentxpath = pmrx.to_xpath()

        if self.wd.is_workunit(parentxpath):
            return parentxpath

        else:
            if parentxpath:
                return self.find_parent_workunit(parentxpath)
            else:
                raise Exception("No work unit ancestors found!")
                pass

    def dependencies_state_to_wu(self, deps, worklist, byxpath):
        """Combine state dependencies with worklist to find work dependencies.

        deps: an iterable of lxml ``Element``s from the profile. These
        should be in the form:

        .. code-block:: xml
          <dep id="something"
               src="/some/xpath"
               op="requires|excludes"
               tgt="/some/other/xpath"/>

        worklist: set of workunit xpaths as returned by ``find_work``

        byxpath: the byxpath index generated by ``compare``

        returns: a list (set?, iterable?) of dependencies between work
        units::

          [[wuA, wuB], [wuB, wuC], [wuD, wuE], ...]

        meaning workunit ``wuA`` depends on ``wuB``, ``wuB`` depends
        on ``wuC`` and so on. This output should be suitable for a
        (yet to be chosen or implemented) topological sort and may
        change later depending on implementation choice.
        """
        for sdep in deps:
            # build a list of deps for topological sort just now
            # might change to generator approach later
            topdeps = []

            # translate src and tgt state xpaths to wu xpaths
            src_wu = self.find_parent_workunit(sdep.get("src"))
            tgt_wu = self.find_parent_workunit(sdep.get("tgt"))

            # find intended work operation for both wus
            if src_wu in byxpath:
                src_action = self.diff_to_action[byxpath[src_wu]]
            else:
                src_action = "none"
            if tgt_wu in byxpath:
                tgt_action = self.diff_to_action[byxpath[tgt_wu]]
            else:
                tgt_action = "none"

            # get to one of [src, tgt], [tgt, src] or nothing

            if sdep.get("op") == "requires":
                if src_action == "add" or src_action == "modify":

                    # tgt_action better be add, modify or none
                    if tgt_action == "remove":
                        raise Exception(sdep.get("src") +
                                        " requires " +
                                        sdep.get("tgt") +
                                        " which will be removed")

                    if tgt_action == "none":
                        # we must assume the target xpath is there already
                        # TODO?: really check the state
                        continue

                    # tgt_action must now be add or modify
                    # src_action deps tgt_action
                    topdeps.append([sdep.get("src"), sdep.get("tgt")])

                elif src_action == "remove" and tgt_action == "remove":
                    topdeps.append([sdep.get("tgt"), spep.get("src")])

                else:
                    # src_action == remove and tgt_action != remove
                    # OR src_action == none
                    continue

            elif sdep.get("op") == "excludes":
                if src_action == "add" or src_action == "modify":

                    # tgt_action better be remove or none
                    if tgt_action == "add" or tgt_action == "modify":
                        raise Exception(sdep.get("src") +
                                        " excludes " +
                                        sdep.get("tgt") +
                                        " which will still exist")

                    if tgt_action == "none":
                        # we must assume the target xpath is not there
                        # TODO?: really check the state
                        continue

                    # tgt_action must now be remove
                    # src_action deps tgt_action
                    topdeps.append([sdep.get("src"), sdep.get("tgt")])

                elif src_action == "remove":
                    if tgt_action == "add":
                        # tgt_action deps src_action
                        topdeps.append([sdep.get("tgt"), spep.get("src")])

                else:
                    # src_action == none
                    continue

            else:
                raise Exception("Don't understand dependency op '%s'"
                                % sdep.get("op"))

        return topdeps


if __name__ == "__main__":

    import sys
    import pprint
    pp = pprint.PrettyPrinter()

    leftfile = sys.argv[1]
    rightfile = sys.argv[2]
    descfile = sys.argv[3]

    leftxml = etree.parse(leftfile)
    rightxml = etree.parse(rightfile)

    xmlcmp = XMLCompare(leftxml, rightxml, descfile)
    pp.pprint(xmlcmp.byxpath)
    pp.pprint(xmlcmp.worklist)
