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
   the same tag, but need not be globally unique.

"""
from lxml import etree
import re

class mrxpath:
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
    def token_att(scanner,token): return "ATT", token[1:]
    def token_elt(scanner,token): return "ELT", token
    scanner = re.Scanner([
            ("'(?:\\\\.|[^'])*'|\"(?:\\\\.|[^\"])*\"", token_qstring),
            (r"/", token_sep),
            (r"[\[\]]", token_bracket),
            (r"=", token_op),
            (r"@[a-zA-Z]\w*", token_att),
            (r"[a-zA-Z]\w*", token_elt),
            ])

    def __init__(self, mpath=None):
        self.rep = []
        if(mpath):
            self.set_path(mpath)
    
    def set_path(self, path):
        """Set the path this instance represents

        calling options on instance ``mrx``::
          mrx.set_path(another_mrxpath_object)
          mrx.set_path("/standard/form[@id='frog']/xpath")
          mrx.set_path("/abbreviated/form[frog]/xpath")
        
        """
        if isinstance(path,mrxpath):
            # clone another MXpath
            self.rep = path.clone_rep()
        elif isinstance(path,basestring):
            # a string, break it up and store the pieces
            newrep = []
            tokens, remainder = mrxpath.scanner.scan(path)
            working = [('ELT','')]
            for token in tokens:
                if token[0] == "SEP":
                    newrep.append(self.tokens_to_rep(working,newrep))
                    working = []
                else:
                    working.append(token)
            newrep.append(self.tokens_to_rep(working,newrep))
            self.rep = newrep

    def tokens_to_rep(self, tokens, rep=None):
        if rep and self.is_attribute(rep):
            raise Exception("cannot add more to an attribute xpath")
        if tokens[0][0] == "ELT":
            name = tokens[0][1]
            if len(tokens) == 1:
                return [name]
            elif tokens[2][0] == "ATT":
                idname = tokens[4][1]
                return [name,idname]
            else:
                idname = tokens[2][1]
                return [name,idname]
        elif tokens[0][0] == "ATT":
            return ["@" + tokens[0][1]]
            
    def clone_rep(self):
        """Return a clone of the invoking object's representation"""
        new = []
        for el in self.rep:
            new.append(el)
        return new

    def is_attribute(self,rep=None):
        """True if this object represents an attribute, False otherwise"""
        if rep == None:
            rep = self.rep
        if len(rep) == 0:
            return False
        if len(rep[-1][0]) == 0:
            return False
        if rep[-1][0][0] == "@":
            return True
        return False

    def is_element(self,rep):
        """True if this object represents an element, False otherwise"""
        if rep == None:
            rep = self.rep
        if len(rep) == 0:
            return False
        return not self.is_attribute()
