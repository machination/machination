#!/usr/bin/python

import sys
import cgi
import cgitb
import time
import os
import re
from M2Crypto import m2, RSA, X509, BIO, ASN1
from machination import context
from machination.xmltools import WebClient
import psycopg2
from lxml import etree

cgitb.enable(display=1)

# Raise an error on Content Length larger than 2 MB (prevent upload DoS)
cgi.maxlen = 2 * 1024 * 1024

# FIXME! Should come from machination context
#cacertfile = "/var/sixkts/server.crt"
#cakeyfile = "/var/sixkts/server.key"

wxpath = '/status/worker[@id="__server__"]'
config_xpath = '{}/certgi'.format(wxpath)
try:
    config_elt = context.desired_status.xpath(config_xpath)[0]
except IndexError:
    htmlOutput('ERROR: no config element defined at {}.'.format(config_xpath))
    exit(0)
cacertfile = config_elt.xpath('ca')[0]['certfile']
cakeyfile = config_elt.xpath('ca')[0]['keyfile']

# Cert lifetime in seconds (~5 years)
try:
    lifetime = config_elt.xpath('lifetime')[0].text
except IndexError:
    lifetime = 157788000

# database params
try:
    dcon_elt = config_elt.xpath('db')[0]
except IndexError:
    htmlOutput('ERROR: no connection element defined at {}.'.format(dbcon_xpath))
    exit(0)
cred_elt = etree.parse(config_elt['credentials']).getroot()


def fileOutput(name, data):
    contenttype = """Content-Type:application/octet-stream;
Content-Disposition:attachment;filename="%s.crt"\n\n""" % (name)

    print(("%s\n%s" % (contenttype, data)))


def htmlOutput(message):
    print(("""Content-Type:text/html\n\n
<html><body><p>%s</p></body></html>""" % (message)))


def sign_csr(csr, serial):
    # Load the CA cert and key
    try:
        cacert = X509.load_cert(cacertfile)
        cakey = RSA.load_key(cakeyfile, callback=lambda passphrase: cred_elt.xpath('/cred/caKey/passphrase/text()'))
    except X509.X509Error:
        htmlOutput("No CA available for signing.")
        sys.exit()

    # Create an X509 CA object from cert and key
    capub = cacert.get_pubkey()
    capub.assign_rsa(cakey, capture=False)

    # Create an X509 cert object from csr
    csrpub = csr.get_pubkey()
    cert = X509.X509()

    cert.set_pubkey(csrpub)
    cert.set_version(0)

    # Set start and end times for cert validity
    now = int(time.time())
    notbefore = ASN1.ASN1_UTCTIME()
    notbefore.set_time(now)
    notafter = ASN1.ASN1_UTCTIME()
    notafter.set_time(now + lifetime)
    cert.set_not_before(notbefore)
    cert.set_not_after(notafter)

    # Set cert subject and serial number
    subject = csr.get_subject()
    cert.set_subject_name(subject)
    cert.set_serial_number(serial)

    # Sign the cert
    cert.set_issuer_name(cacert.get_subject())
    cert.sign(capub, md='sha256')

    return cert


def main():
    form = cgi.FieldStorage()

    # form hasn't been submitted yet
    if not form:
        message = """
    <form action="/cgi-bin/sendcert/index.cgi"
     method="POST" enctype="multipart/form-data">
    <input type="file" name="file">
    <input type="submit">
    <input type="reset">
    </form>
    """
        htmlOutput(message)

    # form has ben submitted
    elif "file" in form:

        joiner = os.environ.get('REMOTE_USER',None)
        if not joiner:
            htmlOutput("ERROR: You must authenticate to use this script.")
            exit(0)

        # can be either a 'file submit' from a browser, or a urlencoded string
        fileitem = form["file"]
        if fileitem.file:
            csrdata = fileitem.file.read()
        else:
            csrdata = fileitem.value

        try:
            csr = X509.load_request_string(csrdata)
        except X509.X509Error:
            htmlOutput("ERROR: No valid CSR data received.")
            exit(0)

        # get object type and name
        subject_name = csr.get_subject()
        obj_typename, obj_name = subject_name.split(":")
        obj_id = int(wc.call('EntityId', obj_typename, obj_name))
        if obj_id < 1:
            # object does not exist - should have been created by
            # client script
            htmlOutput("ERROR: object {} does not exist.".
                       format(subject_name))
            exit(0)

        # Now we need to start looking up things in the hierarchy -
        # make a Webclient.

        wcurl = context.desired_status.xpath(wxpath + '/webclient/@url')[0]
        # TODO(colin): change over to cert or user+pass
        wc = WebClient(wcurl, 'eggy')

        # We'll need settext permission on the object's 'reset_trust' field
        req = {
            'channel_id': wc.call('HierarchyChannel'),
            'op': 'settext'
            'mpath': '/contents/{}[{}]/field[reset_trust]'.format(obj_typename, obj_id),
            'owner': joiner,
            'approval': []
            }
        allowed = wc.call('ActionAllowed', req, '/system/special/authz/objects')
        if allowed != 1:
            htmlOutput('ERROR: user "{}" is not alowed to reset the trust link for {}:{}'.format(joiner, obj_typename, obj_name))
            exit(0)

        # check that csr conforms to our certificate policy
        check_csr(csr)

        # now we've got permission to do something

        dbcon = psycopg2.connect(host=dcon_elt['host'],
                                 port=dcon_elt['port'],
                                 database=dcon_elt['database'],
                                 user=cred_elt.xpath('/cred/db/username/text()'),
                                 password=cred_elt.xpath('/cred/db/password/text()'))
        # This script should not live long enough to worry about
        # more than one cursor - just create a global one.
        cur = dbcon.cursor()
        cur.execute("select nextval(%s)", ('certs'))
        serial = cur.fetchone()[0]
        cert = sign_csr(csr, serial)
        # revoke old row/cert
        cur.execute("update certs set type='R' where name=%s and type='V'",
                    (subject_name))
        # add new row/cert
        cur.execute("insert into certs (serial, name, type, expiry_date) " +
                    "values (%s,%s,'V',%s)",
                    (serial, subject_name, cert.get_not_before()))
        cur.commit()

        # hand the signed certificate back
        fileOutput(csr.get_subject().CN, cert.as_pem())

def check_csr(csr):
    subj = csr.get_subject()
    for node in config_elt.xpath('clientDNForm/node'):
        name = getattr(subj,node.get('id'))
        if node.get('check') == 'equal':
            if node.get('value') != name:
                return False
        elif node.get('check') == 're':
            ch = re.compile(node.get('value'))
            if not ch.search(name):
                return False

    return True

if __name__ == "__main__":
    main()
