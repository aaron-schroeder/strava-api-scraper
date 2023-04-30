"""
HTTP OAuth downloader middleware

See documentation in docs/topics/downloader-middleware.rst

"""
from oauthlib.oauth2 import InsecureTransportError
from oauthlib.oauth2 import WebApplicationClient as Oauth2Client
from scrapy import signals


class HttpOAuth2Middleware(object):
    """Oauth 2.0 RFC 6749

    Ref:
        * https://github.com/scrapy/scrapy/compare/master...juanriaza:oauth-draft
        * https://groups.google.com/g/scrapy-users/c/EUzuuy6oaeE/m/7tmZBsJLDAAJ
        * https://github.com/joshlk/scrapy/blob/a534521d40aebf81a55dd69477dabc0b221e3e96/scrapy/contrib/downloadermiddleware/httpoauth.py
        * look into these:
        * https://github.com/DakotaNelson/strava-scraper/blob/master/strava/strava/middlewares.py
        * https://github.com/Cimera42/osmtiles/blob/86bd2bfd23d384a0e2dbd44a1396f8bf9af06cff/provider/sources/strava/strava.py
    """

    @classmethod
    def from_crawler(cls, crawler):
        o = cls()
        crawler.signals.connect(o.spider_opened, signal=signals.spider_opened)
        return o

    def spider_opened(self, spider):
        client = getattr(spider, 'oauth_client', None)
        if client:
            self.auth = client
        else:
            # These values should not be stored in version control.
            # The recommended approach is to set them at spider runtime:
            # `-a oauth_client_id=...`, `-a oauth_token=...`
            client_id = getattr(spider, 'oauth_client_id', None)
            token = getattr(spider, 'oauth_access_token', None)
            if all((client_id, token)):
                self.auth = Oauth2Client(client_id, access_token=token)

    def _is_secure_transport(self, uri):
        return uri.lower().startswith('https://')

    def process_request(self, request, spider):
        auth = getattr(self, 'auth', None)
        oauth_used = request.meta.get('oauth', False)
        if auth and not oauth_used:
            if not self._is_secure_transport(request.url):
                raise InsecureTransportError()

            # Generate HTTP header
            url, headers, body = self.auth.add_token(
                request.url,
                http_method=request.method,
                body=request.body,
                headers=request.headers)

            # Add token header to request.
            # NOTE: it is necessary to return the 
            # newly-instantiated request or scrapy will use the original
            # one passed to the method.
            request = request.replace(
                url=url,
                headers=headers,
                body=body)

            request.meta['oauth'] = True
            return request
