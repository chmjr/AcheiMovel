from radar.models import Base


def test_metadata_registers_core_tables():
    expected_tables = {
        "properties",
        "source_listings",
        "price_history",
        "auction_details",
        "bank_owned_details",
        "neighborhood_stats",
        "deal_analyses",
        "investor_profile",
        "watchlist",
        "alert_rules",
        "alerts_sent",
        "scrape_runs",
    }

    assert expected_tables.issubset(set(Base.metadata.tables))
