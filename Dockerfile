FROM python:3.11-slim

RUN apt-get update \
    && apt-get install --no-install-recommends -y bluez \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install --no-cache-dir .

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["marshall-heartbit"]

