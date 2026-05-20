FROM python:3.11-slim

WORKDIR /app

COPY ./Server/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./Server/ /app/

RUN chmod +x /app/setup-Env.sh && /app/setup-Env.sh

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:80/login')" || exit 1

CMD ["bash", "/app/go-Server.sh"]