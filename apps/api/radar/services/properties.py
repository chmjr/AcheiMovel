from sqlalchemy.orm import Session

from radar.models.listing import PriceHistory, SourceListing
from radar.models.property import Property
from radar.schemas import ManualPropertyCreate, ManualPropertyResponse
from radar.services.fingerprint import manual_property_fingerprint


def create_manual_property(db: Session, payload: ManualPropertyCreate) -> ManualPropertyResponse:
    fingerprint = manual_property_fingerprint(payload)
    existing = db.query(Property).filter(Property.fingerprint == fingerprint).one_or_none()
    if existing:
        listing = existing.source_listings[0]
        return _response(existing, listing, payload.title, payload.source_name)

    prop = Property(
        fingerprint=fingerprint,
        property_type=payload.property_type,
        city=payload.city,
        neighborhood=payload.neighborhood,
        address=payload.address,
        area_privative=payload.area_privative,
        area_total=payload.area_total,
        bedrooms=payload.bedrooms,
        bathrooms=payload.bathrooms,
        parking_spots=payload.parking_spots,
        floor=payload.floor,
        has_elevator=payload.has_elevator,
        age_years=payload.age_years,
        condition=payload.condition,
        category=payload.category,
    )
    db.add(prop)
    db.flush()

    listing = SourceListing(
        property_id=prop.id,
        source="manual",
        source_id=str(prop.id),
        source_url=payload.source_url or f"manual://{prop.id}",
        title=payload.title,
        description=payload.description,
        price=payload.purchase_price,
        condo_fee=payload.condo_fee,
        iptu_yearly=payload.iptu_yearly,
        photos=[],
        raw_payload={
            "source_name": payload.source_name,
            "manual": True,
        },
    )
    db.add(listing)
    db.flush()
    db.add(PriceHistory(source_listing_id=listing.id, price=payload.purchase_price))
    db.commit()
    db.refresh(prop)
    db.refresh(listing)
    return _response(prop, listing, payload.title, payload.source_name)


def _response(
    prop: Property,
    listing: SourceListing,
    title: str,
    source_name: str,
) -> ManualPropertyResponse:
    return ManualPropertyResponse(
        property_id=str(prop.id),
        source_listing_id=str(listing.id),
        fingerprint=prop.fingerprint,
        title=title,
        city=prop.city,
        neighborhood=prop.neighborhood,
        purchase_price=listing.price,
        source_name=source_name,
    )
