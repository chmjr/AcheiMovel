from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal
import re
from unicodedata import normalize
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from radar.scrapers.base import BaseScraper, RawListing

LANCEJA_BASE = "https://www.lanceja.com.br"
LANCEJA_HOME = f"{LANCEJA_BASE}/"
TARGET_CITY_SLUGS = ("florianopolis", "sao-jose", "palhoca", "biguacu")
TARGET_CITY_NAMES = ("florianópolis", "florianopolis", "são josé", "sao jose", "palhoça", "palhoca", "biguaçu", "biguacu")


class LanceJaScraper(BaseScraper):
    source = "lanceja"
    category = "auction"

    async def discover(self) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            response = await client.get(LANCEJA_HOME)
        for url in _extract_lot_urls(response.text):
            if any(city in _slugify(url) for city in TARGET_CITY_SLUGS) or "-sc" in _slugify(url):
                yield url

    async def parse(self, url: str) -> RawListing | None:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            response = await client.get(url)
        html = response.text
        text = _page_text(html)
        title = _extract_title(html)
        city = _extract_city(title, text)
        if not _is_target_city(city):
            return None

        minimum_bid = _value_after(text, "Lance Mínimo")
        appraisal = _value_after(text, "Avaliação")
        area = _extract_area(title + "\n" + text)
        auction_type = "judicial" if "Judicial" in text else "extrajudicial" if "Extrajudicial" in text else None
        auction_date = _extract_closing_date(text)

        return RawListing(
            source=self.source,
            source_id=_extract_source_id(url),
            source_url=url,
            title=title,
            description=_extract_description(text),
            price=minimum_bid,
            condo_fee=None,
            iptu_yearly=None,
            city=city or "Não informado",
            neighborhood=None,
            address=None,
            property_type=_property_type(title),
            area_privative=area,
            bedrooms=None,
            bathrooms=None,
            parking_spots=None,
            photos=_extract_photos(html),
            raw_payload={"url": url, "html": html},
            auction_data={
                "auction_type": auction_type,
                "auctioneer": "Lance Já",
                "appraisal_value": appraisal,
                "minimum_bid": minimum_bid,
                "discount_pct": _discount(appraisal, minimum_bid),
                "is_occupied": None,
                "auction_date": auction_date,
                "edital_url": _extract_edital_url(html),
                "financeable": None,
            },
        )


def _extract_lot_urls(html: str) -> list[str]:
    urls = set()
    for href in re.findall(r'href=["\']([^"\']*lotes/[^"\']+)["\']', html, re.IGNORECASE):
        urls.add(urljoin(LANCEJA_BASE, href))
    return sorted(urls)


def _page_text(html: str) -> str:
    tree = HTMLParser(html)
    return tree.body.text(separator="\n", strip=True) if tree.body else tree.text(separator="\n", strip=True)


def _extract_title(html: str) -> str:
    tree = HTMLParser(html)
    node = tree.css_first("h2") or tree.css_first("h1")
    return node.text(separator=" ", strip=True) if node else "Lote Lance Já"


def _extract_city(title: str, text: str) -> str | None:
    joined = f"{title}\n{text}"
    match = re.search(r"\bEM\s+([^/\n]+?)/SC\b", joined, re.IGNORECASE)
    if match:
        return _title_city(match.group(1))
    match = re.search(r"\b([A-ZÁÀÂÃÉÊÍÓÔÕÚÇ ]+),\s*SC\b", joined)
    if match:
        return _title_city(match.group(1))
    return None


def _is_target_city(city: str | None) -> bool:
    return bool(city and _normalize(city) in TARGET_CITY_NAMES)


def _value_after(text: str, label: str) -> Decimal | None:
    pattern = rf"{re.escape(label)}[^R$]*R\$\s*([\d\.,]+)"
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return _parse_brl(match.group(1))


def _extract_area(text: str) -> Decimal | None:
    match = re.search(r"([\d\.,]+)\s*m[²2]", text, re.IGNORECASE)
    if not match:
        return None
    return _parse_brl(match.group(1))


def _extract_description(text: str) -> str | None:
    marker = "Descrição do lote"
    if marker not in text:
        return None
    description = text.split(marker, 1)[1].strip()
    return description[:4000]


def _extract_closing_date(text: str) -> datetime | None:
    match = re.search(r"Encerramento:\s*(\d{2}/\d{2}/\d{2})\s*às\s*(\d{2}h\d{2})", text)
    if not match:
        return None
    try:
        return datetime.strptime(f"{match.group(1)} {match.group(2).replace('h', ':')}", "%d/%m/%y %H:%M")
    except ValueError:
        return None


def _extract_photos(html: str) -> list[str]:
    tree = HTMLParser(html)
    photos = []
    for img in tree.css("img"):
        src = img.attributes.get("src")
        if src and "logo" not in src.lower():
            photos.append(urljoin(LANCEJA_BASE, src))
    return photos[:10]


def _extract_edital_url(html: str) -> str | None:
    match = re.search(r'href=["\']([^"\']*editais/[^"\']+\.pdf)["\']', html, re.IGNORECASE)
    return urljoin(LANCEJA_BASE, match.group(1)) if match else None


def _property_type(title: str) -> str:
    lowered = title.lower()
    if "terreno" in lowered or "terra" in lowered:
        return "terreno"
    if "casa" in lowered:
        return "casa"
    if "apart" in lowered:
        return "apartamento"
    if "comercial" in lowered:
        return "comercial"
    return "imovel"


def _extract_source_id(url: str) -> str:
    match = re.search(r"/lotes/([^/?#]+)", url)
    return match.group(1)[:120] if match else url.rsplit("/", 1)[-1]


def _discount(appraisal: Decimal | None, bid: Decimal | None) -> Decimal | None:
    if not appraisal or not bid or appraisal <= 0:
        return None
    return ((appraisal - bid) / appraisal * Decimal("100")).quantize(Decimal("0.01"))


def _parse_brl(value: str) -> Decimal | None:
    clean = re.sub(r"[^\d,.-]", "", value).replace(".", "").replace(",", ".")
    if not clean:
        return None
    try:
        return Decimal(clean)
    except Exception:
        return None


def _title_city(value: str) -> str:
    return " ".join(part.capitalize() for part in value.strip().lower().split())


def _normalize(value: str) -> str:
    return normalize("NFKD", value.lower()).encode("ascii", "ignore").decode("ascii")


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _normalize(value)).strip("-")
