#!/usr/bin/python

import sys
import cgi
import cgitb
import time
from M2Crypto import m2, RSA, X509, BIO, ASN1

cgitb.enable(display=1)

# Raise an error on Content Length larger than 2 MB (prevent upload DoS)
cgi.maxlen = 2 * 1024 * 1024

# FIXME! Should come from machination context
cacertfile = "/var/sixkts/server.crt"
cakeyfile = "/var/sixkts/server.key"

# Cert lifetime in seconds (~5 years)
lifetime = 157788000


def fileOutput(name, data):
    contenttype = """Content-Type:application/octet-stream;
Content-Disposition:attachment;filename="%s"\n\n""" % (name)

    print "%s\n%s" % (contenttype, data)


def htmlOutput(message):
    contenttype = "Content-Type:text/html\n"

    print """%s\n
<html><body>
<p>%s</p>
</body></html>""" % (contenttype, message, )


def main():
    form = cgi.FieldStorage()

    # form hasn't been submitted yet
    if not form:
        message = """
    <form action="/cgi-bin/sendcert/index.cgi" method="POST" enctype="multipart/form-data">
    <input type="file" name="file">
    <input type="submit">
    <input type="reset">
    </form>
    """
        htmlOutput(message)

    # form has ben submitted
    elif "file" in form:
        fileitem = form['file']

        # Test if a file was uploaded
        if fileitem.filename:

            # Cut the current extension off the filename and append .pem
            certname = fileitem.rpartition('.')[0] + ".pem"

            # Load the CSR object from the submitted file
            csrdata = fileitem.file.read()
            try:
                csr = X509.load_request_string(csrdata)
            except X509.X509Error:
                print "Status: 404 Not Found\n\n"
                sys.exit()

            # Load the CA cert and key
            try:
                cacert = X509.load_cert(cacertfile)
                cakey = RSA.load_key(cakeyfile, callback=lambda passphrase: '')
            except X509.X509Error:
                print "Status: 404 Not Found\n\n"
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
            # FIXME! Use an incrementing unique serial number!
            cert.set_serial_number(2)

            # Sign the cert
            cert.set_issuer_name(cacert.get_subject())
            cert.sign(capub, md='sha256')

            # 'Display' the cert as html
            fileOutput(certname, cert.as_pem())

        else:
            message = 'No file specified for upload.'
            htmlOutput(message)

if __name__ == "__main__":
    main()
