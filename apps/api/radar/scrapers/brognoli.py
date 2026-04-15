from decimal import Decimal
import re
from typing import Any
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from radar.scrapers.base import BaseScraper, RawListing
from radar.services.ingestion import persist_raw_listing

BROGNOLI_BASE = "https://www.brognoli.com.br"
CITY_SLUGS = {
    "florianopolis": "Florianópolis",
    "sao-jose": "São José",
    "palhoca": "Palhoça",
    "biguacu": "Biguaçu",
}


class BrognoliScraper(BaseScraper):
    source = "brognoli"
    category = "common"

    async def discover(self):
        for city_slug in CITY_SLUGS:
            yield f"{BROGNOLI_BASE}/comprar/cidade/{city_slug}/1/"

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
    city_hint = _city_from_url(page_url)

    for node in tree.css("a[href*='/imovel/']"):
        href = node.attributes.get("href") or ""
        source_url = urljoin(BROGNOLI_BASE, href)
        if source_url in seen_urls:
            continue

        text = _clean_text(node.text(separator=" "))
        price = _price(text)
        if not text or not price:
            continue
        seen_urls.add(source_url)

        city, neighborhood = _location(text, city_hint)
        listings.append(
            RawListing(
                source="brognoli",
                source_id=source_url.rstrip("/").split("_")[-1],
                source_url=source_url,
                title=_title(text),
                description=text,
                price=price,
                condo_fee=None,
                iptu_yearly=None,
                city=city,
                neighborhood=neighborhood,
                address=_address(text),
                property_type=_property_type(text),
                area_privative=_area(text),
                bedrooms=_room_count(text, "quarto"),
                bathrooms=None,
                parking_spots=_room_count(text, "garagem"),
                photos=[],
                raw_payload={"page_url": page_url, "card_text": text},
            )
        )

    return listings


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _price(text: str) -> Decimal | None:
    match = re.search(r"Valor:\s*R\$\s*([\d.]+(?:,\d{2})?)", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"R\$\s*([\d.]+(?:,\d{2})?)", text)
    if not match:
        return None
    return Decimal(match.group(1).replace(".", "").replace(",", "."))


def _area(text: str) -> Decimal | None:
    match = re.search(r"(\d+(?:[,.]\d+)?)m²", text)
    return Decimal(match.group(1).replace(",", ".")) if match else None


def _room_count(text: str, label: str) -> int | None:
    match = re.search(rf"(\d+)\s+{label}", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _property_type(text: str) -> str:
    lowered = text.lower()
    if "terreno" in lowered:
        return "terreno"
    if "casa" in lowered:
        return "casa"
    if "apartamento" in lowered or "cobertura" in lowered:
        return "apartamento"
    return "imovel"


def _location(text: str, city_hint: str) -> tuple[str, str | None]:
    match = re.search(r"-\s*([^,]+),\s*(Florianópolis|São José|Palhoça|Biguaçu)/SC", text)
    if match:
        return match.group(2), _clean_text(match.group(1))
    return city_hint, None


def _city_from_url(url: str) -> str:
    for slug, city in CITY_SLUGS.items():
        if f"/{slug}/" in url:
            return city
    return "Florianópolis"


def _title(text: str) -> str:
    marker = " Valor:"
    if marker in text:
        text = text.split(marker, 1)[0]
    return text[:180]


def _address(text: str) -> str | None:
    match = re.search(
        r"((?:Rua|Avenida|Servidão|Rodovia|Estrada|Travessa|Alameda)\s+[^-]+)",
        text,
        flags=re.IGNORECASE,
    )
    return _clean_text(match.group(1)) if match else None
