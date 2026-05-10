# Discord DM 알림 봇 설정 및 테스트

이 프로젝트의 Discord 알림은 서버 채널에 메시지를 보내지 않고, 지정한 사용자에게 DM을 보내는 방식으로 동작한다. 리마인더를 보낼 때는 텍스트 메시지와 TTS로 생성한 mp3 음성 파일을 함께 전송한다.

Discord 정책상 봇이 아무 사용자에게나 바로 DM을 보낼 수 없기 때문에, 봇과 사용자가 같은 서버에 있어야 한다. 가장 단순한 구성은 개인용 비공개 서버를 만들고 그 서버에 본인과 봇만 두는 방식이다.

## 1. Discord 봇 생성

1. Discord Developer Portal에 접속한다.
   - https://discord.com/developers/applications
2. `New Application`을 눌러 애플리케이션을 만든다.
3. 왼쪽 메뉴에서 `Bot`으로 이동한다.
4. Bot을 생성한다.
5. `Token`을 복사한다.

복사한 Bot Token은 `.env`의 `DISCORD_BOT_TOKEN`에 넣는다.

주의:
- Bot Token은 비밀번호처럼 취급한다.
- GitHub, README, 채팅 등에 올리지 않는다.
- 노출되면 Developer Portal에서 즉시 토큰을 재발급한다.

## 2. 개인 서버 만들기

1. Discord 앱 왼쪽 서버 목록에서 `+` 버튼을 누른다.
2. `Create My Own`을 선택한다.
3. `For me and my friends`를 선택한다.
4. 서버 이름을 정한다.
   - 예: `Personal Reminder`
5. 다른 사용자는 초대하지 않는다.

이 서버는 실제 알림 채널로 쓰는 것이 아니라, 봇과 사용자가 같은 서버에 있도록 만드는 용도다.

## 3. 봇을 서버에 초대

1. Discord Developer Portal에서 만든 Application을 연다.
2. 왼쪽 메뉴에서 `OAuth2`로 이동한다.
3. URL 생성 영역에서 `Scopes` 중 `bot`을 선택한다.
4. 설치 유형은 `Guild Install`을 사용한다.
5. `Bot Permissions`에서 최소 `Send Messages`를 선택한다.
6. 생성된 URL을 복사해서 브라우저에서 연다.
7. 방금 만든 개인 서버를 선택한다.
8. `Authorize`를 누른다.

필요한 설정:

```text
Install Type: Guild Install
Scopes: bot
Bot Permissions: Send Messages
```

`applications.commands`는 현재 코드에서 사용하지 않는다. slash command를 만들 때 필요한 scope이므로 지금은 선택하지 않아도 된다.

## 4. Discord 사용자 ID 확인

1. Discord 앱에서 왼쪽 아래 톱니바퀴를 누른다.
2. `Advanced` 또는 `고급` 메뉴로 이동한다.
3. `Developer Mode` 또는 `개발자 모드`를 켠다.
4. 내 프로필 또는 서버 멤버 목록에서 내 계정을 우클릭한다.
5. `Copy User ID`를 누른다.

복사되는 값은 보통 17자리 또는 18자리 숫자다.

## 5. .env 설정

프로젝트 루트에 `.env` 파일을 만들고 아래 값을 넣는다.

```env
DISCORD_BOT_TOKEN=봇_토큰
DISCORD_USER_ID=내_디스코드_사용자_ID
```

예:

```env
DISCORD_BOT_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
DISCORD_USER_ID=123456789012345678
```

`.env`는 이미 `.gitignore`에 포함되어 있으므로 Git에 올라가지 않는다.

## 6. 가상환경 구성

프로젝트 루트에서 실행한다.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

프롬프트 앞에 `(.venv)`가 보이면 가상환경이 활성화된 상태다.

## 7. TTS 동작 방식

`discord_bot.py`는 `gTTS`를 사용해서 리마인더 메시지를 한국어 mp3 파일로 생성한다.

동작 흐름:

```text
리마인더 조회
→ DM 텍스트 메시지 전송
→ 같은 메시지로 mp3 생성
→ DM에 mp3 파일 첨부 전송
→ 전송 성공 시 is_sent = 1 처리
```

생성된 음성 파일은 `tts/` 폴더에 저장된다.

```text
tts/test_dm.mp3
tts/reminder_1.mp3
tts/reminder_2.mp3
```

`gTTS`는 mp3 생성 시 네트워크를 사용한다. 인터넷 연결이 없거나 Google TTS 요청이 실패하면 음성 파일 생성 단계에서 실패하고, 해당 리마인더는 발송 완료 처리되지 않는다.

## 8. DM + TTS 전송 테스트

리마인더 DB와 무관하게 DM과 TTS 첨부 전송만 확인하려면 아래 명령을 실행한다.

```bash
python3 discord_bot.py --test-dm
```

성공하면 콘솔에 다음과 비슷하게 출력된다.

```text
Logged in as Alram_Bot#2556
DM 전송 완료: username (123456789012345678)
```

Discord DM으로 아래 메시지가 와야 한다.
DM에는 텍스트 메시지와 `test_dm.mp3` 음성 파일이 함께 와야 한다.

```text
Discord DM 테스트 메시지입니다.
```

## 9. 리마인더 봇 실행

DM과 TTS 테스트가 성공하면 실제 리마인더 봇을 실행한다.

```bash
python3 discord_bot.py
```

봇은 1분마다 SQLite DB에서 발송 대상 리마인더를 조회한다.

대상 조건:

```text
is_sent = 0
remind_at <= 현재 시각
```

전송에 성공하면 해당 리마인더의 `is_sent`를 `1`로 변경한다.

## 10. 테스트용 리마인더 넣기

DB를 초기화한다.

```bash
python3 db.py
```

테스트 데이터를 넣는다.

```bash
sqlite3 calendar.db
```

SQLite 프롬프트에서 실행한다.

```sql
INSERT INTO events (
  id, title, description, start_time, end_time, category, synced_at
) VALUES (
  'test-event-1',
  'DM 알림 테스트',
  '테스트 설명',
  datetime('now'),
  NULL,
  '기타',
  datetime('now')
);

INSERT INTO reminders (
  event_id, remind_at, message, is_sent, created_by
) VALUES (
  'test-event-1',
  datetime('now'),
  'DM 테스트 알림입니다',
  0,
  'user'
);

.exit
```

그 다음 봇을 실행한다.

```bash
python3 discord_bot.py
```

최대 1분 안에 DM이 와야 한다.
DM에는 텍스트 리마인더와 `reminder_{id}.mp3` 음성 파일이 함께 첨부된다.

발송 완료 여부는 아래 명령으로 확인한다.

```bash
sqlite3 calendar.db "SELECT id, message, is_sent FROM reminders;"
```

`is_sent`가 `1`이면 정상적으로 발송 완료 처리된 것이다.

## 11. 자주 나는 오류

### ModuleNotFoundError: No module named 'discord'

가상환경을 활성화하고 의존성을 설치한다.

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

### DISCORD_BOT_TOKEN 환경변수가 필요합니다.

`.env`에 `DISCORD_BOT_TOKEN`이 있는지 확인한다.

```env
DISCORD_BOT_TOKEN=봇_토큰
```

### DISCORD_USER_ID 환경변수가 필요합니다.

`.env`에 `DISCORD_USER_ID`가 있는지 확인한다.

```env
DISCORD_USER_ID=내_디스코드_사용자_ID
```

### 403 Forbidden: Cannot send messages to this user due to having no mutual guilds

봇과 사용자가 같은 서버에 없다는 뜻이다.

해결:
1. 개인 서버를 만든다.
2. 봇을 그 서버에 초대한다.
3. 본인 계정도 같은 서버에 있는지 확인한다.
4. 다시 테스트한다.

```bash
python3 discord_bot.py --test-dm
```

### 같은 서버인데도 DM이 오지 않음

Discord 개인정보 설정에서 서버 멤버의 DM 허용이 꺼져 있을 수 있다.

Discord 설정에서 `Privacy & Safety` 관련 DM 허용 설정을 확인한다.

### gTTSError 또는 TTS 생성 실패

`gTTS`는 음성 파일 생성 시 인터넷 연결이 필요하다.

확인할 것:
- 가상환경에 `gtts`가 설치되어 있는지 확인한다.
- 인터넷 연결을 확인한다.
- 잠시 후 다시 실행한다.

```bash
pip install -r requirements.txt
python3 discord_bot.py --test-dm
```

### DM 텍스트는 왔는데 mp3 파일이 오지 않음

현재 코드는 텍스트와 mp3 전송을 같은 발송 흐름에서 처리한다. mp3 전송 전에 오류가 나면 콘솔에 실패 로그가 출력된다.

확인할 것:
- `tts/` 폴더에 mp3 파일이 생성됐는지 확인한다.
- Discord에서 파일 첨부가 차단되지 않았는지 확인한다.
- 콘솔의 오류 메시지를 확인한다.

## 12. 종료

가상환경을 종료하려면 아래 명령을 실행한다.

```bash
deactivate
```
