from fastapi import FastAPI
from services.summarizer import summarize_article

app = FastAPI(title="AI 뉴스 요약 서비스")


@app.get("/")
def root():
    return {"message": "AI 뉴스 요약 서비스에 오신 것을 환영합니다!"}


@app.post("/summarize")
def summarize(article: dict):
    result = summarize_article(article["text"])
    return {"summary": result}
