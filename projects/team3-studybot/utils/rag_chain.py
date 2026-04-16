import os
import requests


def ask_question(question: str, documents: list[str]) -> str:
    api_key = os.getenv("UPSTAGE_API_KEY")
    context = "\n\n".join(documents[:5])

    response = requests.post(
        "https://api.upstage.ai/v1/solar/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "solar-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "당신은 학습 도우미입니다. "
                        "아래 교재 내용을 바탕으로 학생의 질문에 답변하세요.\n\n"
                        f"교재 내용:\n{context}"
                    ),
                },
                {"role": "user", "content": question},
            ],
        },
    )

    return response.json()["choices"][0]["message"]["content"]
