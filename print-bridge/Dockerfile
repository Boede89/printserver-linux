FROM python:3.12-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends cups-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY print_bridge.py config.example.yaml ./

ENV PRINT_BRIDGE_PORT=8766
EXPOSE 8766

CMD ["python", "-u", "print_bridge.py"]
