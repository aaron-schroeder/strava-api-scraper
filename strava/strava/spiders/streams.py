import json
from json.decoder import JSONDecodeError
import os
from urllib.parse import parse_qs, urlparse

from scrapy import Spider
from scrapy.http import Request


class StravaApiStreamSpider(Spider):
  name = 'streams'
  allowed_domains = ['strava.com']
  url_base = 'https://www.strava.com/api/v3'

  @classmethod
  def from_crawler(cls, crawler, *args, **kwargs):
    spider = super().from_crawler(crawler, *args, **kwargs)
    # Most straightforward/naive approach is to look at the 
    # output file(s) and see which activities have already been scraped.
    spider.saved_activity_ids = []
    for feed_uri, options in spider.settings.getdict('FEEDS').items():
      if not options.get('overwrite') and os.path.exists(feed_uri):
        fmt = options.get('format')
        if fmt == 'json':
          with open(feed_uri, 'r') as f:
            try:
              stream_list = json.load(f)
            except JSONDecodeError:
              continue
            spider.saved_activity_ids = [stream_data['activity_id'] 
                                         for stream_data in stream_list]
        elif fmt == 'jl':
          with open(feed_uri, 'r') as f:
            spider.saved_activity_ids = [json.loads(line)['activity_id'] 
                                         for line in f]
    return spider
 
  # Start on the first activity list page
  def start_requests(self):
    yield Request(self._get_activities_endpoint_url(page=1),
                  dont_filter=True)
  
  def _get_activities_endpoint_url(self, page=1):
    return f'{self.url_base}/athlete/activities?per_page=200&page={page}'

  def parse(self, response):
    data = response.json()
    # crude format validation
    if not isinstance(data, list):
      return
    for item in data:
      # At this point, check whether item['id'] corresponds to an
      # already-saved set of streams. 
      # Implementation specifics do not really matter.
      if item['id'] not in self.saved_activity_ids: 
        # NOTE: Strava API docs say that `key_by_type` empty/true param
        #       is required, but I did not need to.
        yield Request(f'{self.url_base}/activities/{item["id"]}/streams'
                      '?keys=time,latlng,distance,altitude,velocity_smooth,'
                      'heartrate,cadence,watts,temp,moving,grade_smooth',
                      meta={'activity_id': item['id']},
                      dont_filter=True,
                    callback=self.parse_item)

    # If the requested number of activities is returned, there *might* be
    # more activities on the next page.
    if len(data) == 200:
      url_params = parse_qs(urlparse(response.request.url).query)
      next_pg = int(url_params.get('page', [1])[0]) + 1
      yield Request(self._get_activities_endpoint_url(page=next_pg),
                    dont_filter=True)
  
  def parse_item(self, response):
    js = response.json()
    return dict(activity_id=response.meta['activity_id'],
                data=js if isinstance(js, list) else [])
