import json
from datetime import timedelta

import bandcamp_dl
from cachier import cachier
from loguru import logger
from nicegui import ui

"""
import requests

url = "https://bandcamp.com/api/bcsearch_public_api/1/autocomplete_elastic"

payload = {
    "search_text": "Princewhateverer",
    "search_filter": "",
    "full_page": False
}
response = requests.request("POST", url, json=payload)

print(response.text)
"""
# @cachier(cleanup_interval=timedelta(days=1))
# def bandcamp_autocomplete(query: str) -> str:
#     base_url = "https://bandcamp.com/api/bcsearch_public_api/1/autocomplete_elastic"
#     payload = {"search_text": query, "search_filter": "", "full_page": False}
#     response = requests.request("POST", base_url, json=payload)
#     return response.json()
import re

import requests
from bs4 import BeautifulSoup as bs


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


class DataCard(ui.card):
    def __init__(self, image_url: str, name: str, type: str, artist: str, url: str):
        super().__init__()
        self.name = name
        self.url = url
        self.tmp_dir = f"/tmp/bandcamp_dl/{self.name}"
        with self:
            ui.image(image_url).style("width: 100%")
            ui.label(f"{artist} - {name} ({type})")
            ui.separator()
            with ui.row():
                ui.button(text="Close", on_click=self.delete)
                self.fetch_button = ui.button(text="Fetch", on_click=self.fetch)
                self.download_button = ui.button(
                    text="Download", on_click=self.download
                )
                self.download_button.disable()

    def delete(self):
        self.remove(self)

    # Downloads track/album to client
    def download(self):
        # first zip the folder
        import os
        import zipfile

        zip_path = f"{self.tmp_dir}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(self.tmp_dir):
                for file in files:
                    zipf.write(
                        os.path.join(root, file),
                        os.path.relpath(os.path.join(root, file), self.tmp_dir),
                    )
        ui.download(zip_path, filename=f"{self.name}.zip")
        # os.remove(zip_path)

    def execute(self, base):
        import subprocess as sp

        sp.call(["bandcamp-dl", "--base-dir", base, self.url])

    # Downloads track/album to folder
    def fetch(self):
        # Use bandcamp_dl to fetch the track/album
        # mktmp
        import os

        try:
            os.makedirs(self.tmp_dir)
            self.execute(self.tmp_dir)
        except FileExistsError:
            # If empty, remove the tmp_dir and fetch again
            if not os.listdir(self.tmp_dir):
                os.rmdir(self.tmp_dir)
                self.fetch()
            else:
                ui.notify("Folder not empty, cannot fetch")

        if os.path.exists(self.tmp_dir):
            self.download_button.enable()
            self.fetch_button.remove(self.fetch_button)


def sanitise_url(url: str) -> str:
    return re.match(
        r"^https?://[a-zA-Z0-9.-]+\.bandcamp\.com/(album|track)/[a-zA-Z0-9_-]+/?$",
        url,
    ).group(0)


class Main:
    def __init__(self):
        self.user_input = ui.input(label="Download bandcamp url")
        self.button = ui.button(text="Fetch", on_click=self.fetch)

    def fetch(self):
        url = self.user_input.value
        if not url:
            return
        elif not sanitise_url(url):
            return

        result = fetch_bandcamp_url(url)
        if result:
            # ui.context.client.elements is a dict {id: element_object}
            all_elements = ui.context.client.elements.values()

            # Check if the track is already present
            already_exists = any(
                isinstance(c, DataCard) and c.name == result["name"]
                for c in all_elements
            )

            if already_exists:
                ui.notify("This track is already present.", type="warning")
                return

            # Create the new card if it doesn't exist
            DataCard(
                result["image_url"],
                result["name"],
                result["type"],
                result["artist"],
                url=url,
            )


def root():
    main = Main()


ui.run(root)
