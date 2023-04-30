import dj_redis_url
from scrapy.exceptions import CloseSpider, IgnoreRequest, NotConfigured
from twisted.internet import defer
import txredisapi


class StravaRateLimitMiddleware:
    ACTIVE = 'active'

    @classmethod
    def from_crawler(cls, crawler):
        """Create a new instance and pass it Redis' url and namespace"""
        # Get redis URL
        redis_url = crawler.settings.get('STRAVA_REDIS_URL', None)
        # If doesn't exist, disable
        if not redis_url:
            raise NotConfigured
        redis_nm = crawler.settings.get('STRAVA_REDIS_NS', 'RATE_LIMIT')
        o = cls(redis_url, redis_nm)
        return o

    def __init__(self, redis_url, redis_nm):
        # Store the url and the namespace for future reference
        self.redis_url = redis_url
        self.redis_nm = redis_nm
        self.key = f'{self.redis_nm}:status'

        # Report connection error only once
        self.report_connection_error = True

        # Parse redis URL and try to initialize a connection
        args = self.parse_redis_url(self.redis_url)
        self.connection = txredisapi.lazyConnectionPool(connectTimeout=5,
                                                        replyTimeout=5,
                                                        **args)

    @defer.inlineCallbacks
    def process_request(self, request, spider):
        try:
            # If the rate limit status is unknown, assume it is ok.
            rate_limit_status = yield self.connection.get(self.key)
            if (
                rate_limit_status is not None 
                and rate_limit_status == self.ACTIVE
            ):
                # no point firing the request as it won't return 
                # valid data and would still count towards our rate limit
                # TODO: Consider logging how long until it'll be ready
                # to go.
                spider.logger.debug('Rate limit in effect. '
                                    'Request not sent to downloader.')
                raise IgnoreRequest
        except txredisapi.ConnectionError:
            if self.report_connection_error:
                spider.logger.error('Cannot connect to Redis: '
                                    + self.redis_url)
                self.report_connection_error = False

    @defer.inlineCallbacks
    def process_response(self, request, response, spider):
        if response.status == 429:
            # Use header info to determine how long the rate limit will
            # be in effect, then set a value in redis that expires at
            # that time.
            
            usages = response.headers['X-Ratelimit-Usage'].decode('utf-8')
            limits = response.headers['X-Ratelimit-Limit'].decode('utf-8')

            spider.logger.info(f'Strava rate limit reached. '
                               f'Usage: {usages}; Limit: {limits}')

            import calendar, datetime, math
            response_date = response.headers['Date'].decode('utf-8')
            dt = datetime.datetime.strptime(response_date,
                                            '%a, %d %b %Y %H:%M:%S %Z')
            
            timestamp = int(calendar.timegm(dt.timetuple()))
            next_15 = 15 * math.ceil(dt.minute / 15)  # 15, 30, 45, 60
            timestamp_exp = timestamp + 60 * (next_15 - dt.minute) - dt.second
            
            try:
                yield self.connection.execute_command(
                    'SET', self.key, self.ACTIVE, 'EXAT', timestamp_exp)
                    # 'SET', self.key, self.ACTIVE, ('EXAT', timestamp_exp))
            except txredisapi.ConnectionError:
                if self.report_connection_error:
                    spider.logger.error('Cannot connect to Redis: '
                                        + self.redis_url)
                    self.report_connection_error = False

            CloseSpider('rate_limit')
        
        elif response.status == 404:
            # The activity does not have streams to return.
            # But the response is still json, so the response is fine to
            # send through.
            # I guess it depends on what I wanna end up doing with it.
            request.meta['dont_retry'] = True

        defer.returnValue(response)

    @staticmethod
    def parse_redis_url(redis_url):
        """
        Parses redis url and prepares arguments for
        txredisapi.lazyConnection()
        """

        params = dj_redis_url.parse(redis_url)

        conn_kwargs = {}
        conn_kwargs['host'] = params['HOST']
        conn_kwargs['password'] = params['PASSWORD']
        conn_kwargs['dbid'] = params['DB']
        conn_kwargs['port'] = params['PORT']

        # Remove items with empty values
        conn_kwargs = dict((k, v) for k, v in conn_kwargs.items() if v)

        return conn_kwargs