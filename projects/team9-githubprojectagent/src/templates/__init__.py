from src.models.template import NotionTemplate

from . import cover, detailed, minimal, project_record, star, troubleshooting

TEMPLATES: dict[str, NotionTemplate] = {
    minimal.TEMPLATE.id: minimal.TEMPLATE,
    detailed.TEMPLATE.id: detailed.TEMPLATE,
    troubleshooting.TEMPLATE.id: troubleshooting.TEMPLATE,
    cover.TEMPLATE.id: cover.TEMPLATE,
    project_record.TEMPLATE.id: project_record.TEMPLATE,
    star.TEMPLATE.id: star.TEMPLATE,
}


def get(template_id: str) -> NotionTemplate:
    if template_id not in TEMPLATES:
        raise ValueError(f"unknown template: {template_id}")
    return TEMPLATES[template_id]


def list_all() -> list[NotionTemplate]:
    return list(TEMPLATES.values())
