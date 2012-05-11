from M2Crypto import m2, RSA, X509, EVP, ASN1
from collections import namedtuple
import socket
import urllib
import urllib2
import time


def make_key(bits=2048):

    return RSA.gen_key(bits, m2.RSA_F4)


def crt_subject(CN=None, Email=None, OU=None, O=None, L=None, ST=None, C=None):

    emailAddress = Email

    localvars = vars()

    info = X509.X509_Name(m2.x509_name_new())

    Subject = namedtuple('Subject', 'emailAddress Email CN OU O L ST C')
    subject = Subject(**localvars)

    for name in subject._fields:
        value = getattr(subject, name)

        info.add_entry_by_txt(field=name, entry=value, type=0x1000,
                              len=-1, loc=-1, set=0)

    return info


def make_csr(CN=socket.getfqdn(), key=make_key(), alg="sha256",
             Email="machination@machination",
             OU="Machination OU", O="Machination Org",
             L="Machination City", ST="Machination State",
             C="MachinationLand"):

    csr = X509.Request()

    csr.set_subject_name(crt_subject(CN, Email, OU, O, L, ST, C))

    pub = EVP.PKey(md=alg)
    pub.assign_rsa(key, capture=False)

    csr.set_pubkey(pub)
    csr.sign(pub, md=alg)

    return csr


def make_ca(CN=socket.getfqdn(), key=make_key(), alg="sha256",
             Email="machination@machination",
             OU="Machination OU", O="Machination Org",
             L="Machination City", ST="Machination State",
             C="MachinationLand", lifetime=20 * 86400 * 365):

    pub = EVP.PKey(md=alg)
    pub.assign_rsa(key, capture=False)
    cacert = X509.X509()
    cacert.set_pubkey(pub)
    cacert.set_subject_name(crt_subject(CN, Email, OU, O, L, ST, C))

    now = int(time.time())
    notbefore = ASN1.ASN1_UTCTIME()
    notbefore.set_time(now)

    notafter = ASN1.ASN1_UTCTIME()
    notafter.set_time(now + lifetime)

    cacert.set_not_before(notbefore)
    cacert.set_not_after(notafter)

    #Make sure that this differs from certs it goes on to sign!
    cacert.set_serial_number(1)

    #Self-signed, so issuer derived from the cert itself
    cacert.set_issuer_name(cacert.get_subject())

    #Set CA:TRUE extension on cert
    ext = X509.new_extension("basicConstraints", "CA:TRUE")
    ext.set_critical()
    cacert.add_ext(ext)

    #Sign the cacert
    cacert.sign(pub, md=alg)

    return (cacert, key)


def http_post(csr, url="http://keyserver/cgi-bin/sendcert/index.cgi"):

    args = {'file': csr.as_pem()}

    return urllib2.urlopen(url, urllib.urlencode(args)).read()


if __name__ == "__main__":

    print(http_post(make_csr()))
