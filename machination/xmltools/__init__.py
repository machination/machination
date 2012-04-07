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
import re

class mrxpath(object):
    """Manipulate Machination restricted xpaths.

    Machination xpaths are of the form::

    /a/b[@id="id1"]/c
    /a/d/e[@id="id1"]/@att1

    or equivalently:

    /a/b[id1]/c
    /a/d/e[id1]/@att1

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
            self.set_path(mpath)
    
    def set_path(self, path, att = None):
        """Return a represntation based on ``path``
        
        calling options, elements::
          set_path(another_mrxpath_object)
          set_path("/standard/form[@id='frog']/xpath")
          set_path("/abbreviated/form[frog]/xpath")
          set_path(etree_element)

        attributes::
          set_path("/path/to/@attribute")
          set_path(etree_element,"attribute_name")
        """
        if isinstance(path, list):
            self.rep = path
        elif isinstance(path, mrxpath):
            # clone another mrxpath
            self.rep = path.clone_rep()
        elif isinstance(path, str):
            # a string, break it up and store the pieces
            rep = []
            tokens, remainder = mrxpath.scanner.scan(path)
            working = [('NAME','')]
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
        new = []
        for el in self.rep:
            new.append(el)
        return new

    def is_attribute(self, rep = None):
        """True if self represents an attribute, False otherwise"""
        if len(self.rep) < 2:
            # Not anything (first item in rep is always [''])
            return False
        if self.rep[-1][0][0] == "@":
            return True
        return False

    def is_element(self):
        """True if self represents an element, False otherwise"""
        if len(self.rep) < 2:
            # Not anything (first item in rep is always [''])
            return False
        return not self.is_attribute()

    def parent(self):
        """return mrxpath of parent element of rep or self.rep"""
        if len(self.rep) == 2: return None
        p = self.clone_rep()
        p.pop()
        return mrxpath(p)

    def ancestors(self):
        """return a list of ancestors as mrxpath objects (parent first)"""
        a = []
        p = self.parent()
        while p:
            a.append(p)
            p = p.parent()
        return a

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
    
class status(object):
    """Encapsulate a status XML element and functionality to manipulate it"""

    def __init__(self, status):
        if isinstance(status, str):
            status = etree.fromstring(status)
        if not isinstance(status, etree._Element):
            raise Exception("constructor must be called with an Element or a string with valid XML")
        if status.tag != "status":
            raise Exception("status must have the tag 'status', not " + status.tag)
        self.status = status

    def order_like(self, template, mrx=None):
        """order status elements like those in template"""
        if mrx is None:
            elt = self.status
        else:
            mrx = mrxpath(mrx)
            elts = self.status.xpath(mrx.to_xpath())
            if len(elts) > 1:
                raise Exception("The mrxpath 'mrx' must reference only one element")
            elt = elts[0]

    def apply_wu(self, wu):
        """Apply a work unit to self.status"""
        pass

    def apply_wus(self,wus):
        """Iterate over wus, applying them to self.status"""
        for wub in wus:
            self.apply_wu(wu)

    def add(self, elt, mrx, position = "$SAME$LAST"):
        """Add an element to parent specified by mrx

        position should normally be a single element mrxpath like:

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
