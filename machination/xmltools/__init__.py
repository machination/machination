"""Manipulate Machination style XML

Machination has several restrictions on the XML used. The
restrictions' primary aim is to ensure that the various status files
have certain desirable properties, but the restrictions are obeyed in
most places where Machination uses XML. These restrictions are:

#. No mixed content: an element may contain either other elements or
   text, not both.

#. Wherever sibling elements with the same tag are
   allowed (for example, where they represent the items in a list),
   those elements *must* be labelled with an 'id' attribute, even if
   there is currently only one (for example, the list currently
   contains only one item).

#. 'id' attributes must be unique amongst all sibling elements with
   the same tag, but need not be otherwise unique (i.e. ancestors or
   descendents may have the same id, only similarly named siblings may
   not).

"""
from lxml import etree
from lxml.builder import E
import copy
import os
import errno
import re
import functools
import pprint
from machination import context

class MRXpath(object):
    """Manipulate Machination restricted xpaths.

    Machination xpaths are of the form::

    /a/b[@id="id1"]/c
    /a/d/e[@id="id1"]/@att1

    or equivalently:

    /a/b[id1]/c
    /a/d/e[id1]/@att1

    relative xpaths also allowed:

    b[id1]/c

    """

    # A quick lexer, trick found at
    # http://www.evanfosmark.com/2009/02/sexy-lexing-with-python/
    # Thanks for your article Evan
    def token_qstring(scanner,token): return "QSTRING", token[1:-1]
    def token_sep(scanner,token): return "SEP", token
    def token_bracket(scanner,token): return "BRACKET", token
    def token_op(scanner, token): return "OP", token
    def token_at(scanner,token): return "AT", token
    def token_name(scanner,token): return "NAME", token
    scanner = re.Scanner([
            ("'(?:\\\\.|[^'])*'|\"(?:\\\\.|[^\"])*\"", token_qstring),
            (r"/", token_sep),
            (r"[\[\]]", token_bracket),
            (r"=", token_op),
            (r"@", token_at),
            (r"\w*", token_name),
            ])

    def __init__(self, mpath=None, att=None):
        self.rep = []
        if(mpath is not None):
            self.set_path(mpath, att)

    def set_path(self, path, att = None, prefix = None):
        """Set representation based on ``path``

        calling options, elements::
          set_path(another_MRXpath_object)
          set_path("/standard/form[@id='frog']/xpath")
          set_path("/abbreviated/form[frog]/xpath")
          set_path(etree_element)

        attributes::
          set_path("/path/to/@attribute")
          set_path(etree_element,"attribute_name")
        """
        if isinstance(path, list):
            self.rep = copy.deepcopy(path)
        elif isinstance(path, MRXpath):
            # clone another MRXpath
            self.rep = path.clone_rep()
        elif isinstance(path, str):
            # a string, break it up and store the pieces
            rep = []
            tokens, remainder = MRXpath.scanner.scan(path)
            if tokens[0][0] == "SEP":
                # rooted xpath, need an empty name to start
                working = [('NAME','')]
            else:
                working = []
            for token in tokens:
                if token[0] == "SEP":
                    rep.append(self.tokens_to_rep(working,rep))
                    working = []
                else:
                    working.append(token)
            rep.append(self.tokens_to_rep(working,rep))
            self.rep = rep
        elif isinstance(path, etree._Element):
            # an etree element, follow parents to root
            elt = path
            path = []
            if att is not None:
                if att not in elt.keys():
                    raise Exception("Cannot make a path to an attribute that does not exist")
                path.append(["@" + att])
            while(elt is not None):
                item = [elt.tag]
                if "id" in elt.keys():
                    item.append(elt.get("id"))
                path.append(item)
                elt = elt.getparent()
            path.append([""])
            path.reverse()
            self.rep = path

    # TODO: this parser is fragile and doesn't give sensible error messages
    def tokens_to_rep(self, tokens, rep = None):
        if rep and self.is_attribute(rep):
            raise Exception("cannot add more to an attribute xpath")
        if tokens[0][0] == "NAME":
            name = tokens[0][1]
            if len(tokens) == 1:
                # expecting:
                #  [NAME]
                # just an element
                return [name]
            elif tokens[2][0] == "AT":
                # expecting:
                #  [NAME,BRACKET,AT,NAME,OP,QSTRING,BRACKET]
                # an element with an id passed as [@id="something"]
                if len(tokens) < 7:
                    raise Exception("expecting a 7 token sequence: " +
                                    "[NAME,BRACKET,AT,NAME," +
                                    "OP,QSTRING,BRACKET] got " +
                                    repr(tokens))
                if tokens[5][0] != "QSTRING":
                    raise Exception("expecting a QSTRING at element 5 of " +
                                    str(tokens) + " got " + str(tokens[5]))
                idname = tokens[5][1]
                return [name,idname]
            else:
                # expecting:
                #  [NAME,BRACKET,QSTRING|NAME,BRACKET]
                # an element with an id passed as [something]
                if len(tokens) < 4:
                    raise Exception("expecting a 4 token sequence: " +
                                    "[NAME,BRACKET,QSTRING|NAME,BRACKET]" +
                                    " got " +
                                    repr(tokens))
                if tokens[2][0] != "NAME" and tokens[2][0] != "QSTRING":
                    raise Exception("expecting a NAME or QSTRING at " +
                                    "element 2 of " +
                                    str(tokens) + " got " + str(tokens[2]))
                idname = tokens[2][1]
                return [name,idname]
        elif tokens[0][0] == "AT":
            # an attribute, the next token should be the name
            return ["@" + tokens[1][1]]

    def clone_rep(self):
        """Return a clone of representation"""
        return copy.deepcopy(self.rep)

    def __repr__(self):
        return self.to_xpath()

    def __str__(self):
        return self.to_xpath()

    def __hash__(self):
        return str(self).__hash__()

    def __eq__(self, other):
        return self.to_abbrev_xpath() == other.to_abbrev_xpath()
    def __ne__(self, other):
        return self.to_abbrev_xpath() != other.to_abbrev_xpath()

    def __len__(self):
        return self.length()

    def __getitem__(self, key):
        if self.is_rooted():
            rep = self.rep[1:]
        else:
            rep = self.rep
        if isinstance(key, int):
            return MRXpath([rep[key]])
        else:
            ret = MRXpath(rep[key])
            if self.is_rooted() and not key.start:
                ret.reroot()
            return ret

    def __setitem__(self, key, value):
        if isinstance(key, int):
            if self.is_rooted():
                key += 1
            del self.rep[key]
        elif isinstance(key, slice):
            if self.is_rooted():
                start = key.start
                if start is None:
                    start = 0
                stop = key.stop
                if stop is None:
                    stop = len(self)
                key = slice(start + 1, stop + 1, key.step)
            del self.rep[key]
            key = key.start
        else:
            raise Exception("don't understand key type " + str(type(key)))
        for item in MRXpath(value).rep:
            self.rep.insert(key, item)
            key += 1

    def append(self, val):
        if self.is_attribute():
            raise Exception("cannot append to an attribute")
        val = MRXpath(val)
        for i in val.rep:
            self.rep.append(i)

    def is_attribute(self, rep = None):
        """True if self represents an attribute, False otherwise"""
        if self.is_rooted() and len(self.rep) < 2:
            # Not anything (first item in rep is always [''])
            return False
        if len(self.rep) > 0 and self.rep[-1][0][0] == "@":
            return True
        return False

    def is_element(self):
        """True if self represents an element, False otherwise"""
        if self.is_rooted() and len(self.rep) < 2:
            # Not anything (first item in rep is always [''])
            return False
        if len(self.rep) > 0:
            return not self.is_attribute()
        return False

    def is_rooted(self):
        """True if xpath begins with "/", False otherwise"""
        if len(self.rep) >= 1 and self.rep[0][0] == '':
            return True
        else:
            return False

    def reroot(self):
        """root this xpath if it is not already rooted"""
        if len(self.rep) > 0:
            if self.rep[0][0] != '':
                self.rep.insert(0,[''])
        else:
            self.rep = [['']]
        return self

    def parent(self):
        """return MRXpath of parent element of rep or None"""
        if len(self.rep) == 2: return None
        return self[:len(self)-1]

    def ancestors(self):
        """return a list of ancestors as MRXpath objects (parent first)"""
        a = []
        p = self.parent()
        while p:
            a.append(p)
            p = p.parent()
        return a

    def length(self):
        """return the length in elements"""
        if self.is_rooted():
            return len(self.rep) - 1
        else:
            return len(self.rep)

    def last_item(self):
        """return MRXpath object representing the last item in this rep"""
        return MRXpath(self.rep[-1])

    def item(self,n):
        """return MRXpath object representing item n in the rep"""
        return MRXpath(self.rep[0:n+1])

    def name(self):
        """return the name of the object"""
        if self.is_attribute():
            return self.rep[-1][0][1:]
        if len(self.rep) > 0:
            return self.rep[-1][0]
        return None

    def id(self):
        """return id of the object or None"""
        if self.is_attribute():
            raise Exception("an attribute may not have an id")
        if self.is_element():
            if len(self.rep[-1]) > 1:
                return self.rep[-1][1]
            else:
                return None
        return None

    def to_xpath(self):
        """return xpath string"""
        return "/".join([ "%s[@id='%s']" % (e[0],e[1]) if len(e)==2 else e[0] for e in self.rep])

    def to_abbrev_xpath(self):
        """return Machination abbreviated xpath string"""
        return "/".join([ "%s['%s']" % (e[0],e[1]) if len(e)==2 else e[0] for e in self.rep])

    def to_noid_path(self):
        """return xpath with no ids"""
        return "/".join([e[0] for e in self.rep])

    def to_xpath_list(self):
        """return list of xpath path elements"""
        return [ "%s[@id='%s']" % (e[0],e[1]) if len(e)==2 else e[0] for e in self.rep]

    def strip_prefix(self, prefix):
        prefix = MRXpath(prefix)
        return self[len(prefix):].reroot()

    def workername(self, prefix = None):
        """return worker name for an xpath with prefix before worker element"""
        xpath = self
        if prefix is not None:
            xpath = self.strip_prefix(prefix)
        return xpath[0].id()

class Status(object):
    """Encapsulate a status XML element and functionality to manipulate it"""

    def __init__(self, statin, worker_prefix = None):
        if isinstance(statin, str):
            self.status = etree.fromstring(statin)
        elif isinstance(statin, etree._Element):
            self.status = statin
        elif isinstance(statin, Status):
            self.status = copy.deepcopy(statin.status)
        else:
            raise Exception("Don't know how to initialise from a " + type(statin))
        self.wprefix = None
        if worker_prefix is None:
            self.wprefix = self.worker_prefix()
        else:
            self.wprefix = MRXpath(worker_prefix)

    def worker_prefix(self):
        """return self.worker_prefix or try to"""
        if self.wprefix is None:
            # divine from the last worker element we find
            mrx = MRXpath(self.status.xpath("//worker")[-1])
            self.wprefix = mrx.parent()
        return self.wprefix

    def order_like(self, template):
        """order status elements like those in template"""
        if mrx is None:
            elt = self.status
        else:
            mrx = MRXpath(mrx)
            elts = self.status.xpath(mrx.to_xpath())
            if len(elts) > 1:
                raise Exception("The MRXpath 'mrx' must reference only one element")
            elt = elts[0]

    def generate_wus(self, todo, comp, orderstyle="move"):
        """Return a list of workunits from actions guided by template.

        Args:
          comp: an XMLCompare object initialised as:
            XMLCompare(working, template, workerdesc)
              working: ``an etree.Element``. This should a copy of the
                current status element and it will be updated to be as
                close to the ``template`` status element as
                ``actions`` allow.
              template: an etree.Element with the same tag as
                self.status to be used as a template for changes. for
                ordered workers it should have the resulting elements
                in the desired order. Usually the appropriate element
                from final desired_status.
          todo: set of workunit xpaths to do in this pass.
          orderstyle: control what kind of ordering wus are generated:
            move: move(tag1[id1],tag2[id2]) - move tag1[id1] after tag2[id2].
            removeadd: remove(tag1[id1]) followed by add(tag1[id1],tag2[id2]).
            swap: swap(tag1[id1],tag2[id2]).

        Returns:
          a list of work unit (wu) elements

        Side Effects:
          ``working`` will be altered to the nearest desired status that
          ``actions`` will allow. This is usually the desired status within
          the current independent work set.
        """

        working = copy.deepcopy(comp.leftxml)
        template = comp.rightxml
        wds = comp.wds()
#        actions = comp.actions(comp.bystate['datadiff'])
        actions = {'remove': todo & comp.bystate['left'],
                   'add': todo & comp.bystate['right'],
                   'datamod': todo & comp.bystate['datadiff'],
                   'deepmod': todo & comp.bystate['childdiff']}
        wus = []

        # removes
        for rx in actions['remove']:
            rx = MRXpath(rx)
            wd = wds[rx.workername("/status")]
            # todo should always be workunits
            if not wd.is_workunit(rx):
                raise Exception('Trying to remove %s, which is not a work unit'
                                % rx.to_xpath())
            for e in working.xpath(rx.to_xpath()):
                e.getparent().remove(e)
            # <wu op="remove" id="rx"/>
            wus.append(E.wu(op="remove", id=rx.to_xpath()))

        # data only modified

        # modifies
        # iterate through template sub elements and cf. working:
        #  - descendant of a wu which is also a descendant of mx
        #    = ignore, a more sepcific work unit is in charge of mx
        #  - attribute in both
        #    = set value of att in of working to template
        #  - attribute in template only
        #    = add to working
        #  - attribute in working only
        #    = remove from working
        #  - element in both, text only
        #    = set working text to template
        #  - element in both, subelements
        #    = scan attribs as above, then continue to next iteration
        #  - element in template only
        #    = add full element from template to working
        # above loop can't detect elements in working only, so...
        # iterate through working subelements:
        #  - element in working only
        #    = remove element from working
        for mx in comp.bystate['datadiff'] | comp.bystate['childdiff']:
            mx = MRXpath(mx)
            wd = wds[mx.workername("/status")]
            # every action should be a valid work unit
            if not wd.is_workunit(mx):
                raise Exception('Trying to remove %s, which is not a work unit'
                                % mx.to_xpath())
            # alter the working XML
            # find the element to modify
            try:
                e = working.xpath(mx.to_xpath())[0]
                te = template.xpath(mx.to_xpath())[0]
            except IndexError:
                 # no results
                raise Exception("could not find %s in working or template " %
                                mx.to_abbrev_xpath())

            first = True
            for se in e.iter():
                # find equivalent element from template.
                try:
                    ste = template.xpath(MRXpath(se).to_xpath())[0]
                except IndexError:
                    # xpath doesn't exist in template, must be a remove
                    # somewhere in the future
                    continue
                # change any different attributes
                for se_att in se.keys():
                    if se_att not in ste.keys():
                        del se.attrib[se_att]
                    else:
                        se.set(se_att, ste.get(se_att))
                # change any different text
                se.text = ste.text
                if first:
                    # the first element will be e itself
                    first = False
                    continue
                if wd.is_workunit(MRXpath(se).to_noid_path()):
                    # is a workunit: remove
                    se.getparent().remove(se)
            # generate a wu
            wus.append(
                E.wu(e, op="modify", id=mx)
                )

        # add and reorder
        # iterate over elements in template and see if working needs them
        # added or moved.
        for te in template.iter():
            tmrx = MRXpath(te)
            welts = working.xpath(tmrx.to_xpath())
            if welts:
                # there is a corresponding element in working, check if it
                # is in the right position

                # don't do the root element (/worker)
                if tmrx.to_noid_path() == "/worker":
                    continue

                # don't bother generating order wus if order is unimportant
                # (parent not flagged as ordered)
                if not wd.is_ordered(tmrx.parent().to_noid_path()):
                    continue

                # find the first previous element that also exists in working
                prev = te.getprevious()
                wprevs = working.xpath(MRXpath(prev).to_xpath())
                while prev and not wprevs:
                    prev = prev.getprevious()
                    wprevs = working.xpath(MRXpath(prev).to_xpath())

                # find the parent from working
                wparent = working.xpath(tmrx.parent().to_xpath())[0]
                if prev is None:
                    # move to first child
                    wparent.insert(0, welts[0])
                    # remember position for wu
                    pos = "<first>"
                else:
                    # insert after wprev[0]
                    wparent.insert(wparent.index(wprevs[0] + 1), welts[0])
                    pos = MRXpath(wprev[0]).last_item().to_xpath()

                # generate a work unit
                # TODO(colin): support other order wu styles
                wus.append(
                    E.wu(op="move",
                         id=tmrx.to_xpath(),
                         pos=pos)
                    )

            else:
                # there is not a corresponding element in working, add
                # if there is an add in actions, otherwise the
                # element should be added on a later run
                if not tmrx.to_xpath() in actions["add"]:
                    continue

                # can't add to a parent that doesn't exist
                try:
                    wparent = working.xpath(tmrx.parent().to_xpath())[0]
                except IndexError:
                    raise Exception("trying to add " + tmrx.to_xpath() +
                                    " but its parent does not exist")

                # make a copy of the element to add
                add_elt = copy.deepcopy(te)
                # strip out any sub work units - they should be added later
                for subadd in add_elt.iter():
                    if wd.is_workunit(MRXpath(subadd).no_noid_path()):
                        # is a workunit: remove
                        subadd.getparent().remove(subadd)

                # find the first previous element that also exists in working
                prev = te.getprevious()
                wprevs = working.xpath(MRXpath(prev).to_xpath())
                while prev and not wprevs:
                    prev = prev.getprevious()
                    wprevs = working.xpath(MRXpath(prev).to_xpath())

                if prev is None:
                    # add as first child
                    wparent.insert(0, add_elt)
                    pos = "<first>"
                else:
                    # add after wprev[0]
                    wparent.insert(wparent.index(wprevs[0] + 1), add_elt)
                    pos = MRXpath(wprev[0]).last_item().to_xpath()

                # generate a work unit
                wus.append(
                    E.wu(add_elt,
                         op="add",
                         id=tmrx.to_xpath(),
                         pos=pos)
                    )

        # these are the droids you are looking for...
        return wus

    def find_temp_desired(self, wus, template):
        working = Status(self)
        working.apply_wus(wus)
        working.order_like(template)
        return working

    def apply_wu(self, wu):
        """Apply a work unit to self.status"""
        pass

    def apply_wus(self,wus):
        """Iterate over wus, applying them to self.status"""
        for wu in wus:
            self.apply_wu(wu)

    def add(self, elt, mrx, position = "<last>"):
        """Add an element to parent specified by mrx

        position should normally be a single element MRXpath like:

          * name or
          * name[id]

        in which case the new element will be added

        posid should be the id of the element (with tag 'postag') elt
        is to be placed after or one of:

          * ["LAST"] = after last 'postag' element.
            * If postag is ["ANY"] this means parent.append(elt)
          * ["FIRST"] = as first child before first existing 'postag' element
            * If postag is ["ANY"] this means parent.insert(0,elt)

        """
        pass

    def order_after(self, mrx , afterid = ["LAST"]):
        """place element specified by mrx after sibling with id"""
        pass

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

    def __init__(self, workername, prefix = None):
        """WorkerDescription init

        Args:

          workername: the name of the worker. The description file
            will be loaded from a standard location based on this
            name. An etree Element may also be passed, in which case
            the element will be used in place of the root of the
            parsed description file. This is mostly useful for
            debugging.

          prefix(=None): the xpath prefix to worker elements. Used
            when checking worker elements snipped from larger files
            (like desired-status and current-status).
        """

        self.__clear()

        if isinstance(workername,str):
            self.workername = workername
            # try to find the description file
            descfile = os.path.join(context.status_dir(), "workers", workername, "description.xml")
            try:
                self.desc = etree.parse(descfile).getroot()
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

        self.prefix = None
        if prefix:
            self.prefix = MRXpath(prefix)

    def __clear(self):
        """Clear all cache attributes"""

        self.desc = None
        self.workername = None
#        self.wucache = None

    # should provide the same answer every time...
    @functools.lru_cache(maxsize=1)
    def workunits(self):
        """return a set of valid work unit xpaths

        namespace:     https://github.com/machination/ns/workunit
        common prefix: wu

        returns xpaths for all the elements in the worker description
        where the wu:wu attribute is set to '1' or which are direct
        children of the worker element.
        """
        wus = set()
        # add all 'element' elements which would be direct children of
        # the /worker element or where wu:wu=1
        for elt in self.desc.iter("{%s}element" % self.nsmap["rng"]):
            path = self.describes_path(elt)

            # len(path) == 3 comes from the fact that a direct child of
            # worker will end up with a path like ["","worker","Name"]
            if(len(path) == 3 or elt.get("{%s}wu" % self.nsmap["wu"]) == "1"):
                wus.add("/".join(path))
        return wus

    @functools.lru_cache(maxsize=100)
    def get_description(self, xpath):
        """return the description element for xpath"""
        xpath = MRXpath(xpath)
        if self.prefix:
            # check that xpath actually begins with prefix
            if self.prefix != xpath[:len(self.prefix)]:
                raise Exception("prefix is defined so " + str(xpath) + " should start with " + str(self.prefix))
            # remove the prefix from xpath
            xpath = xpath[len(self.prefix):].reroot()
        for el in self.desc.iter("{%s}element" % self.nsmap["rng"]):
            if "/".join(self.describes_path(el)) == xpath.to_noid_path():
                return el
        return None

    @functools.lru_cache(maxsize=100)
    def is_workunit(self, xpath):
        """True if xpath is a valid workunit, False otherwise

        Args:
          xpath: an xpath string or MRXpath object

        Indicated by:
          attribute wu:wu="1"

        Default no indicator:
          False

        Default no description:
          True for immediate children of /worker
          False otherwise
        """

        xpath = MRXpath(xpath)

        if self.desc is not None:
            desc = self.get_description(xpath)
            if desc is not None and desc.get("{%s}wu" % self.nsmap["wu"]) == "1":
                return True
            else:
                return False
        else:
            mrx = MRXpath(xpath)[len(self.prefix):].reroot()
            # xpath should be /worker or /worker/something
            if len(mrx) <= 2:
                return True
            else:
                return False

    @functools.lru_cache(maxsize=100)
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

    @functools.lru_cache(maxsize=100)
    def describes_path(self, element):
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

    @functools.lru_cache(maxsize=100)
    def find_workunit(self, xpath):
        """return nearest workunit: xpath or nearest wu ancestor."""

        mrx = MRXpath(xpath)

        if self.is_workunit(mrx):
            return mrx.to_xpath()

        # xpath is not a workunit - travel up ancestors until we find one
        mrx = mrx.parent()
        while mrx:
            if self.is_workunit(mrx):
                return mrx.to_xpath()
            mrx = mrx.parent()

        # got to the root without finding a workunit
        raise Exception("No work unit ancestors found!")

    def find_work(self, xpset):
        """return the set of workunits for a set of xpaths"""
        return {self.find_workunit(x) for x in xpset}


class XMLCompare(object):
    """Compare two etree Elements and store the results

    Machination (and its workers) use this class to ask for a
    'worklist' based on differences between the 'local' status.xml and
    the downloaded profile.
    """

    def __init__(self, leftxml, rightxml):
        """XMLCompare constructor

        Args:
          leftxml: an etree Element
          rightxml: an etree Element
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
        self.diff_to_action = {
            'left': 'remove',
            'right': 'add',
            'datadiff': 'datamod',
            'childdiff': 'deepmod'
            }
        self.workcache = None
        self.compare()

    def actions(self):
        """return dictionary of sets action: xpaths"""
#        return {xpath: self.diff_to_action[self.byxpath[xpath]] for xpath in self.find_work()}
#        return {self.diff_to_action[self.byxpath[x]]: {y for y in self.find_work() if self.diff_to_action[self.byxpath[x]] == self.diff_to_action[self.byxpath[y]]} for x in self.find_work()}
        return {self.diff_to_action[s]: self.find_work() & self.bystate[s] for s in ['left', 'right', 'datadiff', 'childdiff']}

    def compare(self):
        """Compare the xpath sets and generate a diff dict"""

        for elt in self.leftxml.iter():
            self.leftset.add(MRXpath(elt).to_xpath())
            for att in elt.keys():
                if att == "id":
                    continue
                self.leftset.add(MRXpath(elt,att=att).to_xpath())
        for elt in self.rightxml.iter():
            self.rightset.add(MRXpath(elt).to_xpath())
            for att in elt.keys():
                if att == "id":
                    continue
                self.rightset.add(MRXpath(elt,att=att).to_xpath())

#        self.leftset = {MRXpath(elt).to_xpath() for elt in self.leftxml.iter()}
#        self.rightset = {MRXpath(elt).to_xpath() for elt in self.rightxml.iter()}

        for xpath in self.leftset.difference(self.rightset):
            self.bystate['left'].add(xpath)
            self.byxpath[xpath] = 'left'
            self._set_childdiff(MRXpath(xpath).parent())

        for xpath in self.rightset.difference(self.leftset):
            self.bystate['right'].add(xpath)
            self.byxpath[xpath] = 'right'
            self._set_childdiff(MRXpath(xpath).parent())

        self.find_diffs(self.leftset.intersection(self.rightset))
#        self.worklist = self.find_work(self.bystate['datadiff'] | self.bystate['left'] | self.bystate['right'])

    def find_diffs(self, xpathlist):
        """Find differing values in the intersection set"""

        for xpath in xpathlist:
            l = self.leftxml.xpath(xpath)
            r = self.rightxml.xpath(xpath)

            # l[0] or r[0] can be element objects, or attr strings
            # Try to get the text - if it fails, its an attribute
            lval = ""
            rval = ""

            # check data difference
            try:
                lval = l[0].text
                rval = r[0].text
            except AttributeError:
                lval = l[0]
                rval = r[0]

            if lval != rval:
                self.bystate['datadiff'].add(xpath)
                self.byxpath[xpath] = 'datadiff'
#                for a in MRXpath(xpath).ancestors():
#                    self.bystate['childdiff'].add(a.to_xpath())
#                    self.byxpath[a.to_xpath()] = 'childdiff'
                self._set_childdiff(MRXpath(xpath))

    def order_diff(self):
        # check child order for all xpaths that so far look the same
        for xp in (self.leftset | self.rightset) - (self.bystate['left'] | self.bystate['right'] | self.bystate['datadiff'] | self.bystate['childdiff']):
            # xp guaranteed(?) to exist in both by construction
            left_elt = self.leftxml.xpath(xp)[0]
            right_elt = self.rightxml.xpath(xp)[0]
            # it's enough to check direct children, deeper into the tree
            # will be checked by other xpaths


    def _set_childdiff(self, mrx):
        """set the state of mrx.to_xpath() to 'childdiff'

        Will set all ancestors to 'childdiff' if necessary
        """
        # the following is so that we can call _set_childdiff(x.parent())
        # and not worry
        if mrx is None:
            return

        # Now get on and do the real work
        self.bystate['childdiff'].add(mrx.to_xpath())
        self.byxpath[mrx.to_xpath()] = 'childdiff'
        p = mrx.parent()
        if p and self.byxpath[p.to_xpath()] != 'childdiff':
            self._set_childdiff(p)

    @functools.lru_cache(maxsize=100)
    def find_work(self, prefix = "/status"):
        """return a set of all wus for all diff xpaths in all workers

        Args:
          prefix: xpath prefix to parent of worker elements.
        """

        diffs = self.bystate['datadiff'] | self.bystate['left'] | self.bystate['right']

        wi = len(MRXpath(prefix))

        return {self.wds(prefix)[MRXpath(x)[wi].id()].find_workunit(x) for x in diffs}

    def wds(self, prefix = "/status"):
        """create a dictionary of WorkerDescriptions"""

        # find all the workers that are mentioned
        wnames = {w.get("id") for w in self.leftxml.xpath(prefix + "/worker")} | {w.get("id") for w in self.rightxml.xpath(prefix + "/worker")}

        return {n: WorkerDescription(n, prefix) for n in wnames}


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
