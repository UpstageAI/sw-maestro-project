import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class TestnetConfig(Base):
    __tablename__ = "testnet_configs"

    config_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    rest_base_url: Mapped[str] = mapped_column(String, nullable=False)
    ws_stream_url: Mapped[str] = mapped_column(String, nullable=False)
    ws_api_url: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    balance_snapshots: Mapped[list["BalanceSnapshot"]] = relationship(back_populates="config")
    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="config")
    spot_orders: Mapped[list["SpotOrder"]] = relationship(back_populates="config")
    stream_events: Mapped[list["StreamEvent"]] = relationship(back_populates="config")


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    config_id: Mapped[str] = mapped_column(ForeignKey("testnet_configs.config_id"), nullable=True)
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    config: Mapped["TestnetConfig"] = relationship(back_populates="balance_snapshots")


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    snapshot_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    config_id: Mapped[str] = mapped_column(ForeignKey("testnet_configs.config_id"), nullable=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    snapshot_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    config: Mapped["TestnetConfig"] = relationship(back_populates="price_snapshots")


class SpotOrder(Base):
    __tablename__ = "spot_orders"

    order_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    config_id: Mapped[str] = mapped_column(ForeignKey("testnet_configs.config_id"), nullable=True)
    binance_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    request_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    response_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String, nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    config: Mapped["TestnetConfig"] = relationship(back_populates="spot_orders")
    status_logs: Mapped[list["OrderStatusLog"]] = relationship(back_populates="order")
    cancel_logs: Mapped[list["CancelLog"]] = relationship(back_populates="order")
    reports: Mapped[list["Report"]] = relationship(back_populates="order")


class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"

    log_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("spot_orders.order_id"), nullable=False)
    status_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    order: Mapped["SpotOrder"] = relationship(back_populates="status_logs")


class CancelLog(Base):
    __tablename__ = "cancel_logs"

    cancel_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    order_id: Mapped[str] = mapped_column(ForeignKey("spot_orders.order_id"), nullable=False)
    cancel_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    order: Mapped["SpotOrder"] = relationship(back_populates="cancel_logs")


class StreamEvent(Base):
    __tablename__ = "stream_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    config_id: Mapped[str] = mapped_column(ForeignKey("testnet_configs.config_id"), nullable=True)
    stream_name: Mapped[str] = mapped_column(String, nullable=False)
    event_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    config: Mapped["TestnetConfig"] = relationship(back_populates="stream_events")


class Report(Base):
    __tablename__ = "reports"

    report_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    order_id: Mapped[str | None] = mapped_column(ForeignKey("spot_orders.order_id"), nullable=True)
    report_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    order: Mapped["SpotOrder | None"] = relationship(back_populates="reports")


class AgentRunCheckpoint(Base):
    __tablename__ = "agent_run_checkpoints"

    run_id: Mapped[str] = mapped_column(String, primary_key=True)
    lifecycle_status: Mapped[str] = mapped_column(String, nullable=False)
    hold_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    state_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    schema_version: Mapped[str] = mapped_column(String, nullable=False, default="1.0")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
