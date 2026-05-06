from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import (
    BalanceSnapshot,
    CancelLog,
    OrderStatusLog,
    PriceSnapshot,
    Report,
    SpotOrder,
    StreamEvent,
    TestnetConfig,
)


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
    return db.execute(select(TestnetConfig).order_by(TestnetConfig.created_at.desc())).scalars().first()


def save_balance_snapshot(db: Session, snapshot_json: dict, config_id: str | None = None) -> BalanceSnapshot:
    snapshot = BalanceSnapshot(snapshot_json=snapshot_json, config_id=config_id)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def save_price_snapshot(db: Session, symbol: str, snapshot_json: dict, config_id: str | None = None) -> PriceSnapshot:
    snapshot = PriceSnapshot(symbol=symbol, snapshot_json=snapshot_json, config_id=config_id)
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return snapshot


def save_spot_order(
    db: Session,
    symbol: str,
    request_json: dict,
    response_json: dict | None = None,
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


def update_spot_order_status(db: Session, order_id: str, status: str, response_json: dict | None = None) -> SpotOrder | None:
    order = db.execute(select(SpotOrder).where(SpotOrder.order_id == order_id)).scalars().first()
    if not order:
        return None
    order.status = status
    if response_json is not None:
        order.response_json = response_json
    db.commit()
    db.refresh(order)
    return order


def save_order_status_log(db: Session, order_id: str, status_json: dict) -> OrderStatusLog:
    log = OrderStatusLog(order_id=order_id, status_json=status_json)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def save_cancel_log(db: Session, order_id: str, cancel_json: dict) -> CancelLog:
    log = CancelLog(order_id=order_id, cancel_json=cancel_json)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def save_stream_event(db: Session, stream_name: str, event_json: dict, config_id: str | None = None) -> StreamEvent:
    event = StreamEvent(stream_name=stream_name, event_json=event_json, config_id=config_id)
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def save_report(db: Session, report_json: dict, order_id: str | None = None) -> Report:
    report = Report(report_json=report_json, order_id=order_id)
    db.add(report)
    db.commit()
    db.refresh(report)
    return report
