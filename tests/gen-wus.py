from machination.xmltools import XMLCompare
from machination.xmltools import generate_wus
from machination.xmltools import mc14n
import sys
from lxml import etree
import pprint

left = mc14n(etree.parse(sys.argv[1]))
right = mc14n(etree.parse(sys.argv[2]))

#print(etree.tostring(left, pretty_print = True).decode())
#print(etree.tostring(right, pretty_print = True).decode())

deps = etree.fromstring('<status><deps/></status>')[0]
comp = XMLCompare(left, right)
wudeps = comp.wudeps(deps.iterchildren(tag=etree.Element))

pprint.pprint(comp.bystate)
pprint.pprint(comp.actions())
pprint.pprint(comp.find_work())

wus, working = generate_wus(comp.find_work(), comp)

for wu in wus:
    print(etree.tostring(wu, pretty_print = True).decode())

print(etree.tostring(working, pretty_print = True).decode())
