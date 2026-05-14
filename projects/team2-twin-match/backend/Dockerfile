FROM python:3.11.8-slim

WORKDIR /app

RUN pip install --no-cache-dir poetry

COPY ./poetry.lock ./pyproject.toml ./

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes \
    && pip install --no-cache-dir -r requirements.txt

COPY ./app ./app
COPY ./entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

ENTRYPOINT ["bash", "/entrypoint.sh"]
