#!/usr/bin/python
import argparse
import urllib.request
import http.cookiejar
from machination.cosign import CosignPasswordMgr, CosignHandler
from machination.webclient import WebClient

if __name__ == '__main__':

    cj = http.cookiejar.MozillaCookieJar('cookies.txt')
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        CosignHandler('https://www.ease.ed.ac.uk/',
                      cj,
                      CosignPasswordMgr()
                      )
        )
    req = urllib.request.Request(
        url='https://www.see.ed.ac.uk/~wwwuser2/bin/auth/licusers.cgi',
        )
    res = opener.open(req)
#    cj.extract_cookies(res,req)
#    cj.save(ignore_discard=True)
    print(res.read().decode('utf-8'))
    print('I got that from {} you know.'.format(res.geturl()))

