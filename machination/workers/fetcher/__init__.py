"Wraps the fetcher in a worker"

from lxml import etree
from machination import context
from machination import xmltools
import os
import errno
import sys


class Worker(object):
    """Fetch tagged bundles from sources defined in config

    """

    def __init__(self):
        self.name = self.__module__.split('.')[-1]
        self.wd = xmltools.WorkerDescription(self.name,
                                             prefix='/status')
        self.config_elt = self.read_config()

    def read_config(self):
        config_file = os.path.join(context.conf_dir(), "fetcher.xml")
        try:
            c_elt = etree.Parse(config_file)
        except IOError as e:
            c_elt = etree.Element("config")
        return c_elt

    def write_config(self):
        config_file = os.path.join(context.conf_dir(), "fetcher.xml")
        with open(config_file, 'w') as c:
            c.write(etree.tostring(self.config_elt,
                                   pretty_print=True)
                   )

    def do_work(self, work_list):
        "Process the work units and return their status."
        result = []
        flag = False
        pref = "/status/worker[@id='fetcher']"
        confcheck = ''.join(pref, "/config")
        for wu in work_list:
            if wu.attrib["id"].startswith(confcheck):
                xmltools.apply_wu(wu,
                                  self.config_elt,
                                  strip=pref)
                flag = True
                res = etree.Element("wu",
                                    id=work.wu.attrib["id"]
                                    status="success")
            else:
                operator = "__{}".format(wu.attrib["op"])
                res = getattr(self, operator)(wu)
            result.append(res)

        # Finished all work. Write config file if changed
        if flag:
            self.write_config()

        return result

    def __add(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res

    def __remove(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res

    def __move(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res

    def __datamod(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res

    def __deepmod(self, work):
        res = etree.Element("wu",
                            id=work.attrib["id"])
        res.attrib["status"] = success
        return res



    def generate_status(self):
        w_elt = etree.Element("worker")
        w_elt.set("id", self.name)

        return w_elt

    def do_work(self, wus):
        results = []
