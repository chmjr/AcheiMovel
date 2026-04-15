from decimal import Decimal

from radar.schemas import ManualPropertyCreate
from radar.services.fingerprint import manual_property_fingerprint


def test_manual_property_fingerprint_is_stable_for_same_asset():
    first = ManualPropertyCreate(
        title="Apartamento teste",
        property_type="apartamento",
        city="São José",
        neighborhood="Kobrasol",
        address="Rua X, 100",
        purchase_price=Decimal("223000"),
        area_privative=Decimal("72"),
        bedrooms=2,
    )
    second = first.model_copy(update={"title": "Outro titulo", "purchase_price": Decimal("229000")})

    assert manual_property_fingerprint(first) == manual_property_fingerprint(second)
