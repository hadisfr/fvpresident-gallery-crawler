#!/usr/bin/env python3

import json
import shutil
import re
import logging
from os import path
from pathlib import Path
from typing import Any, Dict, Iterable
from sys import argv, stderr
from pprint import pprint

import requests

logging.captureWarnings(True)

# details_patter = re.compile(r"(?s)<div class=\"ug-textpanel-description\".*?>(.*?)<span.*?>(.*?)</span><span class=\"wrapper\"></span></div>")
details_patter = re.compile(r"(?s)<img\s+alt=\"(.*?)\"\s+src=\"(.*?)\"\s+data-image=\"(.*?)\"\s+data-description='(.*?)'\s+/>")


def parse_page(page_id: int) -> Iterable[Dict[str, Any]]:
    def parse_description(image: Dict[str, Any]) -> Dict[str, Any]:
        description_regex = re.compile(r"(.*)<span class=\"date_author_news\">(.*)</span><span class=\"wrapper\"></span>")
        description = image["data-description"]
        parsed = description_regex.findall(description)
        if len(parsed) != 1 or len(parsed[0]) != 2:
            print("invalid data-description in page %s:\t%s" % (image["page_id"], image["data-description"]), file=stderr)
            image["date_author_news"] = ""
            return image
        description, date_author = parsed[0]
        image["data-description"] = description.strip()
        image["date_author_news"] = date_author.strip()
        return image

    def parse_image(image: Dict[str, Any]) -> Dict[str, Any]:
        if image["alt"] != "" or image["src"] != image["data-image"] or not image["date_author_news"].startswith("تاریخ انتشار: "):
            print("invalid fields:\n%s" % json.dumps(image), file=stderr)
            return image
        return {
            "Page ID": image["page_id"],
            "URL": image["src"],
            "Description": image["data-description"],
            "Publication Date": image["date_author_news"][len("تاریخ انتشار:")+1:].strip(),
        }

    def process_image(image: Dict[str, Any]) -> Dict[str, Any]:
        download_img(image["URL"], image["Page ID"])
        return image

    url = "https://fvpresident.ir/fa/gallery/%d" % page_id
    page = requests.get(url, verify=False)
    if page.status_code != 200:
        print("could not get %s: %s" % (page_id, page.status_code), file=stderr)
        return []
    images = details_patter.findall(page.text)
    if not len(images):
        print("no image found in %s" % page_id, file=stderr)
    images = map(lambda img: {
        "page_id": page_id,
        "alt": img[0].strip(),
        "src": img[1].strip(),
        "data-image": img[2].strip(),
        "data-description": img[3].strip().replace('\n', ' ').replace('\r', ''),
    }, images)
    images = map(parse_description, images)
    images = map(parse_image, images)
    images = map(process_image, images)
    return images


def download_img(img_url: str, page_id: str) -> None:
    response = requests.get(img_url, stream=True, verify=False)
    if response.status_code != 200:
        print("could not get image %s: %s" % (img_url, response.status_code), file=stderr)
        return
    dir_addr = path.join("pics", str(page_id))
    file_addr = path.join(dir_addr, img_url.split("/")[-1])
    Path(dir_addr).mkdir(parents=True, exist_ok=True)
    with open(file_addr, "wb") as f:
        response.raw.decode_content = True
        shutil.copyfileobj(response.raw, f)


def main():
    LAST_PAGE_ID = 8356
    with open("metadata.jsonl", "w") as f:
        for page_id in range(1, LAST_PAGE_ID + 1):
            for image in parse_page(page_id):
                print(json.dumps(image, ensure_ascii=False), file=f)


if __name__ == '__main__':
    main()
