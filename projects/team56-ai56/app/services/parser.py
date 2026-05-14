from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from app.core.models import CandidateProfile, ResumeEducation, ResumeExperience, ResumeProject


URL_RE = re.compile(r"https?://[^\s)]+")
EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\b(?:01[0-9]|0[2-6][0-9]?)-?\d{3,4}-?\d{4}\b")
SECTION_RE = re.compile(r"(?im)^(experience|education|skills|projects|경력|학력|기술|프로젝트)\b")
SECTION_ALIASES = {
    "experience": "experience",
    "경력": "experience",
    "education": "education",
    "학력": "education",
    "skills": "skills",
    "기술": "skills",
    "projects": "projects",
    "project": "projects",
    "프로젝트": "projects",
    "한 줄 소개": "summary",
    "강점": "strengths",
    "지원 동기": "motivation",
    "보완점": "gaps",
    "아쉬운 점": "gaps",
    "협업": "collaboration",
}
SKILL_KEYWORDS = [
    "python",
    "sql",
    "fastapi",
    "streamlit",
    "langgraph",
    "react",
    "node",
    "docker",
    "aws",
    "kubernetes",
    "graphql",
    "django",
]


@dataclass
class ParsedResume:
    raw_text: str
    extracted_urls: list[str]
    github_url: str | None
    profile: CandidateProfile


class ResumeParser:
    def parse_text(self, text: str) -> ParsedResume:
        cleaned = text.strip()
        urls = URL_RE.findall(cleaned)
        github_url = next((url for url in urls if "github.com" in url.lower()), None)
        profile = self._build_profile(cleaned, urls)
        return ParsedResume(raw_text=cleaned, extracted_urls=urls, github_url=github_url, profile=profile)

    def parse_file(self, file_path: Path) -> ParsedResume:
        suffix = file_path.suffix.lower()
        if suffix in {".txt", ".md"}:
            text = file_path.read_text(encoding="utf-8")
        elif suffix == ".pdf":
            text = self._extract_pdf_text(file_path)
        elif suffix == ".docx":
            text = self._extract_docx_text(file_path)
        else:
            text = self._extract_with_textutil(file_path)
        return self.parse_text(text)

    def _extract_pdf_text(self, file_path: Path) -> str:
        from pypdf import PdfReader

        reader = PdfReader(str(file_path))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()

    def _extract_docx_text(self, file_path: Path) -> str:
        from docx import Document

        document = Document(str(file_path))
        return "\n".join(paragraph.text for paragraph in document.paragraphs).strip()

    def _extract_with_textutil(self, file_path: Path) -> str:
        result = subprocess.run(
            ["/usr/bin/textutil", "-convert", "txt", "-stdout", str(file_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()

    def _build_profile(self, text: str, urls: list[str]) -> CandidateProfile:
        non_empty_lines = [line.strip() for line in text.splitlines() if line.strip()]
        lowered = text.lower()
        skills = [skill for skill in SKILL_KEYWORDS if skill in lowered]
        section_hints = [match.group(1) for match in SECTION_RE.finditer(text)]
        section_summaries = self._extract_section_summaries(text)
        structured_projects = self._build_structured_projects(section_summaries, skills)
        structured_experience = self._build_structured_experience(section_summaries)
        structured_education = self._build_structured_education(section_summaries)
        return CandidateProfile(
            headline=non_empty_lines[0] if non_empty_lines else None,
            emails=list(dict.fromkeys(EMAIL_RE.findall(text))),
            phones=list(dict.fromkeys(PHONE_RE.findall(text))),
            urls=urls,
            skills=skills,
            section_hints=section_hints,
            section_summaries=section_summaries,
            projects=section_summaries.get("projects", []),
            experience_items=section_summaries.get("experience", []),
            education_items=section_summaries.get("education", []),
            structured_projects=structured_projects,
            structured_experience=structured_experience,
            structured_education=structured_education,
        )

    def _extract_section_summaries(self, text: str) -> dict[str, list[str]]:
        lines = [line.strip() for line in text.splitlines()]
        sections: dict[str, list[str]] = {}
        current_section: str | None = None

        for raw_line in lines:
            line = raw_line.strip()
            if not line:
                continue

            normalized_header = self._normalize_section_header(line)
            if normalized_header:
                current_section = normalized_header
                sections.setdefault(current_section, [])
                continue

            if current_section:
                sections.setdefault(current_section, []).append(line)

        trimmed_sections: dict[str, list[str]] = {}
        for key, values in sections.items():
            trimmed = values[:8]
            if trimmed:
                trimmed_sections[key] = trimmed
        return trimmed_sections

    def _normalize_section_header(self, line: str) -> str | None:
        candidate = line.strip().strip("[]").rstrip(":").rstrip("]")
        lowered = candidate.lower()
        if lowered in SECTION_ALIASES:
            return SECTION_ALIASES[lowered]
        exact = SECTION_ALIASES.get(candidate)
        if exact:
            return exact
        for key, normalized in SECTION_ALIASES.items():
            if lowered.startswith(key.lower()):
                return normalized
            if candidate.startswith(key):
                return normalized
        return None

    def _build_structured_projects(
        self,
        section_summaries: dict[str, list[str]],
        global_skills: list[str],
    ) -> list[ResumeProject]:
        project_lines = section_summaries.get("projects", [])
        if not project_lines:
            return []

        projects: list[ResumeProject] = []
        current_name: str | None = None
        current_bullets: list[str] = []

        for line in project_lines:
            if "프로젝트명:" in line or line.lower().startswith("project name:"):
                if current_name or current_bullets:
                    projects.append(
                        ResumeProject(
                            name=current_name or "Project",
                            bullets=current_bullets,
                            skills=self._merge_skills(
                                global_skills,
                                self._extract_skills_from_lines([current_name or "", *current_bullets]),
                            ),
                        )
                    )
                current_name = line.split(":", 1)[1].strip() if ":" in line else line.strip()
                current_bullets = []
            elif line.startswith("-"):
                current_bullets.append(line.lstrip("-").strip())
            elif not current_name:
                current_name = line
            else:
                current_bullets.append(line)

        if current_name or current_bullets:
            projects.append(
                ResumeProject(
                    name=current_name or "Project",
                    bullets=current_bullets,
                    skills=self._merge_skills(
                        global_skills,
                        self._extract_skills_from_lines([current_name or "", *current_bullets]),
                    ),
                )
            )

        if not projects and project_lines:
            projects.append(
                ResumeProject(
                    name=project_lines[0],
                    bullets=project_lines[1:],
                    skills=self._merge_skills(global_skills, self._extract_skills_from_lines(project_lines)),
                )
            )
        return projects

    def _build_structured_experience(self, section_summaries: dict[str, list[str]]) -> list[ResumeExperience]:
        lines = section_summaries.get("experience", []) or section_summaries.get("collaboration", [])
        if not lines:
            return []
        return [ResumeExperience(title=lines[0], bullets=lines[1:4])]

    def _build_structured_education(self, section_summaries: dict[str, list[str]]) -> list[ResumeEducation]:
        lines = section_summaries.get("education", [])
        if not lines:
            return []
        return [ResumeEducation(title=lines[0], details=lines[1:4])]

    def _extract_skills_from_lines(self, lines: list[str]) -> list[str]:
        joined = " ".join(lines).lower()
        return [skill for skill in SKILL_KEYWORDS if skill in joined]

    def _merge_skills(self, global_skills: list[str], local_skills: list[str]) -> list[str]:
        merged: list[str] = []
        for skill in [*local_skills, *global_skills]:
            if skill not in merged:
                merged.append(skill)
        return merged[:6]
