"""Worker description file handling"""
from lxml import etree
from machination import context
from machination.xmltools import MRXpath
import os
import errno


class WorkerDescription:
    """Work with worker description files

    SYNOPSIS:

    wd = WorkerDescription(description)

    or

    wd = WorkerDescription()
    wd.load(description)

    dict_keys = wd.workunits()
    bool = wd.is_workunit(xpath)

    hint_dict = wd.gui_hints("xpath")

    DESCRIPTION:

    Machination worker description files are relaxng schema files for
    the input.xml files consumed by workers. Machination specific
    information is encoded in namespace separated additional elements
    or attributes.

    Below is a short example describing the fictitious worker 'motd'
    version 1, which might construct message of the day files. Note
    the default namespace is the relaxng structure one, but that other
    namespaces are defined at the top. Those other namespaces describe
    aspects of the worker that are needed by other parts of
    Machination (for example the user interface).

    <element name="worker"
        xmlns="http://relaxng.org/ns/structure/1.0"
        xmlns:wu="https://github.com/machination/ns/workunit"
        xmlns:gui="https://github.com/machination/ns/guihint"
        xmlns:stpol="https://github.com/machination/ns/status-merge-policy"
        xmlns:secret="https://github.com/machination/ns/secrets"

        gui:icon="motd.svg"
        gui:title="Message of the day worker"
        gui:shorthelp="manipulates message of the day files"
        gui:longhelp="longhelp.txt"
        gui:doc="documentation.html"
        >
      <attribute name="id">
        <value>motd-1</value>
      </attribute>
      <element name="header"
          wu:wu="1"
          gui:icon="motd-header.svg"
          >
        <text/>
      </element>
      <element name="news">
        <zeroOrMore>
          <element name="item" wu:wu="1">
            <attribute name="id">
              <text/>
            </attribute>
            <text/>
          </element>
        </zeroOrMore>
      </element>
      <element name="secrets"
          secret:mustEncrypt="1"
          >
          <text/>
      </element>
      <element name="footer" wu:wu="1">
        <text/>
      </element>
    <element>

    For those unfamiliar with XML, the namespace declarations are the
    'xmlns' structures near the top and are in the form
    'xmlns:short_alias="some_long_identifier"', where the main
    desirable property of 'some_long_identifier' is uniqueness. URIs
    are specified in the standard and most authors use URLs based on
    some domain associated with the project.

    Here is an example of some worker input.xml that validates against
    the above schema:

    <worker id="motd-1"
        xmlns:secret="https://github.com/machination/ns/secrets"
        >
      <header>Hello there.</header>
      <news>
        <item id="brain">I have a brain the size of a planet.</item>
        <item id="depressed">I'm depressed.</item>
      </news>
      <secrets secret:secret="1">Bob - it's Alice here</secrets>
      <footer>Noone ever listens to me.</footer>
    </worker>

    """

    nsmap = {
        'rng': 'http://relaxng.org/ns/structure/1.0',
        'wu': 'https://github.com/machination/ns/workunit',
        'info': 'https://github.com/machination/ns/info'}

    def __init__(self, workername=None):
        """WorkerDescription init

        """

        self.__clear()
        
        if isinstance(workername,str):
            self.workername = workername
            # try to find the description file
            descfile = os.path.join(context.status_dir(), "workers", workername, "description.xml")
            try:
                self.desc = etree.parse(workername).getroot()
            except IOError:
                # carry on with defaults if descfile doesn't exist,
                # but if it does...
                if os.path.isfile(descfile):
                    raise
        elif isinstance(workername, etree._Element):
            # this constructor path allows us to instantiate directly from
            # an element for debugging purposes
            self.desc = workername
            self.workername = self.desc.xpath("/rng:element/rng:attribute[@name='id']/rng:value", namespaces=self.nsmap)[0].text

    def __clear(self):
        """Clear all cache attributes"""

        self.desc = None
        self.workername = None
        self.wucache = None


    def workunits(self):
        """return a set of valid work unit xpaths

        namespace:     https://github.com/machination/ns/workunit
        common prefix: wu

        side effects: maintains a cache of wu xpaths in the set
        self.wucache. This cache is deleted when load() (or __clear())
        is called.

        returns xpaths for all the elements in the worker description
        where the wu:wu attribute is set to '1' or which are direct
        children of the worker element.
        """

        # self.wu exists: just return the keys
        if self.wucache:
            return self.wucache

        # self.wu doesn't exist: construct it;
        self.wucache = set()

        # add all 'element' elements which would be direct children of
        # the /worker element or where wu:wu=1
        for elt in self.desc.iter("{%s}element" % self.nsmap["rng"]):
            path = self.describes_path(elt)

            # len(path) == 3 comes from the fact that a direct child of
            # worker will end up with a path like ["","worker","Name"]
            if(len(path) == 3 or elt.get("{%s}wu" % self.nsmap["wu"]) == "1"):
                self.wucache.add("/".join(path))
        return self.wucache

    def get_description(self, xpath):
        """return the description element for xpath"""
        # remove any ids from xpath
        xpath = MRXpath(xpath).to_noid_path()
        for el in self.desc.iter("{%s}element" % self.nsmap["rng"]):
            if "/".join(self.describes_path(el)) == xpath:
                return el
        return None

    def is_workunit(self, xpath):
        """True if xpath is a valid workunit, False otherwise

        Indicated by:
          attribute wu:wu="1"
        
        Default no indicator:
          False
        
        Default no description:
          True for immediate children of /worker
          False otherwise
        """

        if self.desc is not None:
            return MRXpath(xpath).to_noid_path() in self.workunits()
        else:
            mrx = MRXpath(xpath)
            # xpath should be /worker/something
            if mrx.length() == 2:
                return True
            else:
                return False

    def is_ordered(self, xpath):
        """True if xpath preserves order, False otherwise

        Indicated by:
          attribute info:ordered="1"
        
        Default no indicator:
          False
        
        Default no description:
          False
        """
        desc = self.get_description(xpath)
        if desc.get("{%s}ordered" % self.nsmap["info"]) == "1":
            return True
        else:
            return False


    def describes_path(self,element):
        """Return path in the final document which 'element' describes
        """

        if element.tag != "{%s}element" % self.nsmap['rng']:
            raise TypeError("The element passed to describes_path must have tag 'element'")
        path = []
        current = element
        while current.getparent() is not None:
            if current.tag == "{%s}element" % self.nsmap['rng']:
                path.append(current.get("name"))
            current = current.getparent()
        path.append(current.get("name"))
        path.append("")
        path.reverse()
        return path
        
