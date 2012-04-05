#!/usr/bin/python

"A test worker which relies on the order of elements in its XML"

from lxml import etree
from machination import context
import os, shutil
import errno

class worker(object):
    """Test of order preservation

    This worker is designed to illustrate the various ways in which a
    worker might need to care about ordering of elements in its status
    and how one might deal with them.

    example status:
    .. code-block:: xml
      <status>
        <sysitem id="a">atext</sysitem>
        <sysitem id="b">btext</sysitem>
        <tofile>
          <directive>something</directive>
          <item id="a">atext</item>
          <item id="b">btext</item>
        </tofile>
        <notordered id="a">atext</notordered>
        <notordered id="a">btext</notordered>
      </status>

    #. XML represents a configuration file.

       Illustrated by contents of <tofile> element

       In this case the XML in some part of status represents a
       configuration file or perhaps some other entity that will be
       constructed in its entirety each time from the XML. Most
       configuration information in UNIX-like systems is changed this
       way.

       In do_work() the strategy is to apply all wuwus and make sure
       the resultant working status Element is correct. Then we
       translate to the target file format and write out the results.

       ``utils.apply_wus(wulist,start_status,desired_status)`` will
       take care of updating the XML.

    #. System settings altered via an API.

       Illustrated by <sysitem> elements.

       Here we imagine that some system settings are to be altered via
       an API of some kind. Most configuration information in Windows
       is changed this way for example (usually via WMI or some other
       COM interface).

       In this case we can't consume all wuwus to construct our
       working status Element first and then alter the system. Often
       when making those external API calls we'll need to know things
       like which list index a new item is to be inserted at, which id
       it should be inserted after or where it should be re-ordered
       to. There are functions in utils which will tell us this
       information if we are careful to update a working status
       Element in lock step with performing actions on the system.

       ``utils.apply_wu(wu, current_status, desired_status)`` may be
       called each time an action is performed to track the system
       status. If this is unreliable or if ``generate_status()`` is
       cheap for your worker an alternative is to
       ``generate_status()`` after each action instead of tracking
       changes.

    #. A subsection or tag where ordering isn't actually important.

       Illustrated by <notordered> elements

       A worker whose description file says it preserves order in its
       description file must preserve order throughout its status or
       else risk being invoked by update with extraneous wuwus.

       Imagine that this worker also maintains some configuration
       where order is not important. We should take care to reorder
       our status report to result in least work - i.e. to look as
       much like desired status as possible.

       ``utils.order_as(our_status, template_status)`` will do that
       for us, placing every element that exists in both our_status
       and template_status in the same order as template_status and
       placing any elements in our_status but not template_status at
       the end.

    """

    def __init__(self, datadir = None):
        self.desired = context.desired_status.xpath("/status/worker[@id='dummyordered']")[0]
        if datadir:
            self.datadir = datadir
        else:
            self.datadir = os.path.join(context.cache_dir(),"dummyordered")

    def generate_status(self):
        w_elt = etree.Element("worker")
        w_elt.set("id","dummyordered")

        # <sysitem> elements first from pretend_db
        pdb = pretend_db(os.path.join(self.datadir, "pdb"))
        cur_id = pdb.get_next(None)
        while cur_id != pdb.endstr:
            text, next = pdb.get_contents(cur_id)
            item_elt = etree.Element("sysitem")
            item_elt.set("id", cur_id)
            item_elt.text = text
            w_elt.append(item_elt)
            cur_id = next

        # get tofile element by converting from pretend_config
        pc = pretend_config(os.path.join(self.datadir),"conf.txt")
        w_elt.append(pc.to_xml())

        # notordered from contents of some files
        fpath = os.path.join(self.datadir, "files")
        dic = {}
        for f in os.listdir(fpath):
            with open(os.path.join(fpath,f)) as fd:
                dic[f] = fd.readline().rstrip("\r\n")
        for key in sorted(dic.iterkeys()):
            no_elt = w_elt.SubElement("notordered")
            no_elt.set("id", key)
            no_elt.text = dic[key]

        return w_elt

    def do_work(self,wus):
        pass

    # methods to manipulate the status outside of do_work for testing
    # purposes

    def clear_data(self):
        shutil.rmtree(self.datadir)

    def set_status(self):


class pretend_config(object):
    """adaptor to a pretend config file format::

      directive:something
      [items]
      id1:text1
      id2:text2
      ...
    """

    def __init__(self, path = None):
        if path is None:
            self.path = "/tmp/machination/dummyordered/conf.txt"
        else:
            self.path = path

    def to_xml(self):
        elt = etree.Element("tofile")
        try:
            with open(self.path, "r") as f:
                directive = f.readline().split(":")[1].rstrip("\r\n")
                delt = etree.Element("directive")
                elt.append(delt)
                delt.text = directive
                f.readline() # [items]
                line = f.readline()
                while line != '':
                    itid, text = line.rstrip("\r\n").split(":")
                    item_elt = etree.SubElement(elt, "item")
                    item_elt.set("id",itid)
                    item_elt.text = text
                    line = f.readline()
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
        return elt

    def from_xml(self, elt):
        delt = elt.xpath("directive")[0]
        items = elt.xpath("item")
        with open(self.path, "w") as f:
            f.write("directive:" + delt.text + "\n")
            f.write("[items]\n")
            for item in items:
                f.write("{}:{}".format(item.get("id"),item.text))

class pretend_db(object):
    "a pretend database where the the items 'sysitem' elements represent go"

    def __init__(self, directory = None):
        if directory is None:
            self.dir = "/tmp/machination/dummyordered/pdb"
        else:
            self.dir = directory
        self.datadir = os.path.join(self.dir, "data")
        self.counter = os.path.join(self.dir, "counter")
        self.start = os.path.join(self.dir, "start")
        self.endstr = "::END::"
        try:
            os.makedirs(self.datadir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def clear(self):
        for f in os.listdir(self.datadir):
            os.unlink(os.path.join(self.datadir,f))
        try:
            os.remove(self.start)
        except OSError as e:
            # errno.ENOENT means file does not exist
            if e.errno != errno.ENOENT:
                raise

    def get_id(self):
        # there is a race condition here, but we aren't trying to be
        # clever so we won't bother with locking
        with open(self.counter, "r+") as c:
            cid = int(c.readline())
            c.seek(0)
            c.truncate()
            c.write(str(cid+1)+"\n")
        return str(cid)

    def get_start(self):
        try:
            with open(self.start, "r") as s:
                return s.readline().rstrip("\r\n")
        except IOError as e:
            if e.errno == errno.ENOENT:
                # no start yet
                return self.endstr

    def get_contents(self, anid):
        with open(os.path.join(self.datadir,str(anid))) as f:
            text = f.readline().rstrip("\r\n")
            next = f.readline().rstrip("\r\n")
        return text, next

    def get_next(self, cur_id):
        if cur_id is None:
            # get the start
            return self.get_start()
        text, next = self.get_contents(cur_id)
        return next

    def get_end(self):
        cur_id = self.get_start()
        if cur_id is self.endstr:
            return None
        last_id = cur_id
        while cur_id != self.endstr:
            cur_id = self.get_next(cur_id)
            if cur_id != self.endstr:
                last_id = cur_id
        return last_id

    def change_tail(self,eid,newnext):
        if eid is None:
            # change the start file
            with open(self.start,"w") as s:
                s.write(newnext + "\n")
        else:
            text, next = self.get_contents(eid)
            with open(os.path.join(self.datadir, eid), "w") as p:
                p.write(text + "\n")
                p.write(newnext + "\n")

    def create_elt(self,text,next):
        newid = self.get_id()
        self.write_elt(newid, text, next)
        return newid

    def write_elt(self,eid,text,next):
        with open(os.path.join(self.datadir,eid),"w") as f:
            f.write(text + "\n")
            f.write(next + "\n")

    def id_exists(self, eid):
        return os.path.exists(os.path.join(self.datadir, eid))

    def insert_after(self, myid, afterid, text):
        if self.id_exists(myid):
            raise Exception("cannot insert an id that already exists (%s)" % myid)
        self.write_elt(myid, text, self.get_next(afterid))
        self.change_tail(afterid, myid)

    def append(self, myid, text):
        self.insert_after(myid, self.get_end(), text)

    def prepend(self, myid, text):
        self.insert_after(myid, None, text)

    def index_of(self, eid):
        index = 0
        cur_id = self.get_start()
        while cur_id != eid:
            cur_id = self.get_next(cur_id)
            if cur_id == self.endstr:
                # uh oh - run out of list
                raise Exception("ran off end of list at index %d looking for %s" % (index,eid))
            index = index + 1
        return index

    def id_at_index(self, index):
        theid = None
        for i in range(index + 1):
            theid = self.get_next(theid)
            if theid == self.endstr:
                raise Exception("ran off the end of the list")
        return theid
            
        
