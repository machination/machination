from lxml import etree


class WorkerDescription:
    """Work with worker descriptions"""

    nsmap = {
        'rng': 'http://relaxng.org/ns/structure/1.0',
        'wu': 'https://github.com/machination/ns/workunit'
        }

    def load(self, description):
        "load worker description"

        self.desc = etree.parse(description)

    def workUnits(self):
        "return a list of valid work unit paths"

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
