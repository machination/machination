from lxml import etree
import msilib

version = '1.2.3'
out = 'machination-core-extras.wsx'

wsx = etree.parse('packaging/machination-core-extras-template.xml')
top = wsx.getroot()

for elt in top.iter(tag=etree.Element):
    for att in elt.attrib:
        if elt.get(att) == 'REP-VERSION': elt.set(att, version)
        if elt.get(att) == 'REP-GUID': elt.set(att, msilib.gen_uuid())

with open(out, "w") as f:
    f.write(etree.tostring(wsx).decode())
