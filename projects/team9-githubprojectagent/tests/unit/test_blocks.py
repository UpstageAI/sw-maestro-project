"""_blocks.py Notion 블록 변환 함수 단위 테스트."""
import pytest
from src.templates._blocks import (
    _rt, para, heading, bullet, code, divider, quote, callout,
    toggle, table_row, table, md_to_blocks,
)


class TestRichText:
    def test_plain_text(self):
        rt = _rt("hello")
        assert len(rt) == 1
        assert rt[0]["text"]["content"] == "hello"

    def test_bold_text(self):
        rt = _rt("**굵은 글씨**")
        bold_parts = [p for p in rt if p.get("annotations", {}).get("bold")]
        assert len(bold_parts) == 1
        assert bold_parts[0]["text"]["content"] == "굵은 글씨"

    def test_italic_text(self):
        rt = _rt("*기울임*")
        italic_parts = [p for p in rt if p.get("annotations", {}).get("italic")]
        assert len(italic_parts) == 1

    def test_code_inline(self):
        rt = _rt("`코드`")
        code_parts = [p for p in rt if p.get("annotations", {}).get("code")]
        assert len(code_parts) == 1
        assert code_parts[0]["text"]["content"] == "코드"

    def test_mixed_inline(self):
        rt = _rt("앞 **bold** 뒤")
        assert len(rt) == 3  # 앞, bold, 뒤

    def test_empty_string(self):
        rt = _rt("")
        assert len(rt) == 1
        assert rt[0]["text"]["content"] == ""

    def test_no_inline_markers(self):
        rt = _rt("일반 텍스트입니다")
        assert len(rt) == 1

    def test_multiple_bold(self):
        rt = _rt("**a** **b**")
        bold_parts = [p for p in rt if p.get("annotations", {}).get("bold")]
        assert len(bold_parts) == 2


class TestBlockFunctions:
    def test_para_type(self):
        b = para("텍스트")
        assert b["type"] == "paragraph"
        assert b["object"] == "block"
        assert "rich_text" in b["paragraph"]

    def test_heading_level_1(self):
        b = heading(1, "제목1")
        assert b["type"] == "heading_1"

    def test_heading_level_2(self):
        b = heading(2, "제목2")
        assert b["type"] == "heading_2"

    def test_heading_level_3(self):
        b = heading(3, "제목3")
        assert b["type"] == "heading_3"

    def test_heading_clamps_to_min_1(self):
        b = heading(0, "제목")
        assert b["type"] == "heading_1"

    def test_heading_clamps_to_max_3(self):
        b = heading(5, "제목")
        assert b["type"] == "heading_3"

    def test_bullet_type(self):
        b = bullet("목록 항목")
        assert b["type"] == "bulleted_list_item"

    def test_code_block(self):
        b = code("print('hello')", "python")
        assert b["type"] == "code"
        assert b["code"]["language"] == "python"

    def test_code_block_default_lang(self):
        b = code("text")
        assert b["code"]["language"] == "plain text"

    def test_divider(self):
        b = divider()
        assert b["type"] == "divider"
        assert b["divider"] == {}

    def test_quote(self):
        b = quote("인용문")
        assert b["type"] == "quote"

    def test_callout(self):
        b = callout("⭐", "안내 메시지")
        assert b["type"] == "callout"
        assert b["callout"]["icon"]["emoji"] == "⭐"

    def test_toggle(self):
        children = [para("내용")]
        b = toggle("토글 제목", children)
        assert b["type"] == "toggle"
        assert b["toggle"]["children"] == children

    def test_table_row(self):
        b = table_row(["셀1", "셀2"])
        assert b["type"] == "table_row"
        assert len(b["table_row"]["cells"]) == 2

    def test_table(self):
        b = table([["헤더1", "헤더2"], ["값1", "값2"]])
        assert b["type"] == "table"
        assert b["table"]["table_width"] == 2
        assert b["table"]["has_column_header"] is True

    def test_table_pads_short_rows(self):
        b = table([["헤더1", "헤더2"], ["값1"]])  # 두 번째 행이 짧음
        assert b["table"]["table_width"] == 2

    def test_table_empty_rows(self):
        b = table([])
        assert b["table"]["table_width"] == 1  # max(default=1)


class TestMdToBlocks:
    def test_heading_h1(self):
        blocks = md_to_blocks("# 제목")
        assert len(blocks) == 1
        assert blocks[0]["type"] == "heading_1"

    def test_heading_h2(self):
        blocks = md_to_blocks("## 소제목")
        assert blocks[0]["type"] == "heading_2"

    def test_heading_h3(self):
        blocks = md_to_blocks("### 세부제목")
        assert blocks[0]["type"] == "heading_3"

    def test_bullet_list(self):
        blocks = md_to_blocks("- 항목1\n- 항목2")
        assert all(b["type"] == "bulleted_list_item" for b in blocks)
        assert len(blocks) == 2

    def test_asterisk_bullet(self):
        blocks = md_to_blocks("* 항목")
        assert blocks[0]["type"] == "bulleted_list_item"

    def test_code_block(self):
        md = "```python\nprint('hi')\n```"
        blocks = md_to_blocks(md)
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "python"

    def test_code_block_no_lang(self):
        md = "```\nsome code\n```"
        blocks = md_to_blocks(md)
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "plain text"

    def test_divider(self):
        blocks = md_to_blocks("---")
        assert blocks[0]["type"] == "divider"

    def test_long_divider(self):
        blocks = md_to_blocks("------")
        assert blocks[0]["type"] == "divider"

    def test_paragraph(self):
        blocks = md_to_blocks("일반 텍스트 문단입니다.")
        assert blocks[0]["type"] == "paragraph"

    def test_empty_lines_skipped(self):
        blocks = md_to_blocks("줄1\n\n줄2")
        assert len(blocks) == 2

    def test_mixed_content(self):
        md = "# 제목\n\n- 항목\n\n일반 텍스트\n\n---"
        blocks = md_to_blocks(md)
        types = [b["type"] for b in blocks]
        assert "heading_1" in types
        assert "bulleted_list_item" in types
        assert "paragraph" in types
        assert "divider" in types

    def test_mermaid_code_block(self):
        md = "```mermaid\ngraph TD\n  A-->B\n```"
        blocks = md_to_blocks(md)
        assert blocks[0]["type"] == "code"
        assert blocks[0]["code"]["language"] == "mermaid"

    def test_empty_string(self):
        assert md_to_blocks("") == []
