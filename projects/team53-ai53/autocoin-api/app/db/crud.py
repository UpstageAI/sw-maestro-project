from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    AgentRunCheckpoint,
    BalanceSnapshot,
    CancelLog,
    OrderStatusLog,
    PriceSnapshot,
    Report,
    SpotOrder,
    StreamEvent,
    TestnetConfig,
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def save_testnet_config(db: Session, rest_base_url: str, ws_stream_url: str, ws_api_url: str) -> TestnetConfig:
    config = TestnetConfig(
        rest_base_url=rest_base_url,
        ws_stream_url=ws_stream_url,
        ws_api_url=ws_api_url,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


def get_latest_testnet_config(db: Session) -> TestnetConfig | None:
    return db.scalars(select(TestnetConfig).order_by(TestnetConfig.created_at.desc())).first()


def save_balance_snapshot(db: Session, snapshot_json: dict[str, object], config_id: str | None = None) -> BalanceSnapshot:
    snapshot = BalanceSnapshot(snapshot_json=snapshot_json, config_id=config_id)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def save_price_snapshot(db: Session, symbol: str, snapshot_json: dict[str, object], config_id: str | None = None) -> PriceSnapshot:
    snapshot = PriceSnapshot(symbol=symbol, snapshot_json=snapshot_json, config_id=config_id)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def save_spot_order(
    db: Session,
    symbol: str,
    request_json: dict[str, object],
    response_json: dict[str, object] | None = None,
    binance_order_id: str | None = None,
    status: str = "PENDING",
    config_id: str | None = None,
) -> SpotOrder:
    order = SpotOrder(
        symbol=symbol,
        request_json=request_json,
        response_json=response_json,
        binance_order_id=binance_order_id,
        status=status,
        config_id=config_id,
    )
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


def get_spot_order_by_binance_id(db: Session, binance_order_id: str) -> SpotOrder | None:
    return db.scalars(
        select(SpotOrder).where(SpotOrder.binance_order_id == binance_order_id)
    ).first()


def update_spot_order_status(
    db: Session,
    order_id: str,
    status: str,
    response_json: dict[str, object] | None = None,
) -> SpotOrder | None:
    order = db.get(SpotOrder, order_id)
    if not order:
        return None
    order.status = status
    if response_json is not None:
        order.response_json = response_json
    db.commit()
    db.refresh(order)
    return order


def save_order_status_log(db: Session, order_id: str, status_json: dict[str, object]) -> OrderStatusLog:
    log = OrderStatusLog(order_id=order_id, status_json=status_json)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def save_cancel_log(db: Session, order_id: str, cancel_json: dict[str, object]) -> CancelLog:
    log = CancelLog(order_id=order_id, cancel_json=cancel_json)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def save_stream_event(db: Session, stream_name: str, event_json: dict[str, object], config_id: str | None = None) -> StreamEvent:
    event = StreamEvent(stream_name=stream_name, event_json=event_json, config_id=config_id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def save_or_update_report(
    db: Session,
    run_id: str,
    report_json: dict[str, object],
    order_id: str | None = None,
) -> Report:
    report = db.scalars(select(Report).where(Report.run_id == run_id)).first()
    if report:
        report.report_json = report_json
        if order_id is not None:
            report.order_id = order_id
        db.commit()
        db.refresh(report)
        return report

    report = Report(run_id=run_id, report_json=report_json, order_id=order_id)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


def get_report_by_run_id(db: Session, run_id: str) -> Report | None:
    return db.scalars(select(Report).where(Report.run_id == run_id)).first()


def save_or_update_checkpoint(
    db: Session,
    run_id: str,
    lifecycle_status: str,
    hold_reason: str | None,
    state_json: dict[str, object],
    schema_version: str = "1.0",
    ttl_minutes: int = 60,
) -> AgentRunCheckpoint:
    expires_at = _now() + timedelta(minutes=ttl_minutes)
    checkpoint = db.get(AgentRunCheckpoint, run_id)
    if checkpoint:
        checkpoint.lifecycle_status = lifecycle_status
        checkpoint.hold_reason = hold_reason
        checkpoint.state_json = state_json
        checkpoint.expires_at = expires_at
        db.commit()
        db.refresh(checkpoint)
        return checkpoint
    checkpoint = AgentRunCheckpoint(
        run_id=run_id,
        lifecycle_status=lifecycle_status,
        hold_reason=hold_reason,
        state_json=state_json,
        schema_version=schema_version,
        expires_at=expires_at,
    )
    db.add(checkpoint)
    db.commit()
    db.refresh(checkpoint)
    return checkpoint


def get_checkpoint(db: Session, run_id: str) -> AgentRunCheckpoint | None:
    return db.get(AgentRunCheckpoint, run_id)
