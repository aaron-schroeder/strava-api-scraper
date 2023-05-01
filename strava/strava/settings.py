# Scrapy settings for strava_api project
#
# For simplicity, this file contains only settings considered important or
# commonly used. You can find more settings consulting the documentation:
#
#     https://docs.scrapy.org/en/latest/topics/settings.html
#     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
#     https://docs.scrapy.org/en/latest/topics/spider-middleware.html

BOT_NAME = "strava"

SPIDER_MODULES = ["strava.spiders"]
NEWSPIDER_MODULE = "strava.spiders"

ROBOTSTXT_OBEY = False

DOWNLOADER_MIDDLEWARES = {
   "strava.middlewares.oauth.HttpOAuth2Middleware": 543,
   "strava.middlewares.ratelimit.StravaRateLimitMiddleware": 544,
}

RETRY_ENABLED = False

# STRAVA_REDIS_URL = "redis://127.0.0.1:6379"

# Set settings whose default value is deprecated to a future-proof value
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
FEED_EXPORT_ENCODING = "utf-8"

