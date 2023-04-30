
# strava-api-scraper
> Get time series data for all your Strava activities at once

## Setup

### Step 0: install 
```sh
pip install -r requirements.txt

```

### Step 1: Set up OAuth client

#### Register your API application credentials

```sh
$ strava-oauth register -c {client_id} -s {client_secret}
Strava API app successfully registered:
  client_id: {client_id}
  client_secret: {client_secret}
```

#### Grant your API app access to your personal data

```sh
$ strava-oauth authorize -c {client_id}
Launching OAuth Flask app...
Launching web browser to complete authorization..
```

### Step 2: Scrape your stream data
```sh
scrapy crawl streams  \
    -a oauth_client_id={client_id}   \
    -a oauth_access_token={access_token}  \
    -o data/streams.jl
```

## Optional Features

### Redis-based rate limit monitor
