from lxml import etree


class WorkerDescription:
    """Work with worker description files

    SYNOPSIS:

    wd = WorkerDescription(description)

    or

    wd = WorkerDescription()
    wd.load(description)

    wugenerator = wd.workUnits()

    hint_dict = wd.guiHints("xpath")

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
        gui:icon="motd-header.svg">
        <text/>
      </element>
      <element name="news">
        <zeroOrMore>
          <element name="item" wu:wu="1">
            <attribute name="id">
              <text/>
            </attribute>
          </element>
        </zeroOrMore>
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

    <worker id="motd-1">
      <header>Hello there.</header>
      <news>
        <item id="brain">I have a brain the size of a planet.</item>
        <item id="depressed">I'm depressed.</item>
      </news>
      <footer>Noone ever listens to me.</footer>
    </worker>

    """

    nsmap = {
        'rng': 'http://relaxng.org/ns/structure/1.0',
        'wu': 'https://github.com/machination/ns/workunit'}

    def __init__(self, description=None):
        """WorkerDescription init

        Calls self.load(description) if description is provided"""

        if description:
            self.load(description)

    def load(self, description):
        """load worker description

        description should be either something lxml.etree.parse will
        accept (file like object, path to a file) or an lxml
        ElementTree or Element object.
        """

        self.desc = etree.parse(description)

    def workUnits(self):
        """return a generator of valid work unit xpaths

        namespace:     https://github.com/machination/ns/workunit
        common prefix: wu

        returns xpaths for all the elements in the worker description
        where the wu:wu attribute is set to '1'.
        """

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
            path.append("")
            path.reverse()
            yield "/".join(path)
