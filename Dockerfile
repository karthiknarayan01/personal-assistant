# Shared image for orchestrator, example_specialist, and shopping_agent.
# The actual process to run is supplied per-service (see docker-compose.yml
# / Cloud Run --command --args), so this has no CMD of its own.
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1
