from dataclasses import asdict

from sqlalchemy.orm import Session

from radar.models.listing import AuctionDetail, BankOwnedDetail, PriceHistory, SourceListing
from radar.models.property import Property
from radar.scrapers.base import RawListing
from radar.services.fingerprint import raw_listing_fingerprint


def persist_raw_listing(db: Session, listing: RawListing) -> str:
    prop = _get_or_create_property(db, listing)
    source_listing = (
        db.query(SourceListing)
        .filter(SourceListing.source == listing.source, SourceListing.source_id == listing.source_id)
        .one_or_none()
    )

    if source_listing:
        previous_price = source_listing.price
        source_listing.property_id = prop.id
        source_listing.source_url = listing.source_url
        source_listing.title = listing.title
        source_listing.description = listing.description
        source_listing.price = listing.price
        source_listing.condo_fee = listing.condo_fee
        source_listing.iptu_yearly = listing.iptu_yearly
        source_listing.photos = listing.photos
        source_listing.raw_payload = listing.raw_payload or asdict(listing)
        source_listing.is_active = True
        status = "updated"
        if listing.price is not None and listing.price != previous_price:
            db.add(PriceHistory(source_listing_id=source_listing.id, price=listing.price))
    else:
        source_listing = SourceListing(
            property_id=prop.id,
            source=listing.source,
            source_id=listing.source_id,
            source_url=listing.source_url,
            title=listing.title,
            description=listing.description,
            price=listing.price,
            condo_fee=listing.condo_fee,
            iptu_yearly=listing.iptu_yearly,
            photos=listing.photos,
            raw_payload=listing.raw_payload or asdict(listing),
        )
        db.add(source_listing)
        db.flush()
        if listing.price is not None:
            db.add(PriceHistory(source_listing_id=source_listing.id, price=listing.price))
        status = "new"

    if listing.bank_data:
        _upsert_bank_owned_detail(db, source_listing, listing)
    if listing.auction_data:
        _upsert_auction_detail(db, source_listing, listing)

    db.commit()
    return status


def _get_or_create_property(db: Session, listing: RawListing) -> Property:
    fingerprint = raw_listing_fingerprint(listing)
    prop = db.query(Property).filter(Property.fingerprint == fingerprint).one_or_none()
    if prop:
        return prop

    prop = Property(
        fingerprint=fingerprint,
        property_type=listing.property_type,
        city=listing.city,
        neighborhood=listing.neighborhood or "Não informado",
        address=listing.address,
        area_privative=listing.area_privative,
        bedrooms=listing.bedrooms,
        bathrooms=listing.bathrooms,
        parking_spots=listing.parking_spots,
        category="bank_owned" if listing.bank_data else "auction" if listing.auction_data else "common",
    )
    db.add(prop)
    db.flush()
    return prop


def _upsert_bank_owned_detail(
    db: Session,
    source_listing: SourceListing,
    listing: RawListing,
) -> None:
    detail = (
        db.query(BankOwnedDetail)
        .filter(BankOwnedDetail.source_listing_id == source_listing.id)
        .one_or_none()
    )
    bank_data = listing.bank_data or {}
    if not detail:
        detail = BankOwnedDetail(source_listing_id=source_listing.id, bank=bank_data.get("bank", "caixa"))
        db.add(detail)

    detail.bank = bank_data.get("bank", detail.bank)
    detail.sale_modality = bank_data.get("sale_modality")
    detail.discount_pct = bank_data.get("discount_pct")
    detail.financeable = bank_data.get("financeable")
    detail.fgts_allowed = bank_data.get("fgts_allowed")
    detail.minimum_entry_pct = bank_data.get("minimum_entry_pct")


def _upsert_auction_detail(
    db: Session,
    source_listing: SourceListing,
    listing: RawListing,
) -> None:
    detail = (
        db.query(AuctionDetail)
        .filter(AuctionDetail.source_listing_id == source_listing.id)
        .one_or_none()
    )
    auction_data = listing.auction_data or {}
    if not detail:
        detail = AuctionDetail(source_listing_id=source_listing.id)
        db.add(detail)

    detail.auction_type = auction_data.get("auction_type")
    detail.auctioneer = auction_data.get("auctioneer")
    detail.appraisal_value = auction_data.get("appraisal_value")
    detail.minimum_bid = auction_data.get("minimum_bid")
    detail.discount_pct = auction_data.get("discount_pct")
    detail.is_occupied = auction_data.get("is_occupied")
    detail.auction_date = auction_data.get("auction_date")
    detail.second_auction_date = auction_data.get("second_auction_date")
    detail.matricula = auction_data.get("matricula")
    detail.debts_disclosed = auction_data.get("debts_disclosed")
    detail.auctioneer_fee_pct = auction_data.get("auctioneer_fee_pct")
    detail.edital_url = auction_data.get("edital_url")
    detail.financeable = auction_data.get("financeable")
