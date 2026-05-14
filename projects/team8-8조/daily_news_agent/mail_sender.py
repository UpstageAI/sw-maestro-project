from __future__ import annotations

from dataclasses import dataclass
from email.message import EmailMessage
import smtplib

from daily_news_agent.models import BriefingResult


class MailDeliveryError(RuntimeError):
    """Raised when an email could not be delivered."""


@dataclass(frozen=True)
class EmailMessagePayload:
    subject: str
    plain_text: str
    sender: str
    recipients: list[str]
    html_text: str | None = None


class MailClient:
    def send(self, payload: EmailMessagePayload) -> str | None:
        raise NotImplementedError


def build_email_message(payload: EmailMessagePayload) -> EmailMessage:
    if not payload.sender.strip():
        raise ValueError("발신자 이메일 주소가 비어 있습니다.")
    recipients = [recipient.strip() for recipient in payload.recipients if recipient.strip()]
    if not recipients:
        raise ValueError("수신자 이메일 주소가 비어 있습니다.")

    message = EmailMessage()
    message["Subject"] = payload.subject.strip() or "Daily News Briefing"
    message["From"] = payload.sender.strip()
    message["To"] = ", ".join(recipients)
    message.set_content(payload.plain_text or "")
    if payload.html_text:
        message.add_alternative(payload.html_text, subtype="html")
    return message


def build_briefing_email_payload(
    briefing_result: BriefingResult,
    sender: str,
    recipient: str,
) -> EmailMessagePayload:
    article_lines = []
    for article in briefing_result.selected_articles:
        tag_str = ", ".join(f"#{t}" for t in article.tags) if article.tags else ""
        lines = [
            f"- 제목: {article.title}",
            f"  출처: {article.source}",
            f"  발행일: {article.published_at or '정보 없음'}",
        ]
        if tag_str:
            lines.append(f"  태그: {tag_str}")
        lines.append(f"  링크: {article.link}")
        article_lines.append("\n".join(lines))

    sections = [briefing_result.briefing_markdown.strip()]
    if article_lines:
        sections.append("선정 기사 링크\n" + "\n\n".join(article_lines))
    if briefing_result.errors:
        sections.append("수집 중 오류\n" + "\n".join(f"- {error}" for error in briefing_result.errors))

    plain_text = "\n\n".join(section for section in sections if section).strip()
    html_text = _build_briefing_html(briefing_result)

    return EmailMessagePayload(
        subject=f"Daily News Agent 브리핑 - {briefing_result.interest}",
        plain_text=plain_text,
        html_text=html_text,
        sender=sender,
        recipients=[recipient],
    )


def _markdown_to_html(text: str) -> str:
    import re
    lines = text.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        # h2
        if line.startswith("## "):
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = _inline_markdown(line[3:])
            html_lines.append(f'<h2 style="font-size:16px;font-weight:700;color:#1e293b;margin:24px 0 8px;">{content}</h2>')
        # list item
        elif line.startswith("- "):
            if not in_list:
                html_lines.append('<ul style="margin:0 0 8px;padding-left:20px;">')
                in_list = True
            content = _inline_markdown(line[2:])
            html_lines.append(f'<li style="color:#475569;font-size:14px;line-height:1.7;margin-bottom:4px;">{content}</li>')
        # blank line
        elif line.strip() == "":
            if in_list:
                html_lines.append("</ul>")
                in_list = False
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            content = _inline_markdown(line)
            html_lines.append(f'<p style="color:#475569;font-size:14px;line-height:1.7;margin:0 0 8px;">{content}</p>')

    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


def _inline_markdown(text: str) -> str:
    import re
    # [text](url)
    text = re.sub(
        r'\[([^\]]+)\]\((https?://[^\)]+)\)',
        r'<a href="\2" style="color:#4f46e5;text-decoration:none;font-weight:500;">\1</a>',
        text,
    )
    # **bold**
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    return text


def _build_briefing_html(briefing_result: BriefingResult) -> str:
    import html as html_mod
    from datetime import date

    briefing_html = _markdown_to_html(briefing_result.briefing_markdown)
    today = date.today().strftime("%Y년 %m월 %d일")

    article_cards = ""
    for article in briefing_result.selected_articles:
        title = html_mod.escape(article.title)
        source = html_mod.escape(article.source)
        published = html_mod.escape(article.published_at or "")
        link = html_mod.escape(article.link)
        tags_html = "".join(
            f'<span style="display:inline-block;background:#eef2ff;color:#4f46e5;font-size:11px;'
            f'padding:2px 8px;border-radius:20px;margin:2px 2px 0 0;font-weight:500;">#{html_mod.escape(t)}</span>'
            for t in article.tags
        )
        article_cards += f"""
        <div style="background:#f8fafc;border-radius:12px;padding:16px;margin-bottom:12px;">
          <div style="font-size:14px;font-weight:700;color:#1e293b;margin-bottom:6px;line-height:1.4;">{title}</div>
          <div style="font-size:12px;color:#94a3b8;margin-bottom:8px;">{source}{' · ' + published if published else ''}</div>
          {('<div style="margin-bottom:10px;">' + tags_html + '</div>') if tags_html else ''}
          <a href="{link}" style="display:inline-block;background:#4f46e5;color:#fff;font-size:12px;font-weight:600;
             padding:6px 14px;border-radius:8px;text-decoration:none;">원문 보기 →</a>
        </div>"""

    errors_html = ""
    if briefing_result.errors:
        error_items = "".join(f"<li>{html_mod.escape(e)}</li>" for e in briefing_result.errors)
        errors_html = f"""
        <div style="background:#fffbeb;border:1px solid #fde68a;border-radius:10px;padding:14px;margin-top:16px;">
          <p style="font-size:13px;font-weight:600;color:#92400e;margin:0 0 6px;">수집 중 오류</p>
          <ul style="margin:0;padding-left:18px;color:#92400e;font-size:13px;">{error_items}</ul>
        </div>"""

    interest = html_mod.escape(briefing_result.interest)

    return f"""<!DOCTYPE html>
<html lang="ko">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f1f5f9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:32px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

        <!-- Header -->
        <tr><td style="background:#0f172a;border-radius:16px 16px 0 0;padding:28px 32px;">
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td>
                <div style="display:inline-flex;align-items:center;gap:10px;">
                  <div style="width:36px;height:36px;background:#4f46e5;border-radius:10px;display:inline-block;
                    text-align:center;line-height:36px;font-size:18px;">📰</div>
                  <span style="color:#fff;font-size:18px;font-weight:700;vertical-align:middle;margin-left:10px;">Daily News Agent</span>
                </div>
                <p style="color:#94a3b8;font-size:13px;margin:6px 0 0;">{today} · {interest}</p>
              </td>
            </tr>
          </table>
        </td></tr>

        <!-- Briefing Body -->
        <tr><td style="background:#fff;padding:28px 32px;">
          {briefing_html}
        </td></tr>

        <!-- Article Cards -->
        <tr><td style="background:#fff;padding:0 32px 28px;">
          <h2 style="font-size:15px;font-weight:700;color:#1e293b;margin:0 0 14px;padding-top:8px;
            border-top:1px solid #f1f5f9;">선별된 기사 {len(briefing_result.selected_articles)}개</h2>
          {article_cards}
          {errors_html}
        </td></tr>

        <!-- Footer -->
        <tr><td style="background:#f8fafc;border-radius:0 0 16px 16px;padding:20px 32px;text-align:center;
          border-top:1px solid #e2e8f0;">
          <p style="color:#94a3b8;font-size:12px;margin:0;">Daily News Agent · AI 기반 맞춤형 뉴스 브리핑</p>
        </td></tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


class SMTPMailClient(MailClient):
    def __init__(
        self,
        host: str,
        port: int,
        username: str = "",
        password: str = "",
        use_tls: bool = True,
        use_ssl: bool = False,
        timeout_seconds: int = 10,
    ) -> None:
        self.host = host.strip()
        self.port = port
        self.username = username
        self.password = password
        self.use_tls = use_tls
        self.use_ssl = use_ssl
        self.timeout_seconds = timeout_seconds

    def send(self, payload: EmailMessagePayload) -> None:
        if not self.host:
            raise ValueError("SMTP 호스트가 비어 있습니다.")

        message = build_email_message(payload)
        smtp_factory = smtplib.SMTP_SSL if self.use_ssl else smtplib.SMTP

        try:
            with smtp_factory(self.host, self.port, timeout=self.timeout_seconds) as client:
                if self.use_tls and not self.use_ssl:
                    client.starttls()
                if self.username:
                    client.login(self.username, self.password)
                client.send_message(message)
        except (OSError, smtplib.SMTPException) as exc:
            raise MailDeliveryError(f"메일 전송에 실패했습니다: {exc}") from exc
