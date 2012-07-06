#!/usr/bin/python
import argparse
import urllib.request
import urllib.parse
import http.client
import http.cookiejar
import getpass

class CosignPasswordMgr(object):

    def newcred(self):
        return {'username': input('username: '),
                'password': getpass.getpass()}

    def __init__(self, cred=None, max_tries=5, callback=newcred):
        self.set_cred(cred)
        self.try_count = 1
        self.max_tries = max_tries
        self.callback = callback

    def set_cred(self, cred):
        self.cred = cred
        self.dirty = False

    def get_cred(self):
        if not self.dirty and self.cred is not None:
            self.try_count = self.try_count + 1
            self.dirty = True
            return self.cred

        if self.try_count > self.max_tries:
            raise IndexError("Exceeded max_tries ({})".format(self.max_tries))

        self.cred = self.newcred()
        self.try_count = self.try_count + 1

        self.dirty = True
        return self.cred

class CosignHandler(urllib.request.BaseHandler):
    """urllib.request style handler for Cosign protected URLs.

    See http://weblogin.org

    SYNOPSIS:

    # Cosign relies on cookies.
    cj = http.cookiejar.MozillaCookieJar('cookies.txt')

    # If you've got one big program you'll probably want to keep the
    # cookies in memory, but for lots of little programs we get single
    # sign on behaviour by saving and loading to/from a file.
    try:
        # If this is the first script invocation there might not be a cookie
        # file yet.
        cj.load(ignore_discard=True)
    except IOError:
        pass

    # We need an opener that handles cookies and any cosign redirects and
    # logins.
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cj),
        # Here's the CosignHandler. Note that the login page for our
        # cosign server is https://www.ease.ed.ac.uk/
        CosignHandler('https://www.ease.ed.ac.uk/', cj)
        )

    # Construct a request for the page we actually want
    req = urllib.request.Request(
        url='https://www.see.ed.ac.uk/~wwwuser2/bin/auth/licusers.cgi',
        )

    # If all went well, res encapsulates the desired result, use res.read()
    # to get at the data and so on.
    res = opener.open(req)

    # Save the cookies for future programs (single sign on until they
    # expire)
    cj.extract_cookies(res,req)
    cj.save(ignore_discard=True)
    """

    def __init__(self, login_url, cj):
        """Construct new CosignHandler.

        Args:
          login_url: URL of cosign login page. Used to figure out if we
            have been redirected to the login page after a failed
            authentication, and as the URL to POST to to log in.

          cj: An http.cookiejar.CookieJar or equivalent. You'll need
            something that implements the FileCookieJar interface if
            you want to load/save cookies.
        """
        super().__init__()
        self.login_url = login_url
        self.cj = cj

    def https_response(self, req, res):
        """Handle https_response.

        If the response is from the cosign login page (starts with
        self.login_url) then log in to cosign and retry. Otherwise
        continue as normal.
        """
        if res.code == 200 and res.geturl().startswith(self.login_url + '?'):
            # Been redirected to login page.

            # We'll need the cosign cookies later
            self.cj.extract_cookies(res, req)

            # Grab a username and password.
            user = input('username: ')
            pwd = getpass.getpass()
            data = urllib.parse.urlencode({'login': user,
                                           'password': pwd})

            # Construct a login POST request to the login page.
            req2 = urllib.request.Request(
                self.login_url,
                data.encode('iso-8859-1'),
                )
            # We need a different opener that doesn't have a CosignHandler.
            opener = urllib.request.build_opener(
                urllib.request.HTTPCookieProcessor(self.cj)
                )
            # Try the login
            res2 = opener.open(req2)
            # Cookies, cookies, cookies
            self.cj.extract_cookies(res2, req2)

            # We should be logged in, go back and get what was asked for
            res = opener.open(req)

        return res


if __name__ == '__main__':

    pwm = CosignPasswordMgr(max_tries=2)
    for i in range(3):
        print(pwm.get_cred())

    exit()

    cj = http.cookiejar.MozillaCookieJar('cookies.txt')
    try:
        cj.load(ignore_discard=True)
    except IOError:
        pass
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
    print(res.read().decode('utf-8'))
    print('I got that from {} you know.'.format(res.geturl()))

