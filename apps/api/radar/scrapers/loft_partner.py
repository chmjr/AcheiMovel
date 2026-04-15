from decimal import Decimal
import os
import re
from typing import Any
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from selectolax.parser import HTMLParser

from radar.scrapers.base import BaseScraper, RawListing
from radar.services.ingestion import persist_raw_listing

SEARCH_TYPES = ("Apartamento", "Casa", "Casa em Condomínio", "Cobertura", "Terreno")
MAX_PAGES_PER_TYPE = max(1, int(os.getenv("LOFT_PARTNER_PAGES_PER_TYPE", "1")))
CITY_NAMES = ("Florianópolis", "São José", "Palhoça", "Biguaçu")


class LoftPartnerScraper(BaseScraper):
    category = "common"
    source: str
    base_url: str

    async def discover(self):
        for listing_type in SEARCH_TYPES:
            for page in range(1, MAX_PAGES_PER_TYPE + 1):
                query = {"tipo": listing_type}
                if page > 1:
                    query["pagina"] = str(page)
                yield f"{self.base_url}/busca?{urlencode(query)}"

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
                    listings = _extract_listings(
                        response.text,
                        str(response.url),
                        self.base_url,
                        self.source,
                        seen_urls,
                    )
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


class KzueScraper(LoftPartnerScraper):
    source = "kzue"
    base_url = "https://kzueimoveis.com.br"


class CasaMareScraper(LoftPartnerScraper):
    source = "casamare"
    base_url = "https://casamareimoveis.com.br"


def _extract_listings(
    html: str,
    page_url: str,
    base_url: str,
    source: str,
    seen_urls: set[str],
) -> list[RawListing]:
    tree = HTMLParser(html)
    listings = []

    for node in tree.css("a[href*='/imovel/']"):
        text = _clean_text(node.text(separator=" "))
        if "R$" not in text or "Cód:" not in text:
            continue

        href = node.attributes.get("href") or ""
        source_url = urljoin(base_url, href)
        if source_url in seen_urls:
            continue

        price = _first_money(text)
        source_id = _source_id(source_url, text)
        if not price or not source_id:
            continue

        seen_urls.add(source_url)
        city, neighborhood = _location(text)
        property_type = _property_type(text)

        listings.append(
            RawListing(
                source=source,
                source_id=source_id,
                source_url=source_url,
                title=_title(text),
                description=text,
                price=price,
                condo_fee=None,
                iptu_yearly=None,
                city=city,
                neighborhood=neighborhood,
                address=None,
                property_type=property_type,
                area_privative=_area(text),
                bedrooms=_metric(text, "Dorm"),
                bathrooms=_metric(text, "Ban"),
                parking_spots=None,
                photos=[],
                raw_payload={"page_url": page_url, "card_text": text},
            )
        )

    return listings


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _source_id(url: str, text: str) -> str | None:
    code_match = re.search(r"Cód:\s*([A-Za-z0-9-]+)", text)
    if code_match:
        return code_match.group(1)
    path = urlparse(url).path.rstrip("/")
    return path.split("-")[-1] or path.split("/")[-1] or None


def _first_money(text: str) -> Decimal | None:
    match = re.search(r"R\$\s*([\d.]+(?:,\d{2})?)", text)
    if not match:
        return None
    return Decimal(match.group(1).replace(".", "").replace(",", "."))


def _area(text: str) -> Decimal | None:
    match = re.search(r"(\d+(?:[,.]\d+)?)\s*m²", text)
    if not match:
        return None
    return Decimal(match.group(1).replace(",", "."))


def _metric(text: str, label: str) -> int | None:
    match = re.search(rf"{label}\s+(\d+)", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _property_type(text: str) -> str:
    lowered = text.lower()
    if "terreno" in lowered:
        return "terreno"
    if "casa" in lowered:
        return "casa"
    if "cobertura" in lowered:
        return "apartamento"
    if "apartamento" in lowered or "studio" in lowered:
        return "apartamento"
    return "imovel"


def _location(text: str) -> tuple[str, str | None]:
    city_pattern = "|".join(CITY_NAMES)
    matches = re.findall(r"R\$\s*[\d.]+(?:,\d{2})?\s+(.+?),\s*(" + city_pattern + r")\s*-\s*SC", text)
    if matches:
        neighborhood, city = matches[-1]
        return city, _clean_text(neighborhood)

    fallback = re.findall(r"([^,]{2,80}),\s*(" + city_pattern + r")\s*-\s*SC", text)
    if fallback:
        neighborhood, city = fallback[-1]
        return city, _clean_text(neighborhood)

    return "Florianópolis", None


def _title(text: str) -> str:
    price_match = re.search(r"\s+R\$\s*[\d.]+(?:,\d{2})?", text)
    before_price = text[: price_match.start()] if price_match else text
    before_price = re.sub(r"^Cód:\s*[A-Za-z0-9-]+\s*", "", before_price)
    before_price = re.sub(r"^Comparar\s*", "", before_price)
    before_price = re.sub(r"^(?:Dorm\s+\d+\s*)?(?:Ban\s+\d+\s*)?(?:\d+(?:[,.]\d+)?\s*m²\s*)?", "", before_price)
    before_price = re.sub(
        r"^(Apartamento|Casa em Condomínio|Casa|Cobertura|Terreno|Sala Comercial|Sítio)\s+",
        "",
        before_price,
        flags=re.IGNORECASE,
    )
    return _clean_text(before_price)[:180]
