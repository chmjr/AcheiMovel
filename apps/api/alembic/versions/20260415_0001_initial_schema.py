"""initial schema

Revision ID: 20260415_0001
Revises:
Create Date: 2026-04-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "20260415_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "properties",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("fingerprint", sa.String(), nullable=False, unique=True),
        sa.Column("property_type", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("neighborhood", sa.String(), nullable=False),
        sa.Column("address", sa.String()),
        sa.Column("lat", sa.Numeric(10, 7)),
        sa.Column("lng", sa.Numeric(10, 7)),
        sa.Column("area_privative", sa.Numeric(10, 2)),
        sa.Column("area_total", sa.Numeric(10, 2)),
        sa.Column("bedrooms", sa.Integer()),
        sa.Column("bathrooms", sa.Integer()),
        sa.Column("parking_spots", sa.Integer()),
        sa.Column("floor", sa.Integer()),
        sa.Column("has_elevator", sa.Boolean()),
        sa.Column("age_years", sa.Integer()),
        sa.Column("condition", sa.String()),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_properties_city_neigh", "properties", ["city", "neighborhood"])
    op.create_index("idx_properties_category", "properties", ["category"])

    op.create_table(
        "source_listings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id", ondelete="CASCADE")),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("source_id", sa.String()),
        sa.Column("title", sa.String()),
        sa.Column("description", sa.String()),
        sa.Column("price", sa.Numeric(14, 2)),
        sa.Column("condo_fee", sa.Numeric(10, 2)),
        sa.Column("iptu_yearly", sa.Numeric(10, 2)),
        sa.Column("photos", postgresql.JSONB()),
        sa.Column("raw_payload", postgresql.JSONB()),
        sa.Column("listed_at", sa.DateTime(timezone=True)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true()),
        sa.UniqueConstraint("source", "source_id", name="uq_source_listing_source_id"),
    )
    op.create_index("idx_source_listings_active", "source_listings", ["is_active", "last_seen_at"])

    op.create_table(
        "price_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            "source_listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_listings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("price", sa.Numeric(14, 2), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "auction_details",
        sa.Column(
            "source_listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_listings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("auction_type", sa.String()),
        sa.Column("auctioneer", sa.String()),
        sa.Column("appraisal_value", sa.Numeric(14, 2)),
        sa.Column("minimum_bid", sa.Numeric(14, 2)),
        sa.Column("discount_pct", sa.Numeric(5, 2)),
        sa.Column("is_occupied", sa.Boolean()),
        sa.Column("auction_date", sa.DateTime(timezone=True)),
        sa.Column("second_auction_date", sa.DateTime(timezone=True)),
        sa.Column("matricula", sa.String()),
        sa.Column("debts_disclosed", sa.Numeric(14, 2)),
        sa.Column("auctioneer_fee_pct", sa.Numeric(5, 2)),
        sa.Column("edital_url", sa.String()),
        sa.Column("financeable", sa.Boolean()),
    )

    op.create_table(
        "bank_owned_details",
        sa.Column(
            "source_listing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_listings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("bank", sa.String(), nullable=False),
        sa.Column("sale_modality", sa.String()),
        sa.Column("discount_pct", sa.Numeric(5, 2)),
        sa.Column("financeable", sa.Boolean()),
        sa.Column("fgts_allowed", sa.Boolean()),
        sa.Column("minimum_entry_pct", sa.Numeric(5, 2)),
    )

    op.create_table(
        "neighborhood_stats",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("neighborhood", sa.String(), nullable=False),
        sa.Column("property_type", sa.String(), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False),
        sa.Column("price_per_sqm_p25", sa.Numeric(10, 2)),
        sa.Column("price_per_sqm_p50", sa.Numeric(10, 2)),
        sa.Column("price_per_sqm_p65", sa.Numeric(10, 2)),
        sa.Column("price_per_sqm_p75", sa.Numeric(10, 2)),
        sa.Column("avg_days_listed", sa.Integer()),
        sa.Column("liquidity_score", sa.Numeric(3, 1)),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("city", "neighborhood", "property_type", name="uq_neighborhood_stats_scope"),
    )

    op.create_table(
        "deal_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("scenario", sa.String(), nullable=False),
        sa.Column("financing_mode", sa.String(), nullable=False),
        sa.Column("purchase_price", sa.Numeric(14, 2)),
        sa.Column("estimated_market_value", sa.Numeric(14, 2)),
        sa.Column("estimated_resale_value", sa.Numeric(14, 2)),
        sa.Column("renovation_level", sa.String()),
        sa.Column("renovation_cost", sa.Numeric(14, 2)),
        sa.Column("transaction_costs", sa.Numeric(14, 2)),
        sa.Column("holding_costs", sa.Numeric(14, 2)),
        sa.Column("selling_costs", sa.Numeric(14, 2)),
        sa.Column("contingency", sa.Numeric(14, 2)),
        sa.Column("total_cost", sa.Numeric(14, 2)),
        sa.Column("capital_required", sa.Numeric(14, 2)),
        sa.Column("estimated_profit", sa.Numeric(14, 2)),
        sa.Column("margin_pct", sa.Numeric(5, 2)),
        sa.Column("roi_pct", sa.Numeric(5, 2)),
        sa.Column("annualized_roi_pct", sa.Numeric(6, 2)),
        sa.Column("estimated_months", sa.Integer()),
        sa.Column("risk_level", sa.String()),
        sa.Column("risk_flags", postgresql.JSONB()),
        sa.Column("score", sa.Numeric(5, 2)),
        sa.Column("decision", sa.String()),
        sa.Column("score_breakdown", postgresql.JSONB()),
        sa.Column("computed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_deal_analyses_score", "deal_analyses", ["score"])
    op.create_index("idx_deal_analyses_decision", "deal_analyses", ["decision"])

    op.create_table(
        "investor_profile",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("max_capital", sa.Numeric(14, 2), nullable=False),
        sa.Column("min_profit", sa.Numeric(14, 2), nullable=False),
        sa.Column("min_margin_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("min_score", sa.Integer(), nullable=False),
        sa.Column("max_months", sa.Integer(), nullable=False),
        sa.Column("allow_financing", sa.Boolean(), nullable=False),
        sa.Column("default_entry_pct", sa.Numeric(5, 2), nullable=False),
        sa.Column("interest_rate_yearly", sa.Numeric(5, 2), nullable=False),
        sa.Column("target_cities", postgresql.JSONB(), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_investor_profile_singleton"),
    )

    op.create_table(
        "watchlist",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("notes", sa.String()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "alert_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
        sa.Column("conditions", postgresql.JSONB(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), nullable=False),
    )

    op.create_table(
        "alerts_sent",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("alert_rule_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("alert_rules.id")),
        sa.Column("property_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("properties.id")),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "scrape_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String()),
        sa.Column("items_collected", sa.Integer(), nullable=False),
        sa.Column("items_new", sa.Integer(), nullable=False),
        sa.Column("items_updated", sa.Integer(), nullable=False),
        sa.Column("error", sa.String()),
    )


def downgrade() -> None:
    op.drop_table("scrape_runs")
    op.drop_table("alerts_sent")
    op.drop_table("alert_rules")
    op.drop_table("watchlist")
    op.drop_table("investor_profile")
    op.drop_index("idx_deal_analyses_decision", table_name="deal_analyses")
    op.drop_index("idx_deal_analyses_score", table_name="deal_analyses")
    op.drop_table("deal_analyses")
    op.drop_table("neighborhood_stats")
    op.drop_table("bank_owned_details")
    op.drop_table("auction_details")
    op.drop_table("price_history")
    op.drop_index("idx_source_listings_active", table_name="source_listings")
    op.drop_table("source_listings")
    op.drop_index("idx_properties_category", table_name="properties")
    op.drop_index("idx_properties_city_neigh", table_name="properties")
    op.drop_table("properties")
