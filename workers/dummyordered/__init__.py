#!/usr/bin/python

"A test worker which relies on the order of elements in its XML"

from lxml import etree
from machination import context
import os
import errno

class worker():
    "Test of order preservation"

    def __init__(self):
        self.desired = context.desired_status.xpath("/status/worker[@id='dummyordered']")[0]

    def generate_status(self):
        pass

    def do_work(self,wus):
        pass
        

class pretend_db():
    "where the ordered sysitems go"

    def __init__(self):
        self.dir = "/tmp/pdb"
        self.counter = os.path.join(self.dir, "counter")
        self.start = os.path.join(self.dir, "start")
        try:
            os.makedirs(self.dir)
            # new db, initialise counter and start ref
            self.clear()
        except OSError, e:
            if e.errno != errno.EEXIST:
                raise

    def clear(self):
        with open(self.counter, "w") as c:
            c.write("1\n")
        try:
            os.remove(self.start)
        except OSError, e:
            # errno.ENOENT means file does not exist
            if e.errno != errno.ENOENT:
                raise

    def get_id(self):
        # there is a race condition here, but we aren't trying to be
        # clever
        with open(self.counter, "r+") as c:
            cid = c.readline()

    def append(self,text):
        
