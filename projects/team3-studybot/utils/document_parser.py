import os
import requests


def parse_pdf(uploaded_file) -> list[str]:
    api_key = os.getenv("UPSTAGE_API_KEY")
    files = {"document": (uploaded_file.name, uploaded_file.getvalue(), "application/pdf")}

    response = requests.post(
        "https://api.upstage.ai/v1/document-digitization",
        headers={"Authorization": f"Bearer {api_key}"},
        files=files,
    )

    result = response.json()
    pages = [page["text"] for page in result.get("pages", [])]
    return pages
