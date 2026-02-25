FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /workspace

COPY .github/scripts/requirements-warden.txt /tmp/requirements-warden.txt

RUN apt-get update \
  && apt-get install -y --no-install-recommends nodejs npm ca-certificates \
  && npm install -g @openai/codex \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* \
  && python -m pip install --upgrade pip \
  && pip install --no-cache-dir -r /tmp/requirements-warden.txt
