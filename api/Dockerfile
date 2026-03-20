FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir hatchling

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY app/ app/
COPY migrations/ migrations/
COPY alembic.ini .

EXPOSE 2727

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 2727"]
