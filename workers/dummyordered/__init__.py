#!/usr/bin/python

"A test worker which relies on the order of elements in its XML"

from lxml import etree
from machination import context
import os
import errno

class worker(object):
    "Test of order preservation"

    def __init__(self):
        self.desired = context.desired_status.xpath("/status/worker[@id='dummyordered']")[0]

    def generate_status(self):
        w_elt = etree.Element("worker")
        w_elt.set("id","dummyordered")

        # <sysitem> elements first from pretend_db
        pdb = pretend_db()
        cur_id = pdb.get_next(None)
        while cur_id != pdb.endstr:
            text, next = pdb.get_contents(cur_id)
            item_elt = etree.Element("sysitem")
            item_elt.set("id", cur_id)
            item_elt.text = text
            w_elt.append(item_elt)
            cur_id = next

        # get to_file element by converting from pretend_config

        # notordered from existence testing on some files

        return w_elt

    def do_work(self,wus):
        pass

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
            self.path = "/tmp/machination/dummyordered/file.conf"
        else:
            self.path = path

    def to_xml(self):
        elt = etree.Element("tofile")
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
            
        
