import os
import requests


def summarize_article(text: str) -> str:
    api_key = os.getenv("SOLAR_API_KEY")
    response = requests.post(
        "https://api.upstage.ai/v1/solar/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "solar-mini",
            "messages": [
                {"role": "system", "content": "뉴스 기사를 3줄로 요약해주세요."},
                {"role": "user", "content": text},
            ],
        },
    )
    return response.json()["choices"][0]["message"]["content"]
