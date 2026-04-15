from decimal import Decimal
import os
import re
from typing import Any
from urllib.parse import urljoin

import httpx
from selectolax.parser import HTMLParser

from radar.scrapers.base import BaseScraper, RawListing
from radar.services.ingestion import persist_raw_listing

CHAVES_BASE = "https://www.chavesnamao.com.br"
CITY_SLUGS = {
    "florianopolis": "Florianópolis",
    "sao-jose": "São José",
    "palhoca": "Palhoça",
    "biguacu": "Biguaçu",
}
START_PATHS = (
    "/imoveis-residenciais-a-venda/sc-{city}/",
    "/apartamentos-a-venda/sc-{city}/",
    "/casas-a-venda/sc-{city}/",
    "/terrenos-a-venda/sc-{city}/",
)
MAX_PAGES_PER_CATEGORY = max(1, int(os.getenv("CHAVES_PAGES_PER_CATEGORY", "1")))


class ChavesNaMaoScraper(BaseScraper):
    source = "chaves_na_mao"
    category = "common"

    async def discover(self):
        for city_slug in CITY_SLUGS:
            for path_template in START_PATHS:
                for page in range(1, MAX_PAGES_PER_CATEGORY + 1):
                    path = path_template.format(city=city_slug)
                    suffix = "" if page == 1 else f"?pg={page}"
                    yield urljoin(CHAVES_BASE, f"{path}{suffix}")

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

    for node in tree.css("a[href*='/imovel/'][href*='id-']"):
        href = node.attributes.get("href") or ""
        source_url = urljoin(CHAVES_BASE, href)
        if source_url in seen_urls:
            continue
        seen_urls.add(source_url)

        text = _clean_text(node.text(separator=" "))
        if not text:
            continue

        source_id = _source_id(source_url)
        price = _price_from_url(source_url) or _first_money(text)
        if not source_id or not price:
            continue

        city, neighborhood = _location(text, city_hint)
        title = _title(text, city, neighborhood)

        listings.append(
            RawListing(
                source="chaves_na_mao",
                source_id=source_id,
                source_url=source_url,
                title=title,
                description=text,
                price=price,
                condo_fee=_labeled_money(text, "Condomínio"),
                iptu_yearly=_labeled_money(text, "Iptu"),
                city=city,
                neighborhood=neighborhood,
                address=_address(text),
                property_type=_property_type(source_url, text),
                area_privative=_area(source_url, text),
                bedrooms=_room_count(source_url, text, "quarto"),
                bathrooms=None,
                parking_spots=None,
                photos=[],
                raw_payload={"page_url": page_url, "card_text": text},
            )
        )

    return listings


def _clean_text(value: str) -> str:
    return " ".join(value.split())


def _source_id(url: str) -> str | None:
    match = re.search(r"/id-(\d+)/", url)
    return match.group(1) if match else None


def _price_from_url(url: str) -> Decimal | None:
    match = re.search(r"-RS(\d+)", url)
    return Decimal(match.group(1)) if match else None


def _first_money(text: str) -> Decimal | None:
    match = re.search(r"R\$\s*([\d.]+(?:,\d{2})?)", text)
    if not match:
        return None
    return Decimal(match.group(1).replace(".", "").replace(",", "."))


def _labeled_money(text: str, label: str) -> Decimal | None:
    match = re.search(rf"{label}\s*R\$\s*([\d.]+(?:,\d{{2}})?)", text, flags=re.IGNORECASE)
    if not match:
        return None
    return Decimal(match.group(1).replace(".", "").replace(",", "."))


def _area(url: str, text: str) -> Decimal | None:
    match = re.search(r"-(\d+(?:\.\d+)?)m2-", url)
    if not match:
        match = re.search(r"(\d+(?:[,.]\d+)?)\s*m²", text)
    if not match:
        return None
    return Decimal(match.group(1).replace(",", "."))


def _room_count(url: str, text: str, label: str) -> int | None:
    match = re.search(rf"-(\d+)-{label}s?", url, flags=re.IGNORECASE)
    if not match:
        match = re.search(rf"(\d+)\s+{label}s?", text, flags=re.IGNORECASE)
    return int(match.group(1)) if match else None


def _property_type(url: str, text: str) -> str:
    lowered = f"{url} {text}".lower()
    if "terreno" in lowered:
        return "terreno"
    if "casa" in lowered or "sobrado" in lowered:
        return "casa"
    if "apartamento" in lowered or "cobertura" in lowered or "kitnet" in lowered:
        return "apartamento"
    return "imovel"


def _location(text: str, city_hint: str) -> tuple[str, str | None]:
    matches = re.findall(r"([^,]+),\s*(Florianópolis|São José|Palhoça|Biguaçu)/SC", text)
    if not matches:
        return city_hint, None
    neighborhood, city = matches[-1]
    return city, _clean_text(neighborhood)


def _city_from_url(url: str) -> str:
    for slug, city in CITY_SLUGS.items():
        if f"sc-{slug}" in url:
            return city
    return "Florianópolis"


def _title(text: str, city: str, neighborhood: str | None) -> str:
    markers = [" Endereço indisponível ", f" {city}/SC"]
    if neighborhood:
        markers.append(f" {neighborhood}, {city}/SC")
    end = min((text.find(marker) for marker in markers if text.find(marker) > 0), default=180)
    return text[:end].strip()


def _address(text: str) -> str | None:
    if "Endereço indisponível" in text:
        return None
    street_match = re.search(
        r"((?:Rua|Avenida|Servidão|Rodovia|Estrada|Travessa|Alameda)\s+[^,]+(?:,\s*[\w-]+)?)",
        text,
        flags=re.IGNORECASE,
    )
    return _clean_text(street_match.group(1)) if street_match else None
