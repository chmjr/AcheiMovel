from decimal import Decimal

from radar.schemas import RenovationLevel


RENOVATION_COST_PER_SQM = {
    "light": Decimal("600"),
    "medium": Decimal("1200"),
}


def estimate_renovation_cost(area_privative: Decimal, level: RenovationLevel) -> Decimal:
    return (area_privative * RENOVATION_COST_PER_SQM[level]).quantize(Decimal("0.01"))
