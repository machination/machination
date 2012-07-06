#!/usr/bin/python
import argparse
import urllib.request
import urllib.parse
import http.client
import http.cookiejar
import getpass

def cosign_opener(login_url, cookie_file='cookies.txt'):
    """Generate an OpenerDirector instance which can fetch cosign protected urls"""
    cj = http.cookiejar.MozillaCookieJar(cookie_file)
    cj.load(ignore_discard=True)
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj)
        )

    def splat(txt):
        print(txt)

    opener.splat = splat

    return opener

class CosignHandler(urllib.request.BaseHandler):

    def __init__(self, login_url, cj):
        super().__init__()
        self.login_url = login_url
        self.cj = cj

    def https_response(self, req, res):
        if res.code == 200 and res.geturl().startswith(self.login_url + '?'):
            print('been redirected to login page')
            self.cj.extract_cookies(res, req)
#            user = input('username: ')
#            pwd = getpass.getpass()
            user = 'splat'
            pwd = 'frog'
            data = urllib.parse.urlencode({'login': user,
                                           'password': pwd})
            req2 = urllib.request.Request(
                res.geturl(),
                data.encode('iso-8859-1'),
                {'Content-Type':
                     'application/x-www-form-urlencoded;charset=%s' % 'iso-8859-1'}
                )
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(cj)
                )
            res2 = opener.open(req2)

            print(res2.code)
            print(res2.geturl())
            print(res2.read().decode('iso-8859-1'))
        return res


if __name__ == '__main__':

    cj = http.cookiejar.MozillaCookieJar('cookies.txt')
    cj.load(ignore_discard=True)
    cj.save('lastcookies.txt', ignore_discard=True)
    data = urllib.parse.urlencode({'login':'splat',
                                   'password': 'frog'}).encode('utf-8')
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        CosignHandler('https://www.ease.ed.ac.uk/', cj)
        )
    req = urllib.request.Request(
        url='https://www.see.ed.ac.uk/~wwwuser2/bin/auth/licusers.cgi',
        )
    res = opener.open(req)
    cj.extract_cookies(res,req)
    cj.save(ignore_discard=True)
#    print(res.geturl())
#    print(res.read().decode('utf-8'))
    exit()


    data = urllib.parse.urlencode({'login':'splat',
                                   'password': 'frog'}).encode('utf-8')
    r = urllib.request.Request(
        'https://www.ease.ed.ac.uk/',
        data,
        {'Content-Type':
             'application/x-www-form-urlencoded;charset=%s' % 'utf-8'}
        )
    f = urllib.request.urlopen(r)
    s = f.read().decode('utf-8')
    print(s)
