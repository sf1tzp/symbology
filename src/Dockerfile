FROM python:3.13-slim-bullseye AS builder

WORKDIR /app

RUN apt update
RUN apt install -y cmake make gcc postgresql gcc python3-dev python3-psycopg2 libpq-dev

RUN pip install uv psycopg2-binary

COPY requirements.lock .

RUN uv pip install --system  --no-cache-dir -r requirements.lock

COPY . /app/src/

EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
