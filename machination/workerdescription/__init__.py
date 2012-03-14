"""Worker description file handling"""
from lxml import etree


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
          secret:shouldEncrypt="1"
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
        'wu': 'https://github.com/machination/ns/workunit'}

    def __init__(self, description=None):
        """WorkerDescription init

        Calls self.load(description) if description is provided"""

        self.__clear()
        if description:
            self.load(description)

    def __clear(self):
        """Clear all cache attributes"""

        self.desc = None
        self.wucache = None

    def load(self, description):
        """load worker description

        description should be either something lxml.etree.parse will
        accept (file like object, path to a file) or an lxml
        ElementTree or Element object.
        """

        # clear everything when loading a new description
        self.__clear()
        
        self.desc = etree.parse(description)

    def workunits(self):
        """return a dictionary key view of valid work unit xpaths

        namespace:     https://github.com/machination/ns/workunit
        common prefix: wu

        side effects: maintains a cache of wu xpaths in the dictionary
        self.wucache. This cache is deleted when load() (or __clear()) is
        called.

        returns xpaths for all the elements in the worker description
        where the wu:wu attribute is set to '1'.
        """

        # self.wu exists: just return the keys
        if self.wucache:
            return self.wucache.keys()

        # self.wu doesn't exist: construct it;
        self.wucache = {}
        wuels = self.desc.xpath(
            "//rng:element[@wu:wu='1']",
            namespaces=self.nsmap)
        for elt in wuels:
            path = []
            current = elt
            while current.getparent() is not None:
                if current.tag == '{' + self.nsmap['rng'] + '}element':
                    path.append(current.get("name"))
                current = current.getparent()
            path.append(current.get("name"))
            path.append("")
            path.reverse()
            self.wucache["/".join(path)] = None
        return self.wucache.keys()

    def is_workunit(self, xpath):
        """True if xpath is a valid workunit, False otherwise"""

        return xpath in self.workunits()
