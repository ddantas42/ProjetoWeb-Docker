FROM python:3.11-slim

WORKDIR /app

# Instalar MariaDB server + curl + outras ferramentas
RUN apt-get update && apt-get install -y \
    mariadb-server \
    curl \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Preparar diretórios com permissões
RUN mkdir -p /var/lib/mysql /run/mysqld && \
    chown -R mysql:mysql /var/lib/mysql /run/mysqld && \
    chmod 755 /run/mysqld

# Instalar dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicação e script de inicialização
COPY app.py /app/app.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

ENTRYPOINT ["/entrypoint.sh"]
