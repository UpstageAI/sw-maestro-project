"""PDF 발행 — 선택된 템플릿의 preview_md → HTML → PDF.

흐름:
  1. template.preview_md(story, ctx) 로 마크다운 얻기
  2. ```mermaid 블록은 Kroki API로 PNG 변환 → base64 data URI 임베드
     (실패 시 일반 코드블록으로 폴백 — PDF는 그래도 만들어짐)
  3. markdown 라이브러리로 HTML 변환 + 인라인 CSS
  4. xhtml2pdf의 pisa.CreatePDF로 PDF 파일 생성
  5. output/ 디렉토리에 저장 → 경로 반환

한글 폰트:
  Windows = Malgun Gothic, macOS = Apple SD Gothic Neo, Linux = NanumGothic
  자동 감지·등록. 못 찾으면 Helvetica fallback (한글이 박스로 나올 수 있음).
"""
import base64
import io
import logging
import os
import platform
import re
import tempfile
import zlib
from datetime import datetime
from pathlib import Path
from typing import Optional

import markdown as md_lib
import requests
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa
from xhtml2pdf.default import DEFAULT_FONT as _XHTML2PDF_DEFAULT_FONT

from src import config
from src.models.repo import RepoContext
from src.models.story import StoryDraft
from src.models.template import NotionTemplate

log = logging.getLogger(__name__)

KROKI_BASE = os.environ.get("KROKI_URL", "https://kroki.io")
# 로컬 Kroki(docker compose)면 ~100ms, 공개 인스턴스는 콜드 스타트로 늦음.
KROKI_TIMEOUT = int(os.environ.get("KROKI_TIMEOUT", "30"))

# OS별 한글 폰트 후보
# reportlab은 .ttc (TrueType Collection) 못 읽음 ("postscript outlines not supported").
# 단일 .ttf 파일만 사용 가능. .ttc는 후보에서 제외.
_KOREAN_FONT_CANDIDATES = {
    "Windows": [
        ("KoreanFont", r"C:\Windows\Fonts\malgun.ttf"),
        ("KoreanFont", r"C:\Windows\Fonts\malgunbd.ttf"),
    ],
    "Darwin": [
        # macOS는 ttc만 있어서 까다로움 — Helvetica fallback
        ("KoreanFont", "/Library/Fonts/AppleGothic.ttf"),
    ],
    "Linux": [
        # 우선순위: NanumGothic (Dockerfile fonts-nanum) → 그 외
        ("KoreanFont", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"),
        ("KoreanFont", "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
        ("KoreanFont", "/usr/share/fonts/truetype/nanum/NanumBarunGothic.ttf"),
        # ttc는 reportlab 비호환이라 일부러 제외
    ],
}

_korean_font_registered: Optional[str] = None


def _register_korean_font() -> Optional[str]:
    """한 번만 등록 + bold variant + family. 등록된 폰트 이름 (없으면 None).

    xhtml2pdf가 한글을 렌더하려면:
      1. registerFont(TTFont(...)) — 기본 등록
      2. registerFontFamily(...) — bold/italic 매핑 (CSS의 <strong> 등 처리)
      3. CSS에서 해당 폰트 family를 모든 요소에 적용 (build_css에서 처리)
    """
    global _korean_font_registered
    if _korean_font_registered is not None:
        return _korean_font_registered or None

    candidates = _KOREAN_FONT_CANDIDATES.get(platform.system(), [])
    for name, path in candidates:
        if not os.path.exists(path):
            continue
        try:
            pdfmetrics.registerFont(TTFont(name, path))
        except Exception as e:
            log.warning("폰트 등록 실패 %s: %s", path, e)
            continue

        # bold variant 시도 — 같은 디렉토리의 *Bold.ttf
        bold_name = f"{name}-Bold"
        bold_paths = [
            path.replace("NanumGothic.ttf", "NanumGothicBold.ttf"),
            path.replace("malgun.ttf", "malgunbd.ttf"),
        ]
        registered_bold = False
        for bp in bold_paths:
            if os.path.exists(bp) and bp != path:
                try:
                    pdfmetrics.registerFont(TTFont(bold_name, bp))
                    registered_bold = True
                    break
                except Exception:
                    pass

        # FontFamily 등록 — <strong> 등 자동 매핑
        try:
            registerFontFamily(
                name,
                normal=name,
                bold=bold_name if registered_bold else name,
                italic=name,
                boldItalic=bold_name if registered_bold else name,
            )
        except Exception as e:
            log.warning("FontFamily 등록 실패: %s", e)

        _korean_font_registered = name
        # xhtml2pdf의 DEFAULT_FONT는 모든 generic 폰트(helvetica/sans-serif/...)를
        # Helvetica로 fallback. 그래서 CSS에 'KoreanFont' 적어도 한글이 ■■로 나옴.
        # 주요 키들을 우리 한글 폰트로 강제 매핑해서 모든 텍스트가 한글 폰트로 렌더되게 함.
        for key in ("helvetica", "arial", "tahoma", "verdana", "sans-serif",
                    "times", "times new roman", "serif",
                    "korean", "koreanfont", name.lower()):
            _XHTML2PDF_DEFAULT_FONT[key] = name
        log.info("PDF 한글 폰트 등록: %s (bold=%s) + xhtml2pdf 매핑 강제",
                 name, "yes" if registered_bold else "no")
        return name

    _korean_font_registered = ""
    log.warning("한글 폰트 못 찾음 — PDF 한글이 깨질 수 있습니다.")
    return None


def _build_css(font_name: Optional[str]) -> str:
    """xhtml2pdf용 CSS. 모든 텍스트 요소에 한글 폰트 명시적용 (* 셀렉터로는 부족함)."""
    if font_name:
        # 모든 텍스트 element에 한글 폰트 강제. xhtml2pdf는 기본 Helvetica로 빠지면 한글 ■■.
        body_font = f"'{font_name}', Helvetica, sans-serif"
    else:
        body_font = "Helvetica, sans-serif"

    return f"""
@page {{ size: A4; margin: 1.8cm 2cm; }}
body, p, h1, h2, h3, h4, h5, h6, li, td, th, blockquote, em, strong, span, div {{
    font-family: {body_font};
}}
body {{ font-size: 10.5pt; line-height: 1.6; color: #1f1f1c; }}
h1 {{ font-size: 22pt; border-bottom: 1px solid #c96442; padding-bottom: 5pt; color: #1f1f1c; margin-top: 0; }}
h2 {{ font-size: 16pt; margin-top: 16pt; color: #1f1f1c; }}
h3 {{ font-size: 12.5pt; color: #6b6963; }}
p {{ margin: 5pt 0; }}
ul, ol {{ margin: 5pt 0; padding-left: 22pt; }}
li {{ margin: 2pt 0; }}
strong {{ color: #1f1f1c; }}
em {{ color: #6b6963; }}
code {{ font-family: Courier, monospace; background: #faf9f7; padding: 1pt 4pt; font-size: 9.5pt; }}
pre {{ background: #faf9f7; border: 1px solid #e8e6e1; padding: 8pt 10pt; font-family: Courier, monospace; font-size: 9pt; }}
hr {{ border: 0; border-top: 1px solid #e8e6e1; margin: 12pt 0; }}
blockquote {{ border-left: 3pt solid #c96442; padding-left: 8pt; color: #6b6963; margin: 6pt 0; }}
table {{ border-collapse: collapse; margin: 6pt 0; width: 100%; }}
th, td {{ border: 1px solid #e8e6e1; padding: 4pt 6pt; text-align: left; vertical-align: top; }}
th {{ background: #faf9f7; font-weight: bold; }}
.diagram {{ text-align: center; margin: 10pt 0; padding: 6pt; background: #fafafa; border: 1px solid #e8e6e1; }}
.diagram img {{ max-width: 100%; }}
.meta {{ color: #8e8c85; font-size: 9pt; }}
"""


# ============================================================
# Mermaid → Kroki PNG
# ============================================================

def _mermaid_kroki_png_bytes(mermaid_text: str) -> Optional[bytes]:
    """Kroki API로 Mermaid → PNG (bytes). POST 방식. 실패 시 None."""
    try:
        url = f"{KROKI_BASE}/mermaid/png"
        r = requests.post(
            url,
            data=mermaid_text.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
            timeout=KROKI_TIMEOUT,
        )
        if r.status_code == 200 and r.headers.get("content-type", "").startswith("image/"):
            return r.content
        log.warning("Kroki POST %d %s err=%s",
                    r.status_code, r.headers.get("content-type"), r.text[:200])
    except Exception as e:
        log.warning("Kroki 호출 실패: %s", e)
    return None


# 호환용 (다른 모듈이 참조 가능) — bytes를 base64 data URI로 래핑
def _mermaid_kroki_png_b64(mermaid_text: str) -> Optional[str]:
    b = _mermaid_kroki_png_bytes(mermaid_text)
    return f"data:image/png;base64,{base64.b64encode(b).decode()}" if b else None


MERMAID_BLOCK_RE = re.compile(r"```mermaid\s*\n([\s\S]+?)\n```", re.MULTILINE)


def _replace_mermaid_with_images(markdown_text: str, tmpdir: str) -> str:
    """```mermaid ... ``` 블록을 <img src=tmpfile.png> 로 치환.

    xhtml2pdf는 data: URI를 PDF에 임베드 못 하므로 PNG를 임시 파일로 저장 후
    절대경로를 src로 사용. tmpdir 안의 파일들은 호출자가 정리(자동 cleanup)."""
    def repl(m: re.Match) -> str:
        mer = m.group(1).strip()
        png = _mermaid_kroki_png_bytes(mer)
        if png:
            f = tempfile.NamedTemporaryFile(
                prefix="mmd_", suffix=".png", dir=tmpdir, delete=False,
            )
            f.write(png)
            f.close()
            return f'\n<div class="diagram"><img src="{f.name}" alt="diagram" /></div>\n'
        # 폴백 — 일반 코드블록
        return f"```\n{mer}\n```"
    return MERMAID_BLOCK_RE.sub(repl, markdown_text)


# ============================================================
# 메인 진입점
# ============================================================

def render_pdf(
    story: StoryDraft,
    ctx: RepoContext,
    template: NotionTemplate,
    out_dir: Optional[Path] = None,
) -> Path:
    """선택된 템플릿으로 PDF 생성, 저장된 파일 경로 반환."""
    out_dir = out_dir or config.OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    font_name = _register_korean_font()

    md_text = (
        template.preview_md(story, ctx)
        if template.preview_md
        else (story.merged or "")
    )
    if not md_text.strip():
        raise RuntimeError("렌더할 내용이 비어있음 (template.preview_md / story.merged 둘 다 없음)")

    # Mermaid PNG는 임시 파일로 저장 — PDF 생성 후 자동 정리
    with tempfile.TemporaryDirectory(prefix="mmd_pdf_") as tmpdir:
        md_text = _replace_mermaid_with_images(md_text, tmpdir)

        html_body = md_lib.markdown(
            md_text,
            extensions=["fenced_code", "tables", "nl2br", "sane_lists"],
        )
        css = _build_css(font_name)
        full_html = (
            f'<!DOCTYPE html><html><head><meta charset="utf-8">'
            f"<style>{css}</style></head><body>{html_body}</body></html>"
        )

        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out_path = out_dir / f"{ctx.owner}_{ctx.name}_{template.id}_{ts}.pdf"

        # link_callback: xhtml2pdf의 default callback이 절대 경로 file을 못 찾을 수 있어
        # 명시적으로 그대로 반환. <img src="/tmp/..."> 가 PDF에 임베드되도록.
        def _link_cb(uri: str, _rel: str) -> str:
            if uri.startswith(("/", "file://")):
                return uri
            return uri

        with out_path.open("wb") as f:
            result = pisa.CreatePDF(
                io.StringIO(full_html),
                dest=f,
                encoding="utf-8",
                link_callback=_link_cb,
            )
        if result.err:
            raise RuntimeError(f"PDF 생성 실패: err count={result.err}")

    log.info("PDF 저장: %s", out_path)
    return out_path
