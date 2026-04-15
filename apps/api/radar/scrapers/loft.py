from decimal import Decimal
import os
import re
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

from radar.scrapers.base import BaseScraper, RawListing
from radar.services.ingestion import persist_raw_listing

LOFT_BASE = "https://loft.com.br"
CITY_SLUGS = {
    "florianopolis": "Florianópolis",
    "sao-jose": "São José",
    "palhoca": "Palhoça",
    "biguacu": "Biguaçu",
}
LISTING_KINDS = ("imoveis", "apartamentos", "casas")
MAX_PAGES_PER_CATEGORY = max(1, int(os.getenv("LOFT_PAGES_PER_CATEGORY", "1")))


class LoftScraper(BaseScraper):
    source = "loft"
    category = "common"

    async def discover(self):
        for city_slug in CITY_SLUGS:
            for kind in LISTING_KINDS:
                for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
                    suffix = "" if page == 1 else f"?pagina={page}"
                    yield f"{LOFT_BASE}/venda/{kind}/sc/{city_slug}{suffix}"

    async def parse(self, url: str) -> RawListing | None:
        return None

    async def run(self, db) -> dict[str, Any]:
        stats: dict[str, Any] = {
            "collected": 0,
            "parsed": 0,
            "new": 0,
            "updated": 0,
            "errors": 0,
            "error_messages": [],
        }
        seen_urls: set[str] = set()

        async with httpx.AsyncClient(
            timeout=45,
            follow_redirects=True,
            trust_env=False,
            headers={"user-agent": "Mozilla/5.0"},
        ) as client:
            async for page_url in self.discover():
                try:
                    response = await client.get(page_url)
                    response.raise_for_status()
                    listings = _extract_listings(response.text, str(response.url), seen_urls)
                    stats["collected"] += len(listings)
                    for listing in listings:
                        status = persist_raw_listing(db, listing)
                        stats["parsed"] += 1
                        if status in {"new", "updated"}:
                            stats[status] += 1
                except Exception as exc:
                    db.rollback()
                    stats["errors"] += 1
                    stats["error_messages"].append(f"{page_url}: {exc}")
        return stats


def _extract_listings(html: str, page_url: str, seen_urls: set[str]) -> list[RawListing]:
    tree = HTMLParser(html)
    listings = []
    city = _city_from_url(page_url)

    for node in tree.css("a[href*='/imovel/']"):
        text = _clean_text(node.text(separator=" "))
        if "R$" not in text or "Ver contato" not in text:
            continue

        href = node.attributes.get("href") or ""
        source_url = urljoin(LOFT_BASE, href)
        if source_url in seen_urls:
            continue
        seen_urls.add(source_url)

        price = _first_money(text)
        if not price:
            continue

        address, neighborhood = _address_neighborhood(text)
        listings.append(
            RawListing(
                source="loft",
                source_id=_source_id(source_url),
                source_url=source_url,
                title=_title(text),
                description=text,
                price=price,
                condo_fee=None,
                iptu_yearly=None,
                city=city,
                neighborhood=neighborhood,
                address=address,
                property_type=_property_type(text),
                area_privative=_area(text),
                bedrooms=_number_after_area(text, 1),
                bathrooms=_number_after_area(text, 2),
                parking_spots=None,
                photos=[],
                raw_payload={"page_url": page_url, "card_text": text},
            )
        )

    return listings


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _source_id(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.split("/")[-1]


def _first_money(text: str) -> Decimal | None:
    match = re.search(r"R\$\s*([\d.]+(?:,\d{2})?)", text)
    if not match:
        return None
    return Decimal(match.group(1).replace(".", "").replace(",", "."))


def _area(text: str) -> Decimal | None:
    match = re.search(r"m²\s*(\d+(?:[,.]\d+)?)\s*m²", text)
    return Decimal(match.group(1).replace(",", ".")) if match else None


def _number_after_area(text: str, position: int) -> int | None:
    match = re.search(r"m²\s*\d+(?:[,.]\d+)?\s*m²(?:\s+(\d+))?(?:\s+(\d+))?", text)
    if not match:
        return None
    value = match.group(position)
    return int(value) if value else None


def _property_type(text: str) -> str:
    lowered = text.lower()
    if "terreno" in lowered:
        return "terreno"
    if "casa" in lowered:
        return "casa"
    if "apartamento" in lowered or "cobertura" in lowered or "studio" in lowered:
        return "apartamento"
    return "imovel"


def _address_neighborhood(text: str) -> tuple[str | None, str | None]:
    match = re.search(r"R\$\s*[\d.]+(?:,\d{2})?\s+(.+?)\s+m²\s+\d", text)
    if not match:
        return None, None
    location = _clean_text(match.group(1))
    if "," not in location:
        return location, None
    address, neighborhood = location.rsplit(",", 1)
    return _clean_text(address), _clean_text(neighborhood)


def _title(text: str) -> str:
    cleaned = text.replace("Chegou este mês ", "").replace("Redecorar ", "")
    match = re.search(r"Ver mais sobre o imóvel\s+(.+?)\s+Ver contato", cleaned)
    return _clean_text(match.group(1))[:180] if match else cleaned[:180]


def _city_from_url(url: str) -> str:
    for slug, city in CITY_SLUGS.items():
        if f"/{slug}" in url:
            return city
    return "Florianópolis"
