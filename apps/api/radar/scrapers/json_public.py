import json
import re
from typing import Any

from selectolax.parser import HTMLParser


def extract_next_data(html: str) -> dict[str, Any]:
    tree = HTMLParser(html)
    node = tree.css_first("#__NEXT_DATA__")
    if not node:
        return {}
    return json.loads(node.text())


def extract_json_ld(html: str) -> list[Any]:
    tree = HTMLParser(html)
    payloads = []
    for node in tree.css('script[type="application/ld+json"]'):
        raw = node.text().strip()
        if not raw:
            continue
        payloads.append(json.loads(raw))
    return payloads


def find_public_json_objects(html: str, variable_name: str) -> list[dict[str, Any]]:
    pattern = rf"{re.escape(variable_name)}\s*=\s*({{.*?}})\s*;"
    matches = re.findall(pattern, html, flags=re.DOTALL)
    objects = []
    for match in matches:
        try:
            objects.append(json.loads(match))
        except json.JSONDecodeError:
            continue
    return objects
