from collections.abc import AsyncIterator
from decimal import Decimal
import re
from typing import Any
from urllib.parse import urljoin

import httpx

from radar.scrapers.base import BaseScraper, RawListing
from radar.scrapers.json_public import extract_next_data, extract_json_ld

QUINTO_BASE = "https://www.quintoandar.com.br"
QUINTO_START_URLS = (
    "https://www.quintoandar.com.br/comprar/imovel/florianopolis-sc-brasil",
    "https://www.quintoandar.com.br/comprar/imovel/sao-jose-sc-brasil",
    "https://www.quintoandar.com.br/comprar/imovel/palhoca-sc-brasil",
    "https://www.quintoandar.com.br/comprar/imovel/biguacu-sc-brasil",
)


class QuintoAndarScraper(BaseScraper):
    source = "quintoandar"
    category = "common"

    async def discover(self) -> AsyncIterator[str]:
        for url in QUINTO_START_URLS:
            yield url

    async def parse(self, url: str) -> RawListing | None:
        # The list page contains many houses. The BaseScraper contract parses one URL
        # into one listing, so this method is not used by run(); see run override.
        return None

    async def run(self, db) -> dict[str, Any]:
        from radar.services.ingestion import persist_raw_listing

        stats: dict[str, Any] = {
            "collected": 0,
            "parsed": 0,
            "new": 0,
            "updated": 0,
            "errors": 0,
            "error_messages": [],
        }
        async with httpx.AsyncClient(
            timeout=45,
            follow_redirects=True,
            trust_env=False,
            headers={"user-agent": "Mozilla/5.0"},
        ) as client:
            for url in QUINTO_START_URLS:
                try:
                    response = await client.get(url)
                    listings = _extract_listings(response.text, url)
                    stats["collected"] += len(listings)
                    for listing in listings:
                        status = persist_raw_listing(db, listing)
                        stats["parsed"] += 1
                        if status in {"new", "updated"}:
                            stats[status] += 1
                except Exception as exc:
                    db.rollback()
                    stats["errors"] += 1
                    stats["error_messages"].append(f"{url}: {exc}")
        return stats


def _extract_listings(html: str, page_url: str) -> list[RawListing]:
    data = extract_next_data(html)
    initial_state = ((data.get("props") or {}).get("pageProps") or {}).get("initialState") or {}
    houses = initial_state.get("houses") or {}
    json_ld_by_id = _json_ld_by_id(html)
    listings = []

    for house_id, house in houses.items():
        if not isinstance(house, dict):
            continue
        if not house.get("forSale") or not house.get("salePrice"):
            continue

        address = house.get("address") or {}
        source_url = json_ld_by_id.get(str(house_id)) or f"{QUINTO_BASE}/imovel/{house_id}/comprar"
        city = address.get("city") or _city_from_page_url(page_url)
        title = _title(house)

        listings.append(
            RawListing(
                source="quintoandar",
                source_id=str(house_id),
                source_url=source_url,
                title=title,
                description=house.get("shortSaleDescription") or house.get("shortRentDescription"),
                price=Decimal(str(house["salePrice"])),
                condo_fee=_condo_iptu(house),
                iptu_yearly=None,
                city=city,
                neighborhood=house.get("neighbourhood") or house.get("regionName"),
                address=address.get("address"),
                property_type=_property_type(house.get("type")),
                area_privative=Decimal(str(house["area"])) if house.get("area") else None,
                bedrooms=house.get("bedrooms"),
                bathrooms=house.get("bathrooms"),
                parking_spots=house.get("parkingSpots"),
                photos=_photo_urls(house.get("photos") or []),
                raw_payload={"house": house, "page_url": page_url},
            )
        )

    return listings


def _json_ld_by_id(html: str) -> dict[str, str]:
    urls = {}
    for payload in extract_json_ld(html):
        items = payload if isinstance(payload, list) else [payload]
        for item in items:
            if not isinstance(item, dict):
                continue
            url = item.get("url")
            match = re.search(r"/imovel/(\d+)/", url or "")
            if match:
                urls[match.group(1)] = url
    return urls


def _title(house: dict) -> str:
    kind = house.get("type") or "Imóvel"
    area = f"{house.get('area')}m²" if house.get("area") else ""
    neighborhood = house.get("neighbourhood") or house.get("regionName") or ""
    city = (house.get("address") or {}).get("city") or ""
    return " - ".join(part for part in [f"{kind} {area}".strip(), neighborhood, city] if part)


def _condo_iptu(house: dict) -> Decimal | None:
    value = house.get("condoIptu")
    return Decimal(str(value)) if value is not None else None


def _property_type(value: str | None) -> str:
    lowered = (value or "").lower()
    if "casa" in lowered:
        return "casa"
    if "apart" in lowered:
        return "apartamento"
    if "studio" in lowered or "kitnet" in lowered:
        return "apartamento"
    return "imovel"


def _photo_urls(photos: list[dict]) -> list[str]:
    urls = []
    for photo in photos[:10]:
        url = photo.get("url")
        if not url:
            continue
        if url.startswith("http"):
            urls.append(url)
        else:
            urls.append(urljoin("https://www.quintoandar.com.br/img/", url))
    return urls


def _city_from_page_url(url: str) -> str:
    if "sao-jose" in url:
        return "São José"
    if "palhoca" in url:
        return "Palhoça"
    if "biguacu" in url:
        return "Biguaçu"
    return "Florianópolis"
