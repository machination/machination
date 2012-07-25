"""Interchange between python data and Machination transport XML.

Machination transport XML:

None (undef in perl):
  <u/>

String:
  <s>text</s>

List (array in perl):
  <a>
    <s>item 1</s>
    <s>item 2</s>
    ...
  </a>

Dictionary (hash in perl):
  <h>
    <k id='key1'>
      <s>value 1</s>
    </k>
    ...
  </h>

"""
from lxml import etree


def to_xml(thing):
    """Return etree element representing thing."""
    elt = etree.Element("tmp")

    if thing is None:
        elt.tag = 'u'
    elif isinstance(thing, str) or isinstance(thing, int):
        elt.tag = "s"
        elt.text = str(thing)
    elif isinstance(thing, list):
        elt.tag = "a"
        for item in thing:
            elt.append(to_xml(item))
    elif isinstance(thing, dict):
        elt.tag = "h"
        for k, v in thing.items():
            etree.SubElement(elt, "k", id=k).append(to_xml(v))
    else:
        raise Exception(
            "don't know how to turn a {} into XML".format(type(thing))
            )

    return elt


def from_xml(elt):
    """Return python data represented by elt."""
    if isinstance(elt, str):
        return elt

    if elt.tag == 'u':
        obj = None
    elif elt.tag == 's':
        obj = elt.text
    elif elt.tag == 'a':
        obj = []
        for child in elt.iterchildren(tag=etree.Element):
            obj.append(from_xml(child))
    elif elt.tag == 'h':
        obj = {}
        for kelt in elt.iterchildren(tag='k'):
            k = kelt.get('id')
            obj[k] = from_xml(kelt[0])

    return obj
