"""Discord DM 리마인더 알림 봇"""

import argparse
import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

import discord
from gtts import gTTS

from db import get_unsent_reminders, init_db, mark_as_sent


ENV_PATH = Path(".env")
TTS_DIR = Path("tts")
CHECK_INTERVAL_SECONDS = 60
TEST_MESSAGE = "Discord DM 테스트 메시지입니다."


@dataclass(frozen=True)
class BotConfig:
    token: str
    user_id: int


def load_dotenv(path: Path = ENV_PATH):
    """간단한 KEY=VALUE 형식의 .env 파일을 환경변수로 로드"""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")

        if key.startswith("export "):
            key = key.removeprefix("export ").strip()

        os.environ.setdefault(key, value)


def load_config() -> BotConfig:
    """환경 설정을 읽고 Discord 봇 설정을 반환"""
    token = os.environ.get("DISCORD_BOT_TOKEN")
    user_id = os.environ.get("DISCORD_USER_ID")

    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN 환경변수가 필요합니다.")
    if not user_id:
        raise RuntimeError("DISCORD_USER_ID 환경변수가 필요합니다.")

    try:
        parsed_user_id = int(user_id)
    except ValueError as exc:
        raise RuntimeError("DISCORD_USER_ID는 숫자여야 합니다.") from exc

    return BotConfig(token=token, user_id=parsed_user_id)


def build_message(reminder: dict) -> str:
    """Discord DM으로 보낼 리마인더 메시지 생성"""
    return (
        f"리마인더: {reminder['message']}\n"
        f"일정: {reminder['event_title']}\n"
        f"알림 시각: {reminder['remind_at']}"
    )


def text_to_speech(message: str, file_name: str) -> Path:
    """메시지를 mp3 음성 파일로 변환하고 파일 경로 반환"""
    TTS_DIR.mkdir(exist_ok=True)
    file_path = TTS_DIR / file_name

    tts = gTTS(text=message, lang="ko", slow=False)
    tts.save(file_path)

    return file_path


async def create_tts_file(message: str, file_name: str) -> Path:
    """gTTS 파일 생성을 이벤트 루프 밖에서 실행"""
    return await asyncio.to_thread(text_to_speech, message, file_name)


class ReminderBot(discord.Client):
    def __init__(self, config: BotConfig, test_mode: bool):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        self.config = config
        self.test_mode = test_mode
        self.reminder_task: asyncio.Task | None = None

    async def on_ready(self):
        print(f"Logged in as {self.user}")

        if self.test_mode:
            await self.send_test_dm()
            await self.close()
            return

        if self.reminder_task is None or self.reminder_task.done():
            self.reminder_task = asyncio.create_task(self.run_reminder_loop())

    async def fetch_target_user(self) -> discord.User:
        user = self.get_user(self.config.user_id)
        if user is None:
            user = await self.fetch_user(self.config.user_id)
        return user

    async def send_dm_with_tts(
        self,
        user: discord.User,
        message: str,
        file_name: str,
        audio_label: str,
    ):
        audio_path = await create_tts_file(message, file_name)

        await user.send(message)
        await user.send(
            content=audio_label,
            file=discord.File(audio_path, filename=audio_path.name),
        )

    async def send_test_dm(self):
        try:
            user = await self.fetch_target_user()
            await self.send_dm_with_tts(
                user,
                TEST_MESSAGE,
                "test_dm.mp3",
                "음성 알림 테스트",
            )
            print(f"DM 전송 완료: {user} ({self.config.user_id})")
        except discord.Forbidden as exc:
            print(f"DM 전송 실패: {exc}")
            print("봇과 사용자가 함께 들어가 있는 서버가 없거나, 사용자의 DM 설정이 막혀 있습니다.")

    async def run_reminder_loop(self):
        while not self.is_closed():
            try:
                await self.check_and_send_reminders()
            except Exception as exc:
                print(f"리마인더 확인 실패: {exc}")

            await asyncio.sleep(CHECK_INTERVAL_SECONDS)

    async def check_and_send_reminders(self):
        user = await self.fetch_target_user()

        for reminder in get_unsent_reminders():
            try:
                await self.send_reminder(user, reminder)
            except Exception as exc:
                print(f"리마인더 전송 실패 id={reminder.get('id')}: {exc}")

    async def send_reminder(self, user: discord.User, reminder: dict):
        message = build_message(reminder)
        await self.send_dm_with_tts(
            user,
            message,
            f"reminder_{reminder['id']}.mp3",
            "음성 알림",
        )
        mark_as_sent(reminder["id"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Discord 리마인더 DM 봇")
    parser.add_argument(
        "--test-dm",
        action="store_true",
        help="리마인더 루프 없이 DM 테스트 메시지만 전송하고 종료합니다.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    load_dotenv()
    config = load_config()

    init_db()
    bot = ReminderBot(config=config, test_mode=args.test_dm)
    bot.run(config.token)


if __name__ == "__main__":
    main()
