"A test worker which relies on the order of elements in its XML"

from lxml import etree
from machination import context
from machination import xmltools
import os
import shutil
import errno


class Worker(object):
    """Test of order preservation

    This worker is designed to illustrate the various ways in which a
    worker might need to care about ordering of elements in its status
    and how one might deal with them.

    example status:
    .. code-block:: xml
      <status>
      <worker id="dummyordered">
        <sysitem id="a">atext</sysitem>
        <sysitem id="b">btext</sysitem>
        <tofile>
          <directive>something</directive>
          <item id="a">atext</item>
          <item id="b">btext</item>
        </tofile>
        <notordered id="a">atext</notordered>
        <notordered id="a">btext</notordered>
      </worker>
      </status>

    #. XML represents a configuration file.

       Illustrated by contents of <iniFile> element

       In this case the XML in some part of status represents a
       configuration file or perhaps some other entity that will be
       constructed in its entirety each time from the XML. Most
       configuration information in UNIX-like systems is changed this
       way.

       The preferred strategy is to mark ``iniFile`` as a work
       unit. Changes anywhere under the ``iniFile`` element will be
       sent as a 'deepmod' wu for the whole of ``iniFile``. Just
       translate to the target file format and write out the results.

    #. System settings altered via an API.

       Illustrated by <sysitem> elements.

       Here we imagine that some system settings are to be altered via
       an API of some kind. Most configuration information in Windows
       is changed this way for example (usually via WMI or some other
       COM interface).

       In this case we can't consume all wus to construct our
       working status Element first and then alter the system, we must
       alter the system directly as we evaluate each work unit. Most
       of the time this is fine - just do the work in order and
       (possibly) ``generate_status()`` at the end to make sure the
       new state is fine.

    #. A subsection or tag where ordering isn't actually important.

       Illustrated by <notordered> elements

       A worker whose description file says it preserves order in its
       description file must preserve order throughout its status or
       else risk being invoked by update with extraneous wuwus.

       Imagine that this worker also maintains some configuration
       where order is not important. We should take care to reorder
       our status report to result in least work - i.e. to look as
       much like desired status as possible.

       ``status.order_like(template_status)`` will do that
       for us, placing every element that exists in both status.status
       and template_status in the same order as template_status and
       placing any elements in status.status but not template_status at
       the end.

       An optional MRXpath argument allows for ordering branches of
       the XML tree.

    """

    def __init__(self, datadir=None):
        if datadir:
            self.datadir = datadir
        else:
            self.datadir = os.path.join(context.cache_dir(),
                                        'workers',
                                        'dummyordered')
        self.wd = xmltools.WorkerDescription("dummyordered",
                                             prefix='/status')
        self.pdb = pretend_db(os.path.join(self.datadir, "pdb"))
        self.pc = pretend_config(os.path.join(self.datadir, "conf.txt"))

        self.dispatch = {
            '/status/worker/sysitem': self.handle_ordered,
            '/status/worker/tofile': self.handle_file,
            '/status/worker/notordered': self.handle_notordered,
            }

    def generate_status(self):
        w_elt = etree.Element("worker")
        w_elt.set("id", "dummyordered")

        # <sysitem> elements first from pretend_db
        cur_id = self.pdb.get_next(None)
        while cur_id != self.pdb.endstr:
            text, next = self.pdb.get_contents(cur_id)
            item_elt = etree.Element("sysitem")
            item_elt.set("id", cur_id)
            item_elt.text = text
            w_elt.append(item_elt)
            cur_id = next

        # get tofile element by converting from pretend_config
        w_elt.append(self.pc.to_xml())

        # notordered from contents of some files
        fpath = os.path.join(self.datadir, "files")
        dic = {}
        try:
            for f in os.listdir(fpath):
                with open(os.path.join(fpath, f)) as fd:
                    dic[f] = fd.readline().rstrip("\r\n")
        except OSError as e:
            pass

        for key in dic:
            no_elt = etree.SubElement(w_elt, "notordered")
            no_elt.set("id", key)
            no_elt.text = dic[key]

        return w_elt

    def do_work(self, wus):
        results = []
        for wu in wus:
            wmrx = xmltools.MRXpath(wu.get('id'))
#            print()
#            print("dispatching:\n" +
#                  xmltools.pstring(wu))
            self.dispatch.get(wmrx.to_noid_path(), self.handle_default)(wu)

    def handle_default(self, wu):
        if xmltools.MRXpath(wu.get('id')).name() == 'worker':
            return
        raise Exception(wu.get('id') + " is not a valid work unit for worker 'dummyordered'")

    def handle_ordered(self, wu):
        op = wu.get('op')
        elt_id = xmltools.MRXpath(wu.get('id')).id()
        pos_id = wu.get('pos')
        if pos_id == '<first>':
            pos_id = None
        else:
            pos_id = xmltools.MRXpath(pos_id).id()

        if op == 'add':
            self.pdb.insert_after(elt_id, pos_id, wu[0].text)
        elif op == 'remove':
            self.pdb.remove_elt(elt_id)
        elif op == 'datamod':
            self.pdb.modify_elt(elt_id, wu[0].text)
        else:
            raise Exception('op "%s" not supported for sysitem' % op)

    def handle_file(self, wu):
        if wu.get('op') == 'remove':
            pass
        else:
            self.pc.from_xml(wu[0])

    def handle_notordered(self, wu):
        op = wu.get('op')
        fname = xmltools.MRXpath(wu.get('id')).id()
        if op == 'add' or op == 'datamod':
            with open(os.path.join(self.datadir, "files", fname), "w") as f:
                f.write(wu[0].text + "\n")
        elif op == 'remove':
            os.unlink(os.path.join(self.datadir, 'files', fname))
        else:
            raise Exception('op %s no supported for notordered' % op)

    # methods to manipulate the status outside of do_work for testing
    # purposes

    def clear_data(self):
        try:
            shutil.rmtree(self.datadir)
        except OSError as e:
            if e.errno != errno.ENOENT:
                raise

    def set_status(self, status):
        # make sure we start from scratch
        self.clear_data()

        # create our data directory
        try:
            os.makedirs(self.datadir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

        # fill the database
#        pdb = pretend_db(os.path.join(self.datadir, "pdb"))
        self.pdb.init_datadir()
        for item in status.xpath("sysitem"):
            # always append since we start from empty
            self.pdb.append(item.get("id"), item.text)

        # create the conf file
#        pcfg = pretend_config(os.path.join(self.datadir,"conf.txt"))
        if status.xpath('tofile'):
            self.pc.from_xml(status.xpath("tofile")[0])

        # create the unordered files
        os.makedirs(os.path.join(self.datadir, "files"))
        for elt in status.xpath("notordered"):
            with open(os.path.join(self.datadir, "files", elt.get("id")), "w") as f:
                f.write(elt.text + "\n")


class pretend_config(object):
    """adaptor to a pretend config file format::

      directive:something
      [items]
      id1:text1
      id2:text2
      ...
    """

    def __init__(self, path=None):
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
                f.readline()  # [items]
                line = f.readline()
                while line != '':
                    itid, text = line.rstrip("\r\n").split(":")
                    item_elt = etree.SubElement(elt, "item")
                    item_elt.set("id", itid)
                    item_elt.text = text
                    line = f.readline()
        except IOError as e:
            if e.errno != errno.ENOENT:
                raise
        return elt

    def from_xml(self, elt):
        delt = elt.xpath("directive")
        items = elt.xpath("item")
        with open(self.path, "w") as f:
            if delt:
                f.write("directive:" + delt[0].text + "\n")
            f.write("[items]\n")
            for item in items:
                f.write("{}:{}\n".format(item.get("id"), item.text))


class pretend_db(object):
    "a pretend database where the the items 'sysitem' elements represent go"

    def __init__(self, directory=None):
        if directory is None:
            self.dir = "/tmp/machination/dummyordered/pdb"
        else:
            self.dir = directory
        self.datadir = os.path.join(self.dir, "data")
        self.counter = os.path.join(self.dir, "counter")
        self.start = os.path.join(self.dir, "start")
        self.endstr = "::END::"
        self.init_datadir()

    def init_datadir(self):
        try:
            os.makedirs(self.datadir)
        except OSError as e:
            if e.errno != errno.EEXIST:
                raise

    def clear(self):
        for f in os.listdir(self.datadir):
            os.unlink(os.path.join(self.datadir, f))
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
            c.write(str(cid + 1) + "\n")
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
        with open(os.path.join(self.datadir, str(anid))) as f:
            text = f.readline().rstrip("\r\n")
            next = f.readline().rstrip("\r\n")
        return text, next

    def get_next(self, cur_id):
        if cur_id is None:
            # get the start
            return self.get_start()
        text, next = self.get_contents(cur_id)
        return next

    def get_previous(self, eid):
        cur_id = self.get_start()
        if cur_id == eid:
            # eid is at the start
            return None
        while cur_id != self.endstr:
            next_id = self.get_next(cur_id)
            if next_id == eid:
                return cur_id
        raise KeyError('Could not find previous for key "%s"' % eid)

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

    def change_tail(self, eid, newnext):
        if eid is None:
            # change the start file
            with open(self.start, "w") as s:
                s.write(newnext + "\n")
        else:
            text, next = self.get_contents(eid)
            with open(os.path.join(self.datadir, eid), "w") as p:
                p.write(text + "\n")
                p.write(newnext + "\n")

    def create_elt(self, text, next):
        newid = self.get_id()
        self.write_elt(newid, text, next)
        return newid

    def write_elt(self, eid, text, next):
        with open(os.path.join(self.datadir, eid), "w") as f:
            f.write(text + "\n")
            f.write(next + "\n")

    def remove_elt(self, eid):
        prev_elt = self.get_previous(eid)
        self.change_tail(self.get_previous(eid), self.get_next(eid))
        os.unlink(os.path.join(self.datadir, eid))

    def modify_elt(self, eid, text):
        self.write_elt(eid, text, self.get_next(eid))

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
                raise Exception("ran off end of list at index %d looking for %s" % (index, eid))
            index = index + 1
        return index

    def id_at_index(self, index):
        theid = None
        for i in range(index + 1):
            theid = self.get_next(theid)
            if theid == self.endstr:
                raise Exception("ran off the end of the list")
        return theid


#worker = Worker()
#
#def generate_status():
#    return worker.generate_status()
#
#def do_work(wus):
#    return worker.do_work(wus)
