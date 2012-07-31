import pprint
import sys
import os
from lxml import etree
from machination.xmldata import from_xml, to_xml
from machination import context
#from machination.xmltools import pstring
from machination.cosign import CosignPasswordMgr, CosignHandler

try:
    import urllib.request as urllib_request
    import http.client as http_client
except ImportError:
    import urllib2 as urllib_request
    import httplib as http_client

class HTTPSClientAuthHandler(urllib_request.HTTPSHandler):
    def __init__(self, key, cert):
        urllib_request.HTTPSHandler.__init__(self)
        self.key = key
        self.cert = cert
    def https_open(self, req):
        #Rather than pass in a reference to a connection class, we pass in
        # a reference to a function which, for all intents and purposes,
        # will behave as a constructor
        return self.do_open(self.getConnection, req)
    def getConnection(self, host, timeout=None):
        return http_client.HTTPSConnection(host,
                                           key_file=self.key,
                                           cert_file=self.cert)

class WebClient(object):
    """Machination WebClient"""

    def __init__(self, service_id, obj_type, cred=None):
        self.service_id = service_id
        self.obj_type = obj_type
        self.cred = cred
        try:
            service_elt = context.machination_worker_elt.xpath(
                'services/service[@id="{}"]'.format(service_id)
                )[0]
        except IndexError:
            raise Exception("service id '{}' not found in desired_status".format(service_id))
        tmp_auth = service_elt.xpath(
            'authentication[@id="{}"]'.format(self.obj_type)
            )
        if not tmp_auth:
            tmp_elt = etree.Element('authentication')
            tmp_elt.set('id', self.obj_type)
            if self.obj_type == 'person':
                tmp_elt.set("type", "basic")
            elif self.obj_type == 'os_instance':
                tmp_elt.set("type", "cert")
            tmp_auth=[tmp_elt]
        self.authen_elt = tmp_auth[0]
        self.authen_type = self.authen_elt.get("type")
        self.url = '{}/{}'.format(
            service_elt.xpath('hierarchy/@id')[0],
            self.authen_type
            )
        self.encoding = 'utf-8'
        self.l = context.logger
        self.cookie_file = os.path.join(context.status_dir(), 'cookies.txt')
        self.cookie_jar = None
        handlers = []
        if self.authen_type == 'cosign':
            self.cookie_jar = http.cookiejar.MozillaCookieJar(
                self.cookie_file
                )
            handlers.append(
                self.cookie_jar
                )
            handlers.append(
                CosignHandler(
                    self.authen_elt.get('cosignLoginPage'),
                    self.cookie_jar,
                    CosignPasswordMgr(),
                    save_cookies = True
                    )
                )
        elif self.authen_type == 'cert':
            handlers.append(
                HTTPSClientAuthHandler(
                    os.path.join(context.conf_dir(),
                                 'services',
                                 self.service_id,
                                 'myself.key'),
                    os.path.join(context.conf_dir(),
                                 'services',
                                 self.service_id,
                                 'myself.crt')
                    )
                )
        elif self.authen_type == 'debug':
            if not self.cred:
                username = self.authen_elt.get('username')
                if username is None:
                    username = input('username: ')
                self.cred = {'username': username}
            self.url = '{}/{}:{}'.format(self.url,
                                         self.obj_type,
                                         self.cred.get('username'))

        self.opener = urllib_request.build_opener(*handlers)

    def call(self, name, *args):
        print("calling " + name + " on " + self.url)
        call_elt = etree.Element("r", call=name)
        for arg in args:
            call_elt.append(to_xml(arg))
        print(etree.tostring(call_elt, pretty_print=True))

        # construct and send a request
        r = urllib_request.Request(
            self.url,
            etree.tostring(call_elt, encoding=self.encoding),
            {'Content-Type':
                 'application/x-www-form-urlencoded;charset=%s' % self.encoding}
            )
        urllib_request.install_opener(self.opener)
        f = urllib_request.urlopen(r)
        s = f.read().decode(self.encoding)
#        print("got:\n" + s)
        elt = etree.fromstring(s)
        if elt.tag == 'error':
            raise Exception('error at the server end:\n' + elt[0].text)
        ret = from_xml(elt)
        return ret

    def help(self):
        return self.call("Help")
