from collections.abc import AsyncIterator
from decimal import Decimal
import re
from unicodedata import normalize
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from radar.scrapers.base import BaseScraper, RawListing

MEGA_BASE = "https://www.megaleiloes.com.br"
MEGA_START_URLS = (
    "https://www.megaleiloes.com.br/sc/florianopolis",
    "https://www.megaleiloes.com.br/sc/sao-jose",
    "https://www.megaleiloes.com.br/sc/palhoca",
    "https://www.megaleiloes.com.br/sc/biguacu",
)
REAL_ESTATE_TERMS = ("imovel", "imóveis", "casa", "apartamento", "terreno", "galpao", "galpão", "comercial")
TARGET_CITY_NAMES = ("florianopolis", "sao jose", "palhoca", "biguacu")


class MegaLeiloesScraper(BaseScraper):
    source = "mega_leiloes"
    category = "auction"

    async def discover(self) -> AsyncIterator[str]:
        seen: set[str] = set()
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            for start_url in MEGA_START_URLS:
                response = await client.get(start_url)
                for href in _extract_lot_urls(response.text):
                    if href not in seen:
                        seen.add(href)
                        yield href

    async def parse(self, url: str) -> RawListing | None:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            response = await client.get(url)
        html = response.text
        title = _extract_title(html)
        text = _page_text(html)
        if not _looks_like_real_estate(title + "\n" + text):
            return None

        city = _extract_city(title + "\n" + text)
        if not city or _normalize(city) not in TARGET_CITY_NAMES:
            return None

        price = _first_money(text)
        appraisal = _value_after(text, "Avaliação")

        return RawListing(
            source=self.source,
            source_id=_extract_source_id(url),
            source_url=url,
            title=title,
            description=text[:4000],
            price=price,
            condo_fee=None,
            iptu_yearly=None,
            city=city,
            neighborhood=None,
            address=None,
            property_type=_property_type(title),
            area_privative=_extract_area(title + "\n" + text),
            bedrooms=None,
            bathrooms=None,
            parking_spots=None,
            photos=_extract_photos(html),
            raw_payload={"url": url, "html": html},
            auction_data={
                "auction_type": "judicial" if "Judicial" in text else "extrajudicial" if "Extrajudicial" in text else None,
                "auctioneer": "Mega Leilões",
                "appraisal_value": appraisal,
                "minimum_bid": price,
                "discount_pct": _discount(appraisal, price),
                "is_occupied": "ocupado" in text.lower(),
                "auction_date": None,
                "edital_url": _extract_edital_url(html),
                "financeable": "financiamento" in text.lower(),
            },
        )


def _extract_lot_urls(html: str) -> list[str]:
    urls = set()
    for href in re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        full = urljoin(MEGA_BASE, href.replace("&amp;", "&"))
        lowered = _normalize(full)
        if "/imoveis/" in lowered and any(city.replace(" ", "-") in lowered for city in TARGET_CITY_NAMES):
            urls.add(full)
    return sorted(urls)


def _extract_title(html: str) -> str:
    tree = HTMLParser(html)
    node = tree.css_first("h1") or tree.css_first("h2") or tree.css_first("title")
    return node.text(separator=" ", strip=True) if node else "Lote Mega Leilões"


def _page_text(html: str) -> str:
    tree = HTMLParser(html)
    return tree.body.text(separator="\n", strip=True) if tree.body else tree.text(separator="\n", strip=True)


def _looks_like_real_estate(value: str) -> bool:
    normalized = _normalize(value)
    return any(_normalize(term) in normalized for term in REAL_ESTATE_TERMS)


def _extract_city(value: str) -> str | None:
    normalized = _normalize(value)
    for city in TARGET_CITY_NAMES:
        if city in normalized:
            return " ".join(part.capitalize() for part in city.split())
    return None


def _first_money(text: str) -> Decimal | None:
    match = re.search(r"R\$\s*([\d\.,]+)", text)
    return _parse_brl(match.group(1)) if match else None


def _value_after(text: str, label: str) -> Decimal | None:
    normalized_text = _normalize(text)
    idx = normalized_text.find(_normalize(label))
    if idx < 0:
        return None
    fragment = text[idx : idx + 300]
    match = re.search(r"R\$\s*([\d\.,]+)", fragment)
    return _parse_brl(match.group(1)) if match else None


def _extract_area(text: str) -> Decimal | None:
    match = re.search(r"([\d\.,]+)\s*m[²2]", text, re.IGNORECASE)
    return _parse_brl(match.group(1)) if match else None


def _extract_photos(html: str) -> list[str]:
    tree = HTMLParser(html)
    photos = []
    for img in tree.css("img"):
        src = img.attributes.get("src")
        if src and "logo" not in src.lower():
            photos.append(urljoin(MEGA_BASE, src))
    return photos[:10]


def _extract_edital_url(html: str) -> str | None:
    match = re.search(r'href=["\']([^"\']*(?:edital|Edital)[^"\']*\.pdf)["\']', html)
    return urljoin(MEGA_BASE, match.group(1)) if match else None


def _property_type(title: str) -> str:
    lowered = title.lower()
    if "terreno" in lowered:
        return "terreno"
    if "casa" in lowered:
        return "casa"
    if "apart" in lowered:
        return "apartamento"
    if "galp" in lowered or "comercial" in lowered:
        return "comercial"
    return "imovel"


def _extract_source_id(url: str) -> str:
    clean = url.split("?", 1)[0].rstrip("/")
    return clean.rsplit("/", 1)[-1][:120]


def _discount(appraisal: Decimal | None, bid: Decimal | None) -> Decimal | None:
    if not appraisal or not bid or appraisal <= 0:
        return None
    return ((appraisal - bid) / appraisal * Decimal("100")).quantize(Decimal("0.01"))


def _parse_brl(value: str) -> Decimal | None:
    clean = re.sub(r"[^\d,.-]", "", value).replace(".", "").replace(",", ".")
    return Decimal(clean) if clean else None


def _normalize(value: str) -> str:
    return normalize("NFKD", value.lower()).encode("ascii", "ignore").decode("ascii")
