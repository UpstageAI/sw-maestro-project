FROM python:3.11-slim

WORKDIR /app

# git/curl: 일반 유틸
# fonts-nanum: PDF용 한글 ttf (NanumGothic.ttf, reportlab 호환)
# fonts-noto-cjk: 화면 fallback용 (ttc는 reportlab이 못 읽지만 시스템 표시엔 유효)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl fonts-nanum fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
