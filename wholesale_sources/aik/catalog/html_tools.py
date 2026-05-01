import html
import re
from urllib.parse import urljoin


def compact_spaces(text):
    return " ".join(text.split())


def strip_tags(value):
    plain = re.sub(r"<[^>]+>", " ", value or "")
    return compact_spaces(html.unescape(plain))


def match_one(pattern, text, flags=0):
    match = re.search(pattern, text, flags)
    return match.group(1).strip() if match else ""


def unique_urls(base_url, urls):
    seen = set()
    result = []
    for item in urls:
        absolute = urljoin(base_url, item)
        if not absolute or absolute in seen:
            continue
        seen.add(absolute)
        result.append(absolute)
    return result
