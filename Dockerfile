FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MICROSHOP_DATA_DIR=/app/data
ENV MICROSHOP_BIND_HOST=0.0.0.0

RUN addgroup --system microshop \
    && adduser --system --ingroup microshop microshop

COPY microshop ./microshop
COPY services ./services
COPY frontend ./frontend
COPY run_local.py ./run_local.py
COPY README.md ./README.md

RUN mkdir -p /app/data \
    && chown -R microshop:microshop /app

USER microshop

EXPOSE 8080 8101 8102 8103 8104

CMD ["python", "-m", "services.gateway.app"]
