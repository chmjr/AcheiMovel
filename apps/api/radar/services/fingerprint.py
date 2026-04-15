import hashlib
import re
from decimal import Decimal

from radar.schemas import ManualPropertyCreate
from radar.scrapers.base import RawListing


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    normalized = value.strip().lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def round_decimal(value: Decimal | None, step: int) -> str:
    if value is None:
        return ""
    rounded = int(value / step) * step
    return str(rounded)


def manual_property_fingerprint(payload: ManualPropertyCreate) -> str:
    parts = [
        normalize_text(payload.city),
        normalize_text(payload.neighborhood),
        normalize_text(payload.address),
        normalize_text(payload.property_type),
        round_decimal(payload.area_privative, 5),
        str(payload.bedrooms or ""),
        round_decimal(payload.purchase_price, 10000),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()


def raw_listing_fingerprint(listing: RawListing) -> str:
    parts = [
        normalize_text(listing.city),
        normalize_text(listing.neighborhood),
        normalize_text(listing.address),
        normalize_text(listing.property_type),
        round_decimal(listing.area_privative, 5),
        str(listing.bedrooms or ""),
        round_decimal(listing.price, 10000),
    ]
    return hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
