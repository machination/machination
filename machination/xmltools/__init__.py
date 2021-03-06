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
import sys
import shlex
from machination import context
from machination import utils
import hashlib

l = context.logger

# see if functools.lru_cache is defined
try:
    getattr(functools, 'lru_cache')
except AttributeError:
    from machination import threebits
    functools.lru_cache = threebits.lru_cache

def mc14n(elt):
    '''Machination canonicalization

    Mostly strip ignorable white space from data elements'''

    # Make sure we are working on an element
    if isinstance(elt, etree._ElementTree):
        elt = elt.getroot()

    # Strip comments
    if isinstance(elt, etree._Comment):
        elt.getparent().remove(elt)

    # No tails (not for /local/ people)
    elt.tail = None

    # C14n of children
    children = 0
    for e in elt.iterchildren():
        mc14n(e)
        children = children + 1

    # If elt has any children then it can't be a text element. Note
    # this include comment children => no comments in text bearing
    # elements.
    if children:
        elt.text = None

    return elt

def pstring_old(e, top=True, depth=0, istring='  '):
    """pretty string representation of an etree element"""
    if isinstance(e, etree._ElementTree):
        e = e.getroot()
    rep = []
    rep.append('{}<{}'.format(istring * depth, e.tag))
    for att in e.keys():
        rep.append(" {}='{}'".format(att, e.get(att)))
    if len(e) == 0:
        if e.text is None or e.text == '':
            rep.append("/>")
        else:
            rep.append(">{}</{}>".format(e.text, e.tag))
    else:
        rep.append(">\n")
        for sube in e:
            rep.append(pstring(sube, False, depth + 1, istring))
        rep.append("{}</{}>".format(istring * depth, e.tag))
    if not top:
        rep.append("\n")
    return ''.join(rep)

def pstring(e):
    """pretty string representation of an etree element"""
    if isinstance(e, etree._ElementTree):
        e = e.getroot()
    return etree.tostring(e, pretty_print = True).decode()


def generate_wus(todo, comp, orderstyle="move"):
    """Return a list of workunits from todo list guided by template.

    Args:
    todo: set of workunit xpaths to do in this pass.
    comp: an XMLCompare object initialised as:
    XMLCompare(working, template)
    working: an ``etree.Element``. This should a copy of the
    current status element and it will be updated to be as
    close to the template status element as
    todo allows.
    template: an etree.Element with the same tag as
    working to be used as a template for changes. for
    ordered workers it should have the resulting elements
    in the desired order. Usually the appropriate element
    from final desired_status.
    orderstyle: control what kind of ordering wus are generated:
    move: move(tag1[id1],tag2[id2]) - move tag1[id1] after tag2[id2].
    removeadd: remove(tag1[id1]) followed by add(tag1[id1],tag2[id2]).
    swap: swap(tag1[id1],tag2[id2]).

    Returns:
    a list of work unit (wu) elements

    Side Effects:
    ``working`` will be altered to the nearest desired status that
    ``todo`` allows. This is usually the desired status within
    the current independent work set.
    """

    working = copy.deepcopy(comp.leftxml)
    template = copy.deepcopy(comp.rightxml)
    wds = comp.wds()
#        actions = comp.actions(comp.bystate['datadiff'])
#        actions = {'remove': todo & comp.bystate['left'],
#                   'add': todo & comp.bystate['right'],
#                   'datamod': todo & comp.bystate['datadiff'],
#                   'deepmod': todo & comp.bystate['childdiff'],
#                   'reorder': todo & comp.bystate['orderdiff']}
    wus = []

    # removes
    for rx in comp.actions()['remove'] & todo:
        rx = MRXpath(rx)
        wd = wds[rx.workername("/status")]
        # todo should always be workunits
        if not wd.is_workunit(rx):
            raise Exception('Trying to remove %s, which is not a work unit'
                            % rx.to_xpath())
        for e in working.xpath(rx.to_xpath()):
            e.getparent().remove(e)
        # <wu op="remove" id="rx"/>
        l.dmsg('generating remove for {}'.format(rx.to_xpath()))
        wus.append(E.wu(copy.deepcopy(e), op="remove", id=rx.to_xpath()))

    # data only modified
    for mx in comp.actions()['datamod'] & todo:
        mx = MRXpath(mx)
        wd = wds[mx.workername("/status")]
        # every action should be a valid work unit
        if not wd.is_workunit(mx):
            raise Exception('Trying to modify %s, which is not a work unit'
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
        e.text = te.text
        # generate wu
        wus.append(
            E.wu(copy.deepcopy(e), op="datamod", id=mx.to_xpath())
            )

    # deep modify
    # iterate through template sub elements and cf. working:
    #  - descendant of a wu which is also a descendant of mx
    #    = remove from working, a more sepcific work unit is
    #      in charge of mx
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

    for mx in comp.actions()['deepmod'] & todo:
        mx = MRXpath(mx)
        wd = wds[mx.workername("/status")]
        # every action should be a valid work unit
        if not wd.is_workunit(mx):
            raise Exception('Trying to modify %s, which is not a work unit'
                            % mx.to_xpath())
        # alter the working XML
        # find the element to modify
        # We might reject the mod, so we need to work on a copy of working
        w2 = copy.deepcopy(working)
        try:
            e = w2.xpath(mx.to_xpath())[0]
            te = template.xpath(mx.to_xpath())[0]
        except IndexError:
            # no results
            raise Exception("could not find %s in working or template " %
                            mx.to_abbrev_xpath())

        e_to_remove = set()
        e_removed = set()
        e_to_move = {}
        elts_changed = False
        atts_changed = False
        text_changed = False
        for se in e.iter(tag=etree.Element):
            se_mrx = MRXpath(se)
#            print('checking element {}'.format(se_mrx))
#            print('  se_wux:' + wd.find_workunit(se_mrx))
#            print('  mx_wux:' + wd.find_workunit(mx))

            if se_mrx.parent().to_xpath() in e_removed:
                # Parent already scheduled for removal
                e_removed.add(se_mrx.to_xpath())
#                l.dmsg('deepmod parent already removed for {}'.format(se_mrx.to_xpath()),10)
                continue

            if wd.find_workunit(se_mrx) != wd.find_workunit(mx):
                # se must have a more specific workunit than mx,
                # remove from working - another workunit is in charge
#                l.dmsg('deepmod more specific work unit for ' + se_mrx.to_xpath(), 10)
                e_to_remove.add(se_mrx.to_xpath())
                e_removed.add(se_mrx.to_xpath())
                continue

            # find equivalent element from template.
            try:
                ste = template.xpath(se_mrx.to_xpath())[0]
#                l.dmsg('deepmod found {} in template'.format(se_mrx.to_xpath()))
            except IndexError:
                # xpath doesn't exist in template, remove
                elts_changed = True
                e_to_remove.add(se_mrx.to_xpath())
                e_removed.add(se_mrx.to_xpath())
                continue

            # change any different attributes
            for k in se.keys():
                if k in ste.keys():
                    if se.get(k) != ste.get(k):
                        atts_changed = True
                        se.set(k, ste.get(k))
                else:
                    atts_changed = True
                    del se.attrib[k]
            for k in ste.keys():
                if k not in se.keys():
                    atts_changed = True
                    se.set(k, ste.get(k))

            # change any different text
            if se.text != ste.text:
                text_changed = True
                se.text = ste.text

            if se_mrx.to_xpath() in comp.bystate['orderdiff']\
                    and e != se:
                # sub element in wrong order - change
                elts_changed = True
                context.logger.dmsg('moving {} subelement {}'.
                                    format(mx.to_xpath(), se_mrx.to_xpath()))
                prevwe = closest_shared_previous(w2,
                                                 template,
                                                 se_mrx)
                if prevwe is None:
                    parent_mrx = MRXpath(ste.getparent())
                    parent = w2.xpath(parent_mrx.to_xpath())[0]
                    index = 0
                else:
                    parent = se.getparent()
                    index = parent.index(prevwe) + 1
                e_to_move[se_mrx.to_xpath] = [se, index]

        for xp in e_to_remove:
            rem = e.xpath(xp)[0]
            rem.getparent().remove(rem)

        for xp in e_to_move:
            se, index = e_to_move[xp]
            parent = se.getparent()
            parent.remove(se)
            parent.insert(index, se)

        for ste in te.iter(tag=etree.Element):
            ste_mrx = MRXpath(ste)
            try:
                se = w2.xpath(ste_mrx.to_xpath())[0]
            except IndexError:
                # ste doesn't exist in working.

                # Don't add if ste is a work unit
                if wd.find_workunit(MRXpath(ste)) != wd.find_workunit(mx):
                    continue

                # Add a copy
                add = copy.deepcopy(ste)

                # strip out any sub work units
                for aelt in add.iterdescendants():
                    if wd.find_workunit(MRXpath(aelt)) != \
                            wd.find_workunit(mx):
                        aelt.getparent().remove(aelt)

                # find the first previous xpath that also exists
                # in working
                prevwe = closest_shared_previous(w2,
                                                 template,
                                                 MRXpath(ste))

                # We can just add to working because we aren't
                # iterating over part of it
                if prevwe is None:
                    parent_mrx = MRXpath(ste.getparent())
                    wep = w2.xpath(parent_mrx.to_xpath())[0]
                    index = 0
                else:
                    wep = prevwe.getparent()
                    index = wep.index(prevwe) + 1
                elts_changed = True
                wep.insert(index, add)
            else:
                continue

        # generate wu
        l.dmsg('Checking changes for deepmod {}'.format(mx.to_xpath()), 10)
        if elts_changed or atts_changed or text_changed:
            l.dmsg('Adding deepmod {}'.format(mx.to_xpath()), 10)
            old_elt = working.xpath(mx.to_xpath())[0]
            new_elt = w2.xpath(mx.to_xpath())[0]
            old_elt.getparent().replace(old_elt, new_elt)
            wus.append(
                E.wu(copy.deepcopy(e), op="deepmod", id=mx.to_xpath())
                )

    # add and reorder
    # iterate over elements in template and see if working needs them
    # added or moved.
    for te in template.iter(tag=etree.Element):
        tmrx = MRXpath(te)
        if tmrx.to_xpath() not in todo:
            continue
        welts = working.xpath(tmrx.to_xpath())
        if welts:
            # there is a corresponding element in working, check if it
            # is in the right position

            # ignore worker elements
            if tmrx.to_noid_path() == "/status/worker":
                continue

            # don't reorder unless te is a workunit
            # easiest way to see is to check comp.actions()['reorder']
            if tmrx.to_xpath() not in comp.actions()['reorder']:
                continue

            wd = wds[tmrx.workername("/status")]
            # don't bother generating order wus if order is unimportant
            # (parent not flagged as ordered)
            if not wd.is_ordered(tmrx.parent().to_noid_path()):
                    continue

            # no move needed if previous for welts[0] and te are the same
            if MRXpath(te.getprevious()) == MRXpath(welts[0].getprevious()):
                continue

            # find the first previous element that also exists in working
            prev = closest_shared_previous(working,
                                           template,
                                           tmrx)
            # find the parent from working
            wparent = working.xpath(tmrx.parent().to_xpath())[0]
            if prev is None:
                # move to first child
                wparent.insert(0, welts[0])
                # remember position for wu
                pos = "<first>"
            else:
                # insert after prev
                wparent.insert(wparent.index(prev) + 1, welts[0])
                pos = MRXpath(prev)[-1].to_xpath()

            # generate a work unit
            # TODO(colin): support other order wu styles
            wus.append(
                E.wu(op="move",
                     id=tmrx.to_xpath(),
                     pos=pos)
                )

        else:
            # there is not a corresponding element in working

            # if it's a worker element we better just add it
#            if tmrx.to_noid_path() == "/status/worker":
#                welt = etree.Element(tmrx.name(), id=tmrx.id())
#                working.xpath("/status")[0].append(welt)
#                # but no need to go on and generate a wu
#                continue

            # add
            # if there is an add in actions, otherwise the
            # element should be added on a later run
            if not tmrx.to_xpath() in comp.actions()["add"]:
                continue

            wd = wds[tmrx.workername("/status")]

            wparent = None
            pmrx = tmrx.parent()
            create = []
#            while wparent is None:
#                try:
#                    wparent = working.xpath(pmrx.to_xpath())[0]
#                except IndexError:
#                    create.append([pmrx.name(), pmrx.id()])
#                    pmrx = pmrx.parent()
#                    if pmrx is None:
#                        raise Exception("Couldn't find any parent of {} while adding".format(tmrx.to_xpath()))
#            create.reverse()
#            for create_elt in create:
#                child = etree.Element(create_elt[0])
#                wparent.append(child)
#                if create_elt[1] is not None:
#                    child.set('id', create_elt[1])
#                wparent = child

            # can't add to a parent that doesn't exist
            try:
                wparent = working.xpath(tmrx.parent().to_xpath())[0]
            except IndexError:
                raise Exception("trying to add " + tmrx.to_xpath() +
                                " but its parent does not exist")

            # make a copy of the element to add
            add_elt = copy.deepcopy(te)
            # strip out any sub work units - they should be added later
            for subadd in add_elt.iterdescendants():
                sub_mrx = MRXpath(subadd)
                sub_mrx[:0] = tmrx
                del sub_mrx.rep[0]
                if wd.is_workunit(sub_mrx):
                    # is a workunit: remove
                    subadd.getparent().remove(subadd)

            # find the first previous element that also exists in working
            prev = closest_shared_previous(working,
                                           template,
                                           tmrx)

            if prev is None:
                # add as first child
                wparent.insert(0, add_elt)
                pos = "<first>"
            else:
                # add after wprev[0]
                wparent.insert(wparent.index(prev) + 1, add_elt)
                pos = MRXpath(prev)[-1].to_xpath()

            # generate a work unit
            wus.append(
                E.wu(copy.deepcopy(add_elt),
                     op="add",
                     id=tmrx.to_xpath(),
                     pos=pos)
                )

    # these are the droids you are looking for...
    return wus, working


def closest_shared_previous(working, template, xp):
    """find the closest sibling in working that is prior to xpath xp in template"""
    xp = MRXpath(xp)
    prevte = template.xpath(xp.to_xpath())[0].getprevious()
    while prevte is not None:
        prevwes = working.xpath(MRXpath(prevte).to_xpath())
        if prevwes:
            return prevwes[0]
        prevte = prevte.getprevious()
    return None

def strip_prefix(string, prefix = None):
    """Strip a prefix from a string.

    Arguments:
      string: string from which to strip prefix
      strip: prefix to remove
    Returns: stripped string
    Exceptions:
      - ValueError if string doesn't start with prefix
    """
    if prefix:
        # Remove prefix
        if string.startswith(prefix):
            return string[len(xpath):]
        else:
            raise ValueError(
                'Prefix "{}" not found in {}'.format(prefix, string)
                )
    else:
        return string

def add_prefix_elts(wrapelt, prefix = None):
    if prefix:
        pre_mrx = MRXpath(prefix)
        parent = None
        for item in pre_mrx.rep:
            if item[0] == '':
                continue
            elt = etree.Element(item[0])
            if len(item) > 1:
                elt.set('id', item[1])
            if parent is not None:
                parent.append(elt)
            else:
                top = elt
            parent = elt
        parent.append(wrapelt)
        return top
    return wrapelt

def get_fullpos(pos, parent_mrx):
    '''Return full position xpath from relative one.'''
    if pos == '<first>':
        return pos
    fullpos = copy.deepcopy(parent_mrx)
    fullpos.append(pos)
    return fullpos.to_xpath()

def _addpos_to_index(fullpos, stelt, add_map):
    if fullpos == '<first>':
        return 0
    # try to find the element corresponding to pos
    try:
        prev = stelt.xpath(fullpos)[0]
    except IndexError:
        # Uh oh - couldn't find element at pos. That probably
        # means it was supposed to be added by a previous work
        # unit that failed, or some add workunits are being applied
        # out of order.
        #
        # Check the add map
        if add_map is None:
            raise IndexError('No {} element found and no add_map'.format(fullpos))
        newpos = add_map.get(fullpos)
        if newpos:
            return _addpos_to_index(newpos, stelt, add_map)
        else:
            raise IndexError('No pos found after following add_map:\n'.format(pprint.pformat(add_map)))
    return prev.getparent().index(prev) + 1

def apply_wu(wu, stelt, prefix = None, add_map = None):
    """Apply a work unit to a status element.

    Arguments:
      wu: work unit element
      stelt: status element
    Returns:
      copy of status element with wu applied
    """
    if prefix:
        prefix = MRXpath(prefix)
    stelt = add_prefix_elts(copy.deepcopy(stelt), prefix)
    xpath = wu.get('id')
    op = wu.get('op')
    if op == 'add':
        parent_mrx = MRXpath(xpath).parent()
        parent_elt = stelt.xpath(parent_mrx.to_xpath())[0]
    else:
        tgt_elt = stelt.xpath(xpath)[0]
        parent_elt = tgt_elt.getparent()
    if op == 'add':
        # The element to add is in wu[0]
        pos = wu.get('pos')
        parent_elt.insert(
            _addpos_to_index(get_fullpos(pos, parent_mrx), stelt, add_map),
            copy.deepcopy(wu[0])
            )
    elif op == 'remove':
        parent_elt.remove(tgt_elt)
    elif op == 'datamod':
        tgt_elt.text = wu[0].text
    elif op == 'move':
        pos = wu.get('pos')
        if pos == '<first>':
            parent_elt.insert(0, tgt_elt)
        else:
            prev = stelt.xpath(strip_prefix(pos, strip))[0]
            parent_elt.insert(
                parent_elt.index(prev) + 1,
                tgt_elt
                )
    elif op == 'deepmod':
        mrx = MRXpath(xpath)
        orig_elt = stelt.xpath(xpath)[0]
        new_top = add_prefix_elts(copy.deepcopy(wu[0]), mrx.parent())
        new_elt = new_top.xpath(xpath)[0]
        wd = WorkerDescription(mrx.workername('/status'), '/status')

        for elt in orig_elt.iter(tag = etree.Element):
            elt_mrx = MRXpath(elt)
            # All workunit elements in orig_elt but not in new_elt
            # should be added back in (they were stripped when the
            # deepmod was created).
            #
            # TODO(colin): preserve the original order
#            print(elt_mrx.to_xpath())
            if wd.is_workunit(elt_mrx) and not new_top.xpath(elt_mrx.to_xpath()):
                new_elt.append(copy.deepcopy(elt))
        # now the deepmod element should represent the new state
        parent_elt.replace(orig_elt, new_elt)

    if prefix:
        return stelt.xpath(prefix.to_xpath())[0][0]
    else :
        return stelt

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
    def token_qstring(scanner, token):
        token = re.sub(r'\\(.)', r'\1', token)
        return "QSTRING", token[1:-1]
    def token_sep(scanner, token): return "SEP", token
    def token_bracket(scanner, token): return "BRACKET", token
    def token_op(scanner, token): return "OP", token
    def token_at(scanner, token): return "AT", token
    def token_name_or_id(scanner, token):
        if re.search(token, r'[\.]'):
            return "ID", token
        else:
            return "NAME", token

    scanner = re.Scanner([
            ("'(?:\\\\.|[^'])*'|\"(?:\\\\.|[^\"])*\"", token_qstring),
            (r"/", token_sep),
            (r"[\[\]]", token_bracket),
            (r"=", token_op),
            (r"@", token_at),
            (r"[\{\}\w\*\.]*", token_name_or_id),
            ])

    def __init__(self, path=None, att=None):
        self.set_path(path, att)

    def set_path(self, path, att=None):
        """Set representation based on ``path``

        calling options, elements::
          set_path(another_MRXpath_object)
          set_path("/standard/form[@id='frog']/xpath")
          set_path("/abbreviated/form[frog]/xpath")
          set_path(etree_element)

        attributes::
          set_path("/path/to/@attribute")
          set_path(etree_element,att="attribute_name")
        """
        self._clear_cache()
        if path is None:
            self.rep = []
            return

        if isinstance(path, list):
            self.rep = copy.deepcopy(path)
        elif isinstance(path, MRXpath):
            # clone another MRXpath
            self.rep = path.clone_rep()
        elif isinstance(path, str):
            # a string, break it up and store the pieces
            self.rep = []
            tokens, remainder = MRXpath.scanner.scan(path)
            if tokens[0][0] == "SEP":
                # rooted xpath, need an empty name to start
                working = [('NAME', '')]
            else:
                working = []
            for token in tokens:
                if token[0] == "SEP":
                    self.rep.append(self.tokens_to_rep(working))
                    working = []
                else:
                    working.append(token)
            self.rep.append(self.tokens_to_rep(working))
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
    def tokens_to_rep(self, tokens):
        if self.rep and self.is_attribute():
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
                return [name, idname]
            else:
                # expecting:
                #  [NAME,BRACKET,QSTRING|NAME|ID,BRACKET]
                # an element with an id passed as [something]
                if len(tokens) < 4:
                    raise Exception("expecting a 4 token sequence: " +
                                    "[NAME,BRACKET,QSTRING|NAME|ID,BRACKET]" +
                                    " got " +
                                    repr(tokens))
                if (tokens[2][0] != "NAME" and
                    tokens[2][0] != "QSTRING" and
                    tokens[2][0] != "ID"):
                    raise Exception("expecting a QSTRING, NAME or ID at " +
                                    "element 2 of " +
                                    str(tokens) + " got " + str(tokens[2]))
                idname = tokens[2][1]
                return [name, idname]
        elif tokens[0][0] == "AT":
            # an attribute, the next token should be the name
            return ["@" + tokens[1][1]]

    def clone_rep(self):
        """Return a clone of representation"""
        return copy.deepcopy(self.rep)

    def _clear_cache(self):
        """Clear any accumulated caches. Called when representation changes."""
        self.xp_cache = None

    def __repr__(self):
        return self.to_xpath()

    def __str__(self):
        return self.to_xpath()

    def __hash__(self):
        return str(self).__hash__()

    def __eq__(self, other):
        return self.to_xpath() == other.to_xpath()

    def __ne__(self, other):
        return self.to_xpath() != other.to_xpath()

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
        self._clear_cache()
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
        self._clear_cache()
        val = MRXpath(val)
        for i in val.rep:
            self.rep.append(i)

    def is_attribute(self):
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
        self._clear_cache()
        if len(self.rep) > 0:
            if self.rep[0][0] != '':
                self.rep.insert(0, [''])
        else:
            self.rep = [['']]
        return self

    def parent(self):
        """return MRXpath of parent element of rep or None"""
        if len(self.rep) == 2: return None
        return self[:len(self) - 1]

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

    def item(self, n):
        """return MRXpath object representing item n in the rep"""
        return MRXpath(self.rep[0:n + 1])

    def name(self):
        """return the name of the object"""
        if self.is_attribute():
            return self.rep[-1][0][1:]
        if len(self.rep) > 0:
            return self.rep[-1][0]
        return None

    def id(self, *args):
        """return id of the object or None"""
        if self.is_attribute():
            raise Exception("an attribute may not have an id")
        if args:
            self.rep[-1][1] = str(args[0])
        if self.is_element():
            if len(self.rep[-1]) > 1:
                return self.rep[-1][1]
            else:
                return None
        return None

    def quote_id(self, text, style = None):
        """Quote an id correctly.

        Args:
          style: one of 'bs', 'db', 'apos', 'quot'"""
        if style is None or style == 'bs':
            text = re.sub(r'\\',r'\\\\',text)
            text = re.sub(r'\'','\\\'',text)
            return text

    def to_xpath(self):
        """return xpath string"""
        if self.xp_cache is None:
            self.xp_cache = "/".join(["%s[@id='%s']" % (e[0], self.quote_id(e[1])) if len(e) == 2 else e[0] for e in self.rep])
        return self.xp_cache

    @functools.lru_cache(maxsize=None)
    def to_abbrev_xpath(self):
        """return Machination abbreviated xpath string"""
        return "/".join(["%s['%s']" % (e[0], self.quote_id(e[1])) if len(e) == 2 else e[0] for e in self.rep])

    @functools.lru_cache(maxsize=None)
    def to_noid_path(self):
        """return xpath with no ids"""
        return "/".join([e[0] for e in self.rep])

    @functools.lru_cache(maxsize=None)
    def to_xpath_list(self):
        """return list of xpath path elements"""
        return ["%s[@id='%s']" % (e[0], self.quote_id(e[1])) if len(e) == 2 else e[0] for e in self.rep]

    def strip_prefix(self, prefix):
        prefix = MRXpath(prefix)
        return self[len(prefix):].reroot()

    def workername(self, prefix=None):
        """return worker name for an xpath with prefix before worker element"""
        xpath = self
        if prefix is not None:
            xpath = self.strip_prefix(prefix)
        return xpath[0].id()

    def could_be_parent_of(self, target):
        """True if this MRXpath could be the XML-wise parent of path"""
        target = MRXpath(target)
        i = 0
        for myelt in self.rep:
            if len(target) <= i:
                return False
            tgtelt = target.rep[i]

            mytag = myelt[0]
            myid = None
            if len(myelt) > 1:
                myid = myelt[1]

            tgttag = tgtelt[0]
            tgtid = None
            if len(tgtelt) > 1:
                tgtid = tgtelt[1]

            if not (mytag == tgttag or mytag == '*'):
                return False
            if myid is not None:
                if not (myid == tgtid or myid == '*'):
                    return False
            i += 1
        return True


class Status(object):
    """Encapsulate a status XML element and functionality to manipulate it"""

    def __init__(self, statin, worker_prefix=None):
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

    def find_temp_desired(self, wus, template):
        working = Status(self)
        working.apply_wus(wus)
        working.order_like(template)
        return working

    def apply_wu(self, wu):
        """Apply a work unit to self.status"""
        pass

    def apply_wus(self, wus):
        """Iterate over wus, applying them to self.status"""
        for wu in wus:
            self.apply_wu(wu)

    def add(self, elt, mrx, position="<last>"):
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

    def order_after(self, mrx, afterid=["LAST"]):
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

    def __init__(self, workername, prefix=None):
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

        if isinstance(workername, str):
            self.workername = workername
            # try to find the description file
            descfile = os.path.join(utils.worker_dir(workername),
                                    "description.xml")
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
        mrx = MRXpath(xpath)[len(self.prefix):].reroot()

        # the worker element is always a workunit
        if len(mrx) == 1:
            return True

        if self.desc is not None:
            desc = self.get_description(xpath)
            if desc is not None and desc.get("{%s}wu" % self.nsmap["wu"]) == "1":
                return True
            else:
                return False
        else:
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

    def is_spanned(self, xpath):
        """True if all children are work units, False otherwise"""
        if self.desc is None:
            return False
        for cx in self.element_children(xpath):
            if not self.is_workunit(cx):
                return False
        return True

    def element_children(self, xpath):
        """Return xpaths for all children of xpath that are elements"""
        pass

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
        raise Exception("No work unit ancestors found for %s" % str(xpath))

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
                        'childdiff': set(),
                        'orderdiff': set()}
        self.byxpath = {}
        self.diff_to_action = {
            'left': 'remove',
            'right': 'add',
            'datadiff': 'datamod',
            'childdiff': 'deepmod',
            'orderdiff': 'reorder'
            }
        self.workcache = None
        self.compare()
        context.logger.dmsg('XMLCompare object created')

    @functools.lru_cache(maxsize=None)
    def actions(self):
        """return dictionary of sets as {action: {xpaths}}"""
        actions = {self.diff_to_action[s]: self.find_work() & self.bystate[s] for s in ['left', 'right', 'datadiff', 'childdiff', 'orderdiff']}
#        actions['all'] = actions['add'] | actions['remove'] | actions['datamod'] | actions['deepmod'] | actions['reorder']
        return actions

    def compare(self):
        """Compare the xpath sets and generate a diff dict"""

        for elt in self.leftxml.iter(tag=etree.Element):
            self.leftset.add(MRXpath(elt).to_xpath())
            for att in elt.keys():
                if att == "id":
                    continue
                self.leftset.add(MRXpath(elt, att=att).to_xpath())
        for elt in self.rightxml.iter(tag=etree.Element):
            self.rightset.add(MRXpath(elt).to_xpath())
            for att in elt.keys():
                if att == "id":
                    continue
                self.rightset.add(MRXpath(elt, att=att).to_xpath())

        self.universalset = self.leftset | self.rightset

#        self.leftset = {MRXpath(elt).to_xpath() for elt in self.leftxml.iter()}
#        self.rightset = {MRXpath(elt).to_xpath() for elt in self.rightxml.iter()}

        for xpath in self.leftset.difference(self.rightset):
            self.bystate['left'].add(xpath)
            self.byxpath[xpath] = 'left'

        for xpath in self.rightset.difference(self.leftset):
            self.bystate['right'].add(xpath)
            self.byxpath[xpath] = 'right'

        self.onesideset = self.bystate['left'] | self.bystate['right']
        self.bothsidesset = self.universalset - self.onesideset

        for xp in self.onesideset:
            p = MRXpath(xp).parent()
            if p.to_xpath() in self.bothsidesset:
                self._set_childdiff(p)

        self.find_diffs(self.leftset & self.rightset)

        self.order_diff()

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
                # only set datadiff if childdiff is not set
                if xpath not in self.bystate['childdiff']:
                    self.bystate['datadiff'].add(xpath)
                    self.byxpath[xpath] = 'datadiff'
                    self._set_childdiff(MRXpath(xpath).parent())

    def order_diff(self):
        # check child order for all xpaths that are in both sides
        for xp in self.bothsidesset:
            context.logger.dmsg('checking order for' + xp, 10)
            mrx = MRXpath(xp)
            if mrx.is_attribute():
                context.logger.dmsg('  attribute - ignoring', 10)
                continue
            # xp guaranteed(?) to exist in both by construction
            left_elt = self.leftxml.xpath(xp)[0]
            right_elt = self.rightxml.xpath(xp)[0]
            # An element is defined to have been reordered if it comes
            # after a different sibling in right cf. left
            left_prev = left_elt.getprevious()
            right_prev = right_elt.getprevious()
            # MRXpath objects can still be instantiated and compared
            # even if argument is None, so we don't need to worry about
            # the case where rcp and/or lcp are the first children
            if MRXpath(left_prev) != MRXpath(right_prev):
                self.bystate['orderdiff'].add(mrx.to_xpath())
                self._set_childdiff(mrx.parent())

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
        if mrx.to_xpath() in self.bystate['datadiff']:
            self.bystate['datadiff'].remove(mrx.to_xpath())
        self.byxpath[mrx.to_xpath()] = 'childdiff'
        p = mrx.parent()
        if p and p.to_xpath() not in self.bystate['childdiff']:
            self._set_childdiff(p)

    @functools.lru_cache(maxsize=100)
    def find_work(self, prefix="/status"):
        """return a set of all wus for all diff xpaths in all workers

        Args:
          prefix: xpath prefix to parent of worker elements.
        """

        diffs = self.bystate['datadiff'] | self.bystate['left'] | self.bystate['right'] | self.bystate['orderdiff']

        wi = len(MRXpath(prefix))

        wus = set()
        for x in diffs:
#            print(x)
            mrx = MRXpath(x)
            if mrx[wi].name() != 'worker':
                continue
            if len(mrx) < 2:
                continue
            wus.add(self.wds(prefix)[mrx[wi].id()].find_workunit(x))
        return wus

#        return {self.wds(prefix)[MRXpath(x)[wi].id()].find_workunit(x) for x in diffs if(len(MRXpath(x)) > 2)}

    def wds(self, prefix="/status"):
        """create a dictionary of WorkerDescriptions"""

        # find all the workers that are mentioned
        wnames = {w.get("id") for w in self.leftxml.xpath(prefix + "/worker")} | {w.get("id") for w in self.rightxml.xpath(prefix + "/worker")}

        return {n: WorkerDescription(n, prefix) for n in wnames}

    def wudeps(self, statedeps):
        """Combine state dependencies with worklist to find work dependencies.

        statedeps: an iterable of lxml ``Element``s from the profile. These
        should be in the form:

        .. code-block:: xml
          <dep id="something"
               src="/some/xpath"
               op="requires|excludes"
               tgt="/some/other/xpath"/>

        returns: a list (set?, iterable?) of dependencies between work
        units::

          [[wuA, wuB], [wuB, wuC], [wuD, wuE], ...]

        meaning workunit ``wuA`` depends on ``wuB``, ``wuB`` depends
        on ``wuC`` and so on. This output should be suitable for a
        (yet to be chosen or implemented) topological sort and may
        change later depending on implementation choice.
        """

#        wu_byxpath = {wu.get("id"): wu for wu in wus}

        topdeps = []
        for sdep in statedeps:
            # build a list of deps for topological sort just now
            # might change to generator approach later

            # translate src and tgt state xpaths to wu xpaths
            src_mrx = MRXpath(sdep.get("src"))
            tgt_mrx = MRXpath(sdep.get("tgt"))
            src_wuxpath = WorkerDescription(
                src_mrx.workername(prefix="/status"), prefix="/status"
                ).find_workunit(src_mrx.to_xpath())
            tgt_wuxpath = WorkerDescription(
                tgt_mrx.workername(prefix="/status"), prefix="/status"
                ).find_workunit(tgt_mrx.to_xpath())

            # find intended work operation for both wus
            if src_wuxpath in self.byxpath:
                src_action = self.diff_to_action[self.byxpath[src_wuxpath]]
            else:
                src_action = "none"
            if tgt_wuxpath in self.byxpath:
                tgt_action = self.diff_to_action[self.byxpath[tgt_wuxpath]]
            else:
                tgt_action = "none"

            # get to one of [src, tgt], [tgt, src] or nothing

            if sdep.get("op") == "requires":
                if src_action == "add" or src_action == "datamod" or\
                        src_action == "deepmod":

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
                    topdeps.append([tgt_wuxpath, src_wuxpath])

                elif src_action == "remove" and tgt_action == "remove":
                    topdeps.append([src_wuxpath, tgt_wuxpath])

                else:
                    # src_action == remove and tgt_action != remove
                    # OR src_action == none
                    continue

            elif sdep.get("op") == "excludes":
                if src_action == "add" or src_action == "datamod" or\
                        src_action == "deepmod":

                    # tgt_action better be remove or none
                    if tgt_action == "add" or tgt_action == "datamod" or\
                            src_action == "deepmod":
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
                    topdeps.append([tgt_wuxpath, src_wuxpath])

                elif src_action == "remove":
                    if tgt_action == "add":
                        # tgt_action deps src_action
                        topdeps.append([src_wuxpath, tgt_wuxpath])

                else:
                    # src_action == none
                    continue

            else:
                raise Exception("Don't understand dependency op '%s'"
                                % sdep.get("op"))

        return topdeps


class AssertionCompiler(object):
    """Compile XML assertions into a document"""

    def __init__(self, wc):
        """Instantiate XMLConstructor
        Args:
          wc: a machination.webclient.WebClient
        """
        self.doc = etree.ElementTree()
        self.wc = wc

    def compile(self, data):
        """Compile encapsulated in data

        Args:
          data: as returned by wc.call("GetAssertionList")
        """
        self.doc = etree.ElementTree()
        mpolicies = {}
        res_idx = {}
        mp_map = {}
        mps = set()
        for mp in data['mps']:
            mps.add(mp[-1])
        for hcp in data['hcs']:
            hc = hcp[-1]
            l = []
            for hid in hcp:
                if hid in mps:
                    l.append(hid)
            mp_map[hc] = l
        mpolicies['mp_map'] = mp_map
        mpolicies['data'] = data
        stack = data['attachments']
        stack.reverse()
        while stack:
            a = stack.pop()
            if a['ass_op'] == 'requires' or a['ass_op'] == 'excludes':
                # mpath requires ass_arg is equivalent to:
                #  mpath exists or create
                #  ass_arg exists or addlib
                #  id = "mpath requires ass_arg"
                #  /s/w[m]/deps/dep[$id]/@src hastext mpath
                #  /s/w[m]/deps/dep[$id]/@op hastext requires
                #  /s/w[m]/deps/dep[$id]/@tgt hastext ass_arg
                #
                #
                # mpath excludes ass_arg is equivalent to:
                #  mpath exists or create
                #  ass_arg notexists
                #  id = "mpath excludes ass_arg"
                #  /s/w[m]/deps/dep[$id]/@src hastext mpath
                #  /s/w[m]/deps/dep[$id]/@op hastext excludes
                #  /s/w[m]/deps/dep[$id]/@tgt hastext ass_arg
                if a['ass_op'] == 'requires':
                    ass_arg_op = 'addlib'
                elif a['ass_op'] == 'excludes':
                    ass_arg_op = 'delete'
                depid = '{} {} {}'.format(a['mpath'], 'requires', a['ass_arg'])
                new = [
                    {'mpath': '/status/worker[__machination__]/deps[{}]/@tgt'.format(depid),
                     'ass_op': 'hastext',
                     'ass_arg': a['ass_arg'],
                     'action_op': 'settext'},

                    {'mpath': '/status/worker[__machination__]/deps[{}]/@op'.format(depid),
                     'ass_op': 'hastext',
                     'ass_arg': a['ass_op'],
                     'action_op': 'settext'},
                    {'mpath': '/status/worker[__machination__]/deps[{}]/@src'.format(depid),
                     'ass_op': 'hastext',
                     'ass_arg': a['mpath'],
                     'action_op': 'settext'},
                    {'mpath': a['ass_arg'],
                     'ass_op': ass_arg_op,
                     'action_op': 'addlib'},
                    {'mpath': a['mpath'],
                     'ass_op': 'exists',
                     'action_op': 'create'}
                    ]
                stack.extend(new)
                continue
            if not self.try_assert(a):
                fname = "action_{}".format(a['action_op'])
                poldir = self.get_poldir(a, mpolicies)
                getattr(self, fname)(a, res_idx, poldir, stack)
        return self.doc, res_idx

    def try_assert(self, assertion):
        """test an assertion and return True or False"""
        mpath = MRXpath(assertion['mpath'])
        op = assertion['ass_op']
        arg = assertion['ass_arg']

        # tests
        if op == 'exists':
            if self.doc.getroot() is None:
                return False

            if self.doc.xpath(mpath.to_xpath()):
                return True
            else:
                return False
        elif op == 'notexists':
            if self.doc.getroot() is None:
                return True
            if self.doc.xpath(mpath.to_xpath()):
                return False
            else:
                return True
        elif op.startswith('hastext'):
            if self.doc.getroot() is None:
                return False

            nodes = self.doc.xpath(mpath.to_xpath())
            if len(nodes) == 0:
                return False
            if isinstance(nodes[0], etree._Element):
                # element
                content = nodes[0].text
            else:
                # attribute
                content = nodes[0]

            # now look at which of the hastext assertions this is
            if op == 'hastext':
                if content == arg:
                    return True
                else:
                    return False
            elif op == 'hastextfromlist':
                words = set(shlex.split(arg))
                if content in words:
                    return True
                else:
                    return False
            elif op == 'hastextmatching':
                if re.search(arg, content):
                    return True
                else:
                    return False

        # ordering assertions
        #
        # These aren't 'strong' enough to cause their respective
        # elements to come into existence. If either the src or tgt
        # elements doesn't exist then the assertion evaluates as true
        # (resulting in no action). If the src and or tgt must exist,
        # create seperate exists or hastext* assertions.
        elif op == 'first':
            if mpath.is_attribute():
                raise Exception("can't assert the order of attributes")
            elts = self.doc.xpath(mpath.to_xpath())
            if not elts:
                return True
            if elts[0] is elts[0].getparent()[0]:
                return True
            else:
                return False
        elif op == 'last':
            if mpath.is_attribute():
                raise Exception("can't assert the order of attributes")
            elts = self.doc.xpath(mpath.to_xpath())
            if not elts:
                return True
            if elts[0] is elts[0].getparent()[-1]:
                return True
            else:
                return False
        elif op == 'before':
            if mpath.is_attribute():
                raise Exception("can't assert the order of attributes")
            src_elts = self.doc.xpath(mpath.to_xpath())
            if not src_elts:
                return True
            src_idx = src_elts[0].index()
            tgt_mrx = MRXpath(arg)
            tgt_elts = self.doc.xpath(tgt_mrx.to_xpath())
            if not tgt_elts:
                return True
            tgt_idx = tgt_elts[0].index()
            if src_idx < tgt_idx:
                return True
            else:
                return False
        elif op == 'after':
            if mpath.is_attribute():
                raise Exception("can't assert the order of attributes")
            src_elts = self.doc.xpath(mpath.to_xpath())
            if not src_elts:
                return True
            src_idx = src_elts[0].index()
            tgt_mrx = MRXpath(arg)
            tgt_elts = self.doc.xpath(tgt_mrx.to_xpath())
            if not tgt_elts:
                return True
            tgt_idx = tgt_elts[0].index()
            if src_idx > tgt_idx:
                return True
            else:
                return False

        else:
            raise Exception("Assertion op '{}' unknown".format(op))

    def get_poldir(self, assertion, mpolicies):
        """Find which direction a policy points
        """
        if('mpolicy' in assertion):
            return assertion['mpolicy']
        pols = self.get_mpolicy(assertion['hc_id'], mpolicies)
        pols.reverse()
        direction = 0
        for pol in pols:
            pol_mrx = MRXpath(pol['mpath'])
            if pol_mrx.could_be_parent_of(assertion['mpath']):
                direction = pol['policy_direction']
                break
        return direction

    def get_mpolicy(self, hc, mpolicies):
        """Find the merge policies for a given hc
        """
        data = mpolicies['data']
        mplist = mpolicies['mp_map'][hc]

        pols = []
        for mp in mplist:
            if mp in data['mpolicy_attachments']:
                pols.extend(data['mpolicy_attachments'][mp])
        return pols

    def policy_check(self, mpath, a, res_idx, poldir):
        """Check to see if action should be done according to policy

        NOT IN USE YET
        """

        mpath = MRXpath(mpath)

    def dep_assertions(self, src, op, tgt):
        """Return a list of assertions representing dependency"""
        depid = '{} {} {}'.format(src, op, tgt)
        depid = hashlib.sha256(depid.encode('utf8')).hexdigest()
        deppath = '/status/worker[__machination__]/deps/dep[{}]'.format(depid)
        return [
            {'mpath': '{}/@tgt'.format(deppath),
             'ass_op': 'hastext',
             'ass_arg': tgt,
             'action_op': 'settext',
             'mpolicy': 0},
            {'mpath': '{}/@op'.format(deppath),
             'ass_op': 'hastext',
             'ass_arg': op,
             'action_op': 'settext',
             'mpolicy': 0},
            {'mpath': '{}/@src'.format(deppath),
             'ass_op': 'hastext',
             'ass_arg': src,
             'action_op': 'settext',
             'mpolicy': 0},
            ]

    def action_create(self, a, res_idx, poldir, stack,
                      record_index=True):
        """Create an element or attribute"""

        mpath = MRXpath(a['mpath'])
        lineage = [mpath]
        lineage.extend(mpath.ancestors())
        lineage.reverse()
        pelt = self.doc

        # test to see if a notexists takes precedence
        for p in lineage:
            if p.to_xpath() in res_idx:
                if poldir == -1:
                    # see if the node doesn't exist because of a
                    # previous "notexists" on mpath or parents
                    if res_idx[p.to_xpath()]['ass_op'] == 'notexists':
                        return
                elif poldir == 0:
                    # check there is no mandatory notextists for mpath
                    # or parents
                    if(res_idx[p.to_xpath()]['ass_op'] == 'notexists' and
                       res_idx[p.to_xpath()]['is_mandatory'] == "1"):
                        return

        # now we should go ahead and create the node
        for p in lineage:
            # deal with the root node first if it doesn't exist
            if pelt is self.doc and self.doc.getroot() is None:
                new = etree.Element(p.name())
                self.doc._setroot(new)
                pelt = new
                continue

            children = pelt.xpath(p.to_xpath())
            if children:
                # node p already exists
                pelt = children[0]
                continue

            context.logger.dmsg('creating element {}'.format(
                    p.to_abbrev_xpath()))
            if p.is_attribute():
                pelt.set(p.name(), "")
                # can't continue after an attribute
                break
            else:
                new = etree.Element(p.name())
                if p.id():
                    new.set('id', p.id())
                pelt.append(new)
                if p.name() == 'machinationFetcherBundle':
                    # add a dep for the bundle
                    src = p.to_xpath()
                    tgt = "/status/worker[fetcher]/bundle['{}']".format(p.quote_id(p.id()))
                    stack.extend(self.dep_assertions(src, 'requires', tgt))
                pelt = new

        if record_index:
            res_idx[mpath.to_xpath()] = a

    def action_settext(self, a, res_idx, poldir, stack):
        """Set the text of an element or attribute"""

        mpath = MRXpath(a['mpath'])
        lineage = [mpath]
        lineage.extend(mpath.ancestors())
        lineage.reverse()

        # find the node to be set
        if self.doc.getroot() is None:
            nodes = []
        else:
            nodes = self.doc.xpath(mpath.to_xpath())

        # test to see if a notexists takes precedence
        for p in lineage:
            if p.to_xpath() in res_idx:
                if poldir == -1:
                    # see if the node doesn't exist because of a
                    # previous "notexists" on mpath or parents
                    if res_idx[p.to_xpath()]['ass_op'] == 'notexists':
                        return
                    # Check if the node has some text already - abort
                    # if it does.
                    if nodes:
                        if (mpath.is_element() and
                            nodes[0].text is not None and
                            nodes[0].text != ''):
                            return
                        elif (mpath.is_attribute() and
                              nodes[0] != ''):
                            return
                elif poldir == 0:
                    # check there is no mandatory notextists for mpath
                    # or parents
                    if(res_idx[p.to_xpath()]['ass_op'] == 'notexists' and
                       res_idx[p.to_xpath()]['is_mandatory'] == "1"):
                        return
                    # check if the node has some mandatory text
                    # already, abort if it does
                    if(nodes and
                       res_idx[p.to_xpath()]['is_mandatory'] == "1" and
                       res_idx[p.to_xpath()]['ass_op'].startswith('hastext')):
                        return

        # create the element if it doesn't already exist
        if len(nodes) == 0:
#            print("\ncalling create {}\n".format(mpath.to_abbrev_xpath()))
            self.action_create(a,
                               res_idx,
                               poldir,
                               stack,
                               record_index=False)
            nodes = self.doc.xpath(mpath.to_xpath())

        # default to the assertion argument if the action argument is
        # missing
        content = a.get('action_arg')
        if content is None:
            content = a.get('ass_arg')
        if content is None:
            content = ''
        context.logger.dmsg('setting text of {} to {}'.format(
                mpath.to_abbrev_xpath(), content))

        if mpath.is_element():
            # element: clear and set text
            nodes[0].tail = None
            for child in nodes[0].iterchildren():
                nodes[0].remove(child)
            nodes[0].text = content
        else:
            # attribute: need to set it from the parent
            pelt = self.doc.xpath(mpath.parent().to_xpath())[0]
            pelt.set(mpath.name(), content)

        res_idx[mpath.to_xpath()] = a

    def action_delete(self, a, res_idx, poldir, stack):
        """Delete an element or attribute"""

        if poldir == -1:
            # never delete an existing node if remote wins
            return

        mpath = MRXpath(a['mpath'])
        lineage = [mpath]
        lineage.extend(mpath.ancestors())
        lineage.reverse()

        if poldir == 1:
            # always delete if local wins
            self.delete_mpath(mpath)
            self.res_idx[mpath.to_xpath()] = a
            return

        # test to see if a mandatory creation instruction (exists, hastext, ...)
        # takes precedence
        for p in lineage:
            if p.to_xpath() in res_idx:
                if((res_idx[p.to_xpath()]['ass_op'] == 'exists' or
                    res_idx[p.to_xpath()]['ass_op'].startswith('hastext')) and
                   res_idx[p.to_xpath()]['is_mandatory'] == "1"):
                    return
        # no mandatory creation instruction
        self.delete_mpath(mpath)
        self.res_idx[mpath.to_xpath()] = a

    def delete_mpath(mpath):
        """Delete an mpath (MRXPath) from the document"""
        if mpath.is_element():
            elt = self.doc.xpath(mpath.to_xpath())[0]
            elt.getparent().remove(elt)
        else:
            # an attribute
            pelt = self.doc.xpath(mpath.parent().to_xpath())[0]
            del pelt.attributes[mpath.name()]


    def action_addlib(self, a, res_idx, poldir, stack):
        """Add a library item"""

        # don't try to add a library item we've added before
        itemidtext = '{} {} {}'.format(a['mpath'], a['ass_op'], a['ass_arg'])
        itemid = hashlib.sha256(itemidtext.encode('utf8')).hexdigest()
        itemxp = '/status/__scratch__/libAdded/item[@id="{}"]'.format(itemid)
        if len(self.doc.xpath(itemxp)) != 0:
            context.logger.dmsg("seen {} before".format(itemidtext))
            return

        libs = self.doc.xpath('/status/__scratch__/libPath/item')
        libpath = [x.text for x in libs]

        # look up the library item and get an assertion list
        ainfo = self.wc.call('GetLibraryItem', a, libpath)
        alist = ainfo['assertions']
        if ainfo['found'] is None:
            # couldn't find the library item
            context.logger.wmsg("failed to find library item for" +
                                itemidtext +
                                "\nlibrary path:\n" +
                                pprint.pformat(libpath))
            return

        # add the assertions to the stack
        alist.reverse()
        stack.extend(alist)

        # remember that we added this library item
        self.action_settext({'mpath': itemxp,
                             'ass_op': 'hastext',
                             'ass_arg': ainfo['found'],
                             'action_op': 'settext',
                             'is_mandatory': '1',
                            },
                           res_idx,
                           poldir,
                           stack)

    def action_reorderfirst(self, a, res_idx, poldir, stack):
        """Make an element first amongst its siblings"""

        mpath = MRXpath(a['mpath'])

        # Find the node to be moved. It must exist - we wouldn't have
        # got to this action if not.
        node = self.doc.xpath(mpath.to_xpath())[0]

        # test to see if a reorderlast or reorderafter takes precedence
        if poldir == -1:
            # see if the node is in the wrong place because of a
            # previous ordering instruction
            if(res_idx[mpath.to_xpath()]['ass_op'] == 'reorderlast' or
               res_idx[mpath.to_xpath()]['ass_op'] == 'reorderafter'):
                return
        elif poldir == 0 and res_idx[mpath.to_xpath()]['is_mandatory'] == "1":
            # check there is no mandatory notextists for mpath
            if(res_idx[mpath.to_xpath()]['ass_op'] == 'reorderlast' or
               res_idx[mpath.to_xpath()]['ass_op'] == 'reorderafter'):
                return

        # No policy or mandatory overrides - go on and move.
        node.getparent().insert(0,node)
        self.res_idx[mpath.to_xpath()] = a

    def action_reorderlast(self, a, res_idx, poldir, stack):
        """Make an element last amongst its siblings"""

        mpath = MRXpath(a['mpath'])

        # Find the node to be moved. It must exist - we wouldn't have
        # got to this action if not.
        node = self.doc.xpath(mpath.to_xpath())[0]

        # test to see if a reorderfirst or reorderbefore takes precedence
        if poldir == -1:
            # see if the node is in the wrong place because of a
            # previous ordering instruction
            if(res_idx[mpath.to_xpath()]['ass_op'] == 'reorderfirst' or
               res_idx[mpath.to_xpath()]['ass_op'] == 'reorderbefore'):
                return
        elif poldir == 0 and res_idx[mpath.to_xpath()]['is_mandatory'] == "1":
            # check there is no mandatory notextists for mpath
            if(res_idx[mpath.to_xpath()]['ass_op'] == 'reorderfirst' or
               res_idx[mpath.to_xpath()]['ass_op'] == 'reorderbefore'):
                return

        # No policy or mandatory overrides - go on and move.
        node.getparent().append(node)
        self.res_idx[mpath.to_xpath()] = a

    def action_reorderafter(self, a, res_idx, poldir, stack):
        """Move an element after a specified sibling"""

        mpath = MRXpath(a['mpath'])

        # test to see if a reorderfirst or reorderbefore takes precedence
        if (
            poldir == -1 or
            (
             poldir == 0 and
             res_idx[mpath.to_xpath()]['is_mandatory'] == "1"
            )
           ):
            # see if the node is in the wrong place because of a
            # previous ordering instruction
            if(
               res_idx[mpath.to_xpath()]['ass_op'] == 'reorderfirst' or
               (
                res_idx[mpath.to_xpath()]['ass_op'] == 'reorderbefore' and
                res_idx[mpath.to_xpath()]['ass_arg'] == a['ass_arg']
               )
              ):
                return

        # Find the node to be moved. It must exist - we wouldn't have
        # got to this action if not.
        node = self.doc.xpath(mpath.to_xpath())[0]
        # same goes for the target element
        tmrx = MRXpath(mpath)
        tmrx.id(a['ass_arg'])
        tnode = self.doc.xpath(tmrx.to_xpath())[0]

        # No policy or mandatory overrides - go on and move.
        p = node.getparent()
        p.insert(p.index(tnode)+1,node)
        self.res_idx[mpath.to_xpath()] = a

    def action_reorderbefore(self, a, res_idx, poldir, stack):
        """Move an element before a specified sibling"""

        mpath = MRXpath(a['mpath'])

        # test to see if a reorderfirst or reorderbefore takes precedence
        if (
            poldir == -1 or
            (
             poldir == 0 and
             res_idx[mpath.to_xpath()]['is_mandatory'] == "1"
            )
           ):
            # see if the node is in the wrong place because of a
            # previous ordering instruction
            if(
               res_idx[mpath.to_xpath()]['ass_op'] == 'reorderlast' or
               (
                res_idx[mpath.to_xpath()]['ass_op'] == 'reorderafter' and
                res_idx[mpath.to_xpath()]['ass_arg'] == a['ass_arg']
               )
              ):
                return

        # Find the node to be moved. It must exist - we wouldn't have
        # got to this action if not.
        node = self.doc.xpath(mpath.to_xpath())[0]
        # Same goes for the target element.
        tmrx = MRXpath(mpath)
        tmrx.id(a['ass_arg'])
        tnode = self.doc.xpath(tmrx.to_xpath())[0]

        # No policy or mandatory overrides - go on and move.
        p = node.getparent()
        p.insert(p.index(tnode),node)
        self.res_idx[mpath.to_xpath()] = a
