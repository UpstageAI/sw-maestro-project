"""세션 관리 — state machine + in-memory 저장. 로컬 단일 사용자 가정."""
import threading
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional

from src.models.repo import RepoContext
from src.models.story import StoryDraft, Verdict


class State:
    INIT = "INIT"
    FETCHING = "FETCHING"
    COMPRESSING = "COMPRESSING"
    INTERVIEWING = "INTERVIEWING"
    GENERATING = "GENERATING"
    VALIDATING = "VALIDATING"
    REFINING = "REFINING"
    DIAGRAMMING = "DIAGRAMMING"
    MERGING = "MERGING"
    READY_FOR_TEMPLATE = "READY_FOR_TEMPLATE"
    PUBLISHING = "PUBLISHING"
    DONE = "DONE"
    ERROR = "ERROR"
    ABORTED = "ABORTED"


@dataclass
class Session:
    id: str
    repo_url: str
    pat: Optional[str] = None
    notion_token: Optional[str] = None
    notion_parent_page_id: Optional[str] = None
    user_attached_info: Optional[str] = None

    state: str = State.INIT
    log: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_state_change: float = field(default_factory=time.time)

    ctx: Optional[RepoContext] = None
    questions: list[str] = field(default_factory=list)
    answers: list[str] = field(default_factory=list)

    draft: StoryDraft = field(default_factory=StoryDraft)
    verdict: Optional[Verdict] = None
    history: list[Verdict] = field(default_factory=list)

    publish_result: Optional[dict] = None
    error: Optional[str] = None
    cost_report: dict = field(default_factory=dict)

    abort_event: threading.Event = field(default_factory=threading.Event)
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def set_state(self, s: str, msg: Optional[str] = None) -> None:
        with self._lock:
            self.state = s
            self.last_state_change = time.time()
            stamp = time.strftime("%H:%M:%S")
            line = f"[{stamp}] {s}" + (f" — {msg}" if msg else "")
            self.log.append(line)

    def request_abort(self, reason: str = "user requested") -> None:
        """사용자가 중단 요청. 실행 중인 노드가 다음 체크포인트에서 RuntimeError 던짐."""
        self.abort_event.set()
        self.error = f"abort: {reason}"
        self.set_state(State.ABORTED, reason)

    def check_abort(self) -> None:
        """노드 진입 시 호출. abort 요청됐으면 즉시 RuntimeError."""
        if self.abort_event.is_set():
            raise RuntimeError("session aborted")


class SessionManager:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, **kwargs) -> Session:
        sid = uuid.uuid4().hex[:12]
        s = Session(id=sid, **kwargs)
        with self._lock:
            self._sessions[sid] = s
        return s

    def get(self, sid: str) -> Optional[Session]:
        return self._sessions.get(sid)


_MGR = SessionManager()


def manager() -> SessionManager:
    return _MGR
