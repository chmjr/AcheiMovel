from collections.abc import AsyncIterator
from decimal import Decimal
import re
from unicodedata import normalize
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from radar.scrapers.base import BaseScraper, RawListing

LEILOEIRO_PUBLICO_BASE = "https://www.leiloeiropublico.com.br"
LEILOEIRO_PUBLICO_HOME = f"{LEILOEIRO_PUBLICO_BASE}/"
SEED_DETAIL_URLS = (
    "https://www.leiloeiropublico.com.br/DetalheLote.aspx?Leilao=19.048&Lote=001&Sublote=1",
)
TARGET_CITY_NAMES = ("florianopolis", "sao jose", "palhoca", "biguacu")


class LeiloeiroPublicoScraper(BaseScraper):
    source = "leiloeiro_publico"
    category = "auction"

    async def discover(self) -> AsyncIterator[str]:
        seen = set(SEED_DETAIL_URLS)
        for url in SEED_DETAIL_URLS:
            yield url

        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            response = await client.get(LEILOEIRO_PUBLICO_HOME)
        for url in _extract_detail_urls(response.text):
            if url not in seen:
                seen.add(url)
                yield url

    async def parse(self, url: str) -> RawListing | None:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            response = await client.get(url)
        html = response.text
        text = _page_text(html)
        title = _extract_title(html, text)
        city = _extract_city(title)
        if not city or _normalize(city) not in TARGET_CITY_NAMES:
            return None

        minimum_bid = _value_after(text, "Oferta Minima") or _value_after(text, "Oferta Mínima")
        appraisal = _value_after(text, "Valor de Avaliacao") or _value_after(text, "Valor de Avaliação")

        return RawListing(
            source=self.source,
            source_id=_extract_source_id(url),
            source_url=url,
            title=title,
            description=_extract_description(text),
            price=minimum_bid,
            condo_fee=None,
            iptu_yearly=None,
            city=city,
            neighborhood=_extract_neighborhood(text),
            address=_extract_address(text),
            property_type=_property_type(title),
            area_privative=_extract_area(text),
            bedrooms=None,
            bathrooms=None,
            parking_spots=None,
            photos=_extract_photos(html),
            raw_payload={"url": url, "html": html},
            auction_data={
                "auction_type": "judicial" if "Judicial" in text else None,
                "auctioneer": "Leiloeiro Público",
                "appraisal_value": appraisal,
                "minimum_bid": minimum_bid,
                "discount_pct": _discount(appraisal, minimum_bid),
                "is_occupied": None,
                "auction_date": None,
                "edital_url": _extract_edital_url(html),
                "financeable": None,
            },
        )


def _extract_detail_urls(html: str) -> list[str]:
    urls = set()
    for href in re.findall(r'href=["\']([^"\']*DetalheLote\.aspx[^"\']+)["\']', html, re.IGNORECASE):
        urls.add(urljoin(LEILOEIRO_PUBLICO_BASE, href))
    return sorted(urls)


def _page_text(html: str) -> str:
    tree = HTMLParser(html)
    return tree.body.text(separator="\n", strip=True) if tree.body else tree.text(separator="\n", strip=True)


def _extract_title(html: str, text: str) -> str:
    match = re.search(r"Lote\s+\d+\s*-\s*([^\n]+)", text, re.IGNORECASE)
    if match:
        return match.group(0).strip()
    tree = HTMLParser(html)
    for selector in ("h2", "h1"):
        node = tree.css_first(selector)
        if not node:
            continue
        title = node.text(separator=" ", strip=True)
        if "google chrome" not in title.lower():
            return title
    return "Lote Leiloeiro Público"


def _extract_city(value: str) -> str | None:
    normalized = _normalize(value)
    for city in TARGET_CITY_NAMES:
        if city in normalized:
            return " ".join(part.capitalize() for part in city.split())
    return None


def _value_after(text: str, label: str) -> Decimal | None:
    normalized_text = _normalize(text)
    normalized_label = _normalize(label)
    idx = normalized_text.find(normalized_label.lower())
    if idx < 0:
        return None
    fragment = text[idx : idx + 300]
    match = re.search(r"R\$\s*([\d\.,]+)", fragment)
    return _parse_brl(match.group(1)) if match else None


def _extract_description(text: str) -> str | None:
    marker = "Descrição"
    if marker in text:
        return text.split(marker, 1)[1][:4000].strip()
    return text[:4000]


def _extract_neighborhood(text: str) -> str | None:
    match = re.search(r"Bairro\s+([^,\n.]+)", text, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_address(text: str) -> str | None:
    match = re.search(r"(Rua|Avenida|Av\.?)\s+([^,\n]+(?:,[^,\n]+){0,2})", text, re.IGNORECASE)
    return match.group(0).strip() if match else None


def _extract_area(text: str) -> Decimal | None:
    match = re.search(r"([\d\.,]+)\s*m[²2]", text, re.IGNORECASE)
    return _parse_brl(match.group(1)) if match else None


def _extract_photos(html: str) -> list[str]:
    tree = HTMLParser(html)
    photos = []
    for img in tree.css("img"):
        src = img.attributes.get("src")
        if src and "logo" not in src.lower():
            photos.append(urljoin(LEILOEIRO_PUBLICO_BASE, src))
    return photos[:10]


def _extract_edital_url(html: str) -> str | None:
    match = re.search(r'href=["\']([^"\']*(?:Edital|edital)[^"\']*\.pdf)["\']', html)
    return urljoin(LEILOEIRO_PUBLICO_BASE, match.group(1)) if match else None


def _property_type(title: str) -> str:
    lowered = title.lower()
    if "galp" in lowered or "comercial" in lowered:
        return "comercial"
    if "terreno" in lowered:
        return "terreno"
    if "casa" in lowered:
        return "casa"
    if "apart" in lowered:
        return "apartamento"
    return "imovel"


def _extract_source_id(url: str) -> str:
    query = url.split("?", 1)[-1]
    return re.sub(r"[^A-Za-z0-9_.=-]+", "-", query)[:120]


def _discount(appraisal: Decimal | None, bid: Decimal | None) -> Decimal | None:
    if not appraisal or not bid or appraisal <= 0:
        return None
    return ((appraisal - bid) / appraisal * Decimal("100")).quantize(Decimal("0.01"))


def _parse_brl(value: str) -> Decimal | None:
    clean = re.sub(r"[^\d,.-]", "", value).replace(".", "").replace(",", ".")
    return Decimal(clean) if clean else None


def _normalize(value: str) -> str:
    return normalize("NFKD", value.lower()).encode("ascii", "ignore").decode("ascii")
