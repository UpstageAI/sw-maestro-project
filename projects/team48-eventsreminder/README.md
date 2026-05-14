# AI 캘린더 리마인더 서비스

일정을 등록하면 AI가 종류를 자동 분류하고, 적절한 타이밍에 리마인더를 보내주는 캘린더 서비스

## 기술 스택

- Frontend: Streamlit (streamlit-calendar)
- LLM: Solar API
- DB: SQLite
- 알림: Discord Bot + TTS

## 프로젝트 구조

```
db.py              # 공용 — SQLite CRUD 함수
pipeline.py        # 공용 — 전체 흐름 연결 (fetch → 분류 → 리마인더 → 저장)
calendar_sync.py   # 구글캘린더 iCal 연동
classifier.py      # LLM 일정 분류
reminder.py        # 카테고리별 리마인더 생성 규칙
app.py             # Streamlit 캘린더 UI
discord_bot.py     # 디스코드 알림 발송 + TTS + 스케줄러
```

## 파이프라인

1. Google Calendar에서 iCal URL로 일정 가져오기
2. Solar API로 일정 종류 분류 (면접, 시험, 약속, 마감, 기타)
3. 카테고리에 따라 리마인더 자동 생성
4. SQLite에 저장
5. Streamlit에서 캘린더 UI 표시 + 리마인더 수정
6. 스케줄러가 알림 시점 체크
7. Discord로 알림 발송 + TTS

## 설치

```bash
pip install -r requirements.txt
```

## 실행

DB 초기화:
```bash
python db.py
```

파이프라인 실행:
```bash
python pipeline.py <iCal URL>
```

Streamlit 앱 실행:
```bash
streamlit run app.py
```
