"""SessionManager 및 Session 단위 테스트."""
import threading
import time
import pytest
from src.services.session_manager import SessionManager, Session, State


class TestSessionCreate:
    def setup_method(self):
        self.mgr = SessionManager()

    def test_create_returns_session(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        assert isinstance(s, Session)

    def test_create_session_id_is_12_chars(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        assert len(s.id) == 12

    def test_create_generates_unique_ids(self):
        ids = {self.mgr.create(repo_url="https://github.com/a/b").id for _ in range(20)}
        assert len(ids) == 20

    def test_create_sets_repo_url(self):
        url = "https://github.com/myuser/myrepo"
        s = self.mgr.create(repo_url=url)
        assert s.repo_url == url

    def test_create_initial_state_is_init(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        assert s.state == State.INIT

    def test_create_with_optional_fields(self):
        s = self.mgr.create(
            repo_url="https://github.com/a/b",
            pat="ghp_testtoken",
            notion_token="secret-notion",
            notion_parent_page_id="page-123",
            user_attached_info="추가 정보입니다.",
        )
        assert s.pat == "ghp_testtoken"
        assert s.notion_token == "secret-notion"
        assert s.user_attached_info == "추가 정보입니다."


class TestSessionGet:
    def setup_method(self):
        self.mgr = SessionManager()

    def test_get_existing_session(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        assert self.mgr.get(s.id) is s

    def test_get_nonexistent_returns_none(self):
        assert self.mgr.get("nonexistent_id") is None

    def test_get_after_multiple_creates(self):
        s1 = self.mgr.create(repo_url="https://github.com/a/b")
        s2 = self.mgr.create(repo_url="https://github.com/c/d")
        assert self.mgr.get(s1.id) is s1
        assert self.mgr.get(s2.id) is s2
        assert self.mgr.get(s1.id) is not s2


class TestSessionState:
    def setup_method(self):
        self.mgr = SessionManager()

    def test_set_state_changes_state(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.set_state(State.FETCHING)
        assert s.state == State.FETCHING

    def test_set_state_appends_to_log(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.set_state(State.FETCHING, "레포 fetch 시작")
        assert any("FETCHING" in line for line in s.log)

    def test_set_state_with_message_appears_in_log(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.set_state(State.GENERATING, "4섹션 병렬 생성")
        assert any("4섹션 병렬 생성" in line for line in s.log)

    def test_set_state_updates_last_state_change(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        before = s.last_state_change
        time.sleep(0.01)
        s.set_state(State.FETCHING)
        assert s.last_state_change > before

    def test_state_sequence(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        for state in [State.FETCHING, State.COMPRESSING, State.GENERATING, State.DONE]:
            s.set_state(state)
        assert s.state == State.DONE

    def test_set_state_is_thread_safe(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        errors = []

        def toggle():
            try:
                for st in [State.FETCHING, State.GENERATING, State.VALIDATING, State.DONE]:
                    s.set_state(st)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=toggle) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"스레드 안전 실패: {errors}"


class TestSessionAbort:
    def setup_method(self):
        self.mgr = SessionManager()

    def test_request_abort_sets_aborted_state(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.request_abort("테스트 중단")
        assert s.state == State.ABORTED

    def test_request_abort_sets_abort_event(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.request_abort("테스트 중단")
        assert s.abort_event.is_set()

    def test_request_abort_sets_error_message(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.request_abort("사용자 요청")
        assert "사용자 요청" in s.error

    def test_check_abort_raises_when_aborted(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.request_abort("테스트")
        with pytest.raises(RuntimeError, match="aborted"):
            s.check_abort()

    def test_check_abort_does_not_raise_when_not_aborted(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.check_abort()  # 예외 없이 통과해야 함

    def test_abort_appears_in_log(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.request_abort("테스트 중단 메시지")
        assert any("ABORTED" in line for line in s.log)


class TestStateConstants:
    def test_all_expected_states_defined(self):
        expected = {
            "INIT", "FETCHING", "COMPRESSING", "INTERVIEWING",
            "GENERATING", "VALIDATING", "REFINING", "DIAGRAMMING",
            "MERGING", "READY_FOR_TEMPLATE", "PUBLISHING", "DONE",
            "ERROR", "ABORTED",
        }
        actual = {v for k, v in vars(State).items() if not k.startswith("_")}
        assert expected == actual, f"누락: {expected - actual}, 추가: {actual - expected}"
