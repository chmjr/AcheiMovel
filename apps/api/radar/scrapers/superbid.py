from collections.abc import AsyncIterator
from datetime import datetime
from decimal import Decimal
import re
from unicodedata import normalize
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from radar.scrapers.base import BaseScraper, RawListing
from radar.scrapers.json_public import extract_next_data

SUPERBID_BASE = "https://www.superbid.net"
SUPERBID_START_URLS = (
    "https://www.superbid.net/categorias/imoveis/imoveis-residenciais/casas/santa-catarina/florianopolis-sc",
    "https://www.superbid.net/categorias/imoveis/imoveis-residenciais/casas/santa-catarina/sao-jose-sc",
    "https://www.superbid.net/categorias/imoveis/imoveis-residenciais/casas/santa-catarina/palhoca-sc",
    "https://www.superbid.net/categorias/imoveis/imoveis-residenciais/apartamentos/santa-catarina/florianopolis-sc",
    "https://www.superbid.net/categorias/imoveis/terrenos/santa-catarina/florianopolis-sc",
)
TARGET_CITY_NAMES = ("florianopolis", "sao jose", "palhoca", "biguacu")


class SuperbidScraper(BaseScraper):
    source = "superbid"
    category = "auction"

    async def discover(self) -> AsyncIterator[str]:
        seen: set[str] = set()
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            for start_url in SUPERBID_START_URLS:
                response = await client.get(start_url)
                for href in _extract_offer_urls(response.text):
                    if href not in seen:
                        seen.add(href)
                        yield href

    async def parse(self, url: str) -> RawListing | None:
        async with httpx.AsyncClient(timeout=30, follow_redirects=True, trust_env=False) as client:
            response = await client.get(url)
        data = _extract_next_data(response.text)
        offer = _first_offer(data)
        if not offer:
            return None

        product = offer.get("product") or {}
        location = product.get("location") or {}
        city = _city_from_location(location.get("city"))
        if not city or _normalize(city) not in TARGET_CITY_NAMES:
            return None

        detail = offer.get("offerDetail") or {}
        auction = offer.get("auction") or {}
        description = _strip_html(product.get("detailedDescription") or "")
        price = _decimal(detail.get("currentMinBid") or detail.get("initialBidValue") or offer.get("price"))
        photos = [item.get("link") for item in product.get("galleryJson") or [] if item.get("link")]
        attachments = product.get("attachments") or []

        return RawListing(
            source=self.source,
            source_id=str(offer["id"]),
            source_url=url,
            title=product.get("shortDesc") or offer.get("seoTitle") or "Oferta Superbid",
            description=description,
            price=price,
            condo_fee=None,
            iptu_yearly=None,
            city=city,
            neighborhood=_extract_neighborhood(product.get("shortDesc") or description),
            address=_extract_address(description),
            property_type=_property_type(product.get("shortDesc") or ""),
            area_privative=_extract_area(product.get("shortDesc") or description),
            bedrooms=None,
            bathrooms=None,
            parking_spots=None,
            photos=photos,
            raw_payload={"url": url, "offer": offer},
            auction_data={
                "auction_type": "judicial" if product.get("judicial") else "extrajudicial",
                "auctioneer": auction.get("auctioneer"),
                "appraisal_value": None,
                "minimum_bid": price,
                "discount_pct": None,
                "is_occupied": "ocupado" in description.lower(),
                "auction_date": _parse_superbid_datetime(offer.get("endDate")),
                "edital_url": _first_pdf(attachments),
                "financeable": "financiado" in description.lower(),
            },
        )


def _extract_offer_urls(html: str) -> list[str]:
    urls = set()
    for href in re.findall(r'href=["\']([^"\']*/oferta/[^"\']+)["\']', html, re.IGNORECASE):
        urls.add(urljoin(SUPERBID_BASE, href))
    return sorted(urls)


def _extract_next_data(html: str) -> dict:
    return extract_next_data(html)


def _first_offer(data: dict) -> dict | None:
    offers = (((data.get("props") or {}).get("pageProps") or {}).get("offerDetails") or {}).get("offers")
    return offers[0] if offers else None


def _city_from_location(value: str | None) -> str | None:
    if not value:
        return None
    return value.split("-")[0].strip()


def _strip_html(value: str) -> str:
    return HTMLParser(value).text(separator=" ", strip=True)


def _extract_neighborhood(value: str) -> str | None:
    match = re.search(r"bairro\s+([^,]+?)\s+em\s+", value, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_address(value: str) -> str | None:
    match = re.search(r"Endere[cç]o\s*-\s*([^,]+(?:,[^,]+){0,2})", value, re.IGNORECASE)
    return match.group(1).strip() if match else None


def _extract_area(value: str) -> Decimal | None:
    match = re.search(r"([\d\.,]+)\s*m[²2]", value, re.IGNORECASE)
    return _parse_brl(match.group(1)) if match else None


def _property_type(value: str) -> str:
    lowered = value.lower()
    if "casa" in lowered:
        return "casa"
    if "apart" in lowered:
        return "apartamento"
    if "terreno" in lowered:
        return "terreno"
    return "imovel"


def _first_pdf(attachments: list[dict]) -> str | None:
    for attachment in attachments:
        link = attachment.get("link")
        if link and link.lower().endswith(".pdf"):
            return link
    return None


def _parse_superbid_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def _decimal(value) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None


def _parse_brl(value: str) -> Decimal | None:
    clean = re.sub(r"[^\d,.-]", "", value).replace(".", "").replace(",", ".")
    return Decimal(clean) if clean else None


def _normalize(value: str) -> str:
    return normalize("NFKD", value.lower()).encode("ascii", "ignore").decode("ascii")
