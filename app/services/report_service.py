from sqlalchemy.orm import Session

from app.db.crud import save_report
from app.db.models import Report


def save_run_report(db: Session, report_json: dict, order_id: str | None = None) -> Report:
    return save_report(db, report_json=report_json, order_id=order_id)
