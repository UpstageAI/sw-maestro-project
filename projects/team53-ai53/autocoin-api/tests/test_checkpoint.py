from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.crud import get_checkpoint, save_or_update_checkpoint


def test_save_checkpoint_creates_new(client: TestClient, db_session: Session):
    cp = save_or_update_checkpoint(db_session, "run_001", "HOLD", "HOLD_REVIEW_REQUIRED", {"key": "val"})
    assert cp.run_id == "run_001"
    assert cp.lifecycle_status == "HOLD"
    assert cp.hold_reason == "HOLD_REVIEW_REQUIRED"
    assert cp.state_json == {"key": "val"}
    assert cp.expires_at.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc)


def test_save_checkpoint_updates_existing(client: TestClient, db_session: Session):
    save_or_update_checkpoint(db_session, "run_002", "HOLD", "HOLD_DATA_INSUFFICIENT", {"v": 1})
    updated = save_or_update_checkpoint(db_session, "run_002", "READY_FOR_BE", None, {"v": 2})
    assert updated.lifecycle_status == "READY_FOR_BE"
    assert updated.hold_reason is None
    assert updated.state_json == {"v": 2}


def test_get_checkpoint_returns_none_for_unknown(client: TestClient, db_session: Session):
    assert get_checkpoint(db_session, "nonexistent_run") is None


def test_get_checkpoint_returns_existing(client: TestClient, db_session: Session):
    save_or_update_checkpoint(db_session, "run_003", "HOLD", None, {})
    cp = get_checkpoint(db_session, "run_003")
    assert cp is not None
    assert cp.run_id == "run_003"


def test_checkpoint_ttl_is_set(client: TestClient, db_session: Session):
    cp = save_or_update_checkpoint(db_session, "run_004", "HOLD", None, {}, ttl_minutes=30)
    expires = cp.expires_at.replace(tzinfo=timezone.utc)
    assert datetime.now(timezone.utc) + timedelta(minutes=29) < expires
    assert expires < datetime.now(timezone.utc) + timedelta(minutes=31)
