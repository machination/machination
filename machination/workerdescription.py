from lxml import etree

class WorkerDescription:
    """Work with worker descriptions"""

    nsmap = {
        'rng':'http://relaxng.org/ns/structure/1.0',
        'wu':'https://github.com/machination/ns/workunit'
        }

    def load(self,description):
        "load worker description"

        self.desc = etree.parse(description)

    def workUnits(self):
        "return a list of valid work unit paths"

        wuels = self.desc.xpath(
            "//rng:element[@wu:wu='1']",
            namespaces=nsmap)
        wus = []
        for elt in wuels:
            path = [elt.get("name")]
            while elt.getparent() :
                if elt.tag == '{' + nsmap['rng'] + '}' + 'element' :
                    path.append(elt.get("name")
        return path
            
