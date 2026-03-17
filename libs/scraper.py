import re
from datetime import timedelta

import requests
from bs4 import BeautifulSoup as bs
from cachier import cachier
from loguru import logger


def find_bandcamp_artists(query: str) -> str:
    # <meta property="og:image" content="https://f4.bcbits.com/img/a3577478510_5.jpg">
    soup = bs(query, "html.parser")
    meta = soup.find("meta", property="og:image")
    if meta:
        return meta["content"]
    return ""


def find_bandcamp_name(query: str) -> list:
    match = re.match("https://(.+\\.|)bandcamp.com/(album|track)/(.+)", query)
    if match:
        artist = match.group(1).strip(".")
        name = match.group(3)
        type = match.group(2)
        return [f"{artist}", f"{name}", f"{type}"]
    return []


@cachier(stale_after=timedelta(days=1))
def request_site(url: str) -> requests.Response:
    response = requests.get(url)
    if response.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"HTTP error {response.status_code}", response=response
        )
    return response


def scrape_bandcamp_url(query: str) -> dict:
    url = query
    response = request_site(url)
    if response.status_code == 200:
        image_url = find_bandcamp_artists(response.text)
        artist, name, type = find_bandcamp_name(url)
        logger.info(f"Found: {artist} - {name} ({type}), image_url: {image_url}")
        return {"image_url": image_url, "name": name, "type": type, "artist": artist}
    elif response.status_code != 200:
        raise requests.exceptions.HTTPError(
            f"HTTP error {response.status_code}", response=response
        )
    return {}


def fetch_bandcamp_url(query: str) -> dict:
    results = scrape_bandcamp_url(query)
    return results
