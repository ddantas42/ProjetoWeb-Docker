#!/bin/bash
set -e

# Cores para logging
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}=== Iniciando ProjetoWeb Data Server ===${NC}"

# Variáveis
DB_USER="${DB_USER:-projectweb}"
DB_PASSWORD="${DB_PASSWORD:-projectweb}"
DB_NAME="${DB_NAME:-projectweb}"
MYSQL_ROOT_PASSWORD="${MARIADB_ROOT_PASSWORD:-rootpass}"

# Diretórios
MYSQL_DATA_DIR="/var/lib/mysql"
MYSQL_RUN_DIR="/run/mysqld"

# Criar diretorios com permissões corretas
mkdir -p "$MYSQL_DATA_DIR" "$MYSQL_RUN_DIR"
chown -R mysql:mysql "$MYSQL_DATA_DIR" "$MYSQL_RUN_DIR"
chmod 755 "$MYSQL_RUN_DIR"

# Inicializar dados do MariaDB se não existirem
if [ ! -d "$MYSQL_DATA_DIR/mysql" ]; then
    echo -e "${YELLOW}Inicializando base de dados MariaDB...${NC}"
    if command -v mariadb-install-db >/dev/null 2>&1; then
        mariadb-install-db --user=mysql --datadir="$MYSQL_DATA_DIR" --auth-root-authentication-method=normal --skip-test-db --silent 2>/dev/null || true
    else
        mysql_install_db --user=mysql --datadir="$MYSQL_DATA_DIR" --silent 2>/dev/null || true
    fi
    chown -R mysql:mysql "$MYSQL_DATA_DIR"
fi

# Iniciar MariaDB em background
echo -e "${YELLOW}Iniciando MariaDB...${NC}"
mysqld_safe --user=mysql --skip-syslog --datadir="$MYSQL_DATA_DIR" &
MYSQL_PID=$!

# Aguardar MariaDB estar pronto
echo -e "${YELLOW}Aguardando MariaDB ficar pronto...${NC}"
MAX_ATTEMPTS=60
ATTEMPT=1
until mysqladmin ping -u root -p"${MYSQL_ROOT_PASSWORD}" --silent 2>/dev/null || mysqladmin ping -u root --silent 2>/dev/null; do
    if [ $ATTEMPT -ge $MAX_ATTEMPTS ]; then
        echo -e "${RED}ERRO: MariaDB não respondeu em tempo${NC}"
        kill $MYSQL_PID 2>/dev/null || true
        exit 1
    fi
    echo "Tentativa $ATTEMPT/$MAX_ATTEMPTS..."
    sleep 1
    ATTEMPT=$((ATTEMPT + 1))
done

echo -e "${GREEN}✓ MariaDB está pronto${NC}"

# Determinar como autenticar no cliente local
if mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1" >/dev/null 2>&1; then
    MYSQL_CLIENT=(mysql -u root -p"${MYSQL_ROOT_PASSWORD}")
else
    MYSQL_CLIENT=(mysql -u root)
fi

# Configurar MariaDB
echo -e "${YELLOW}Configurando MariaDB...${NC}"
"${MYSQL_CLIENT[@]}" <<MYSQL_EOF
CREATE DATABASE IF NOT EXISTS \`${DB_NAME}\`;

CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';
CREATE USER IF NOT EXISTS '${DB_USER}'@'127.0.0.1' IDENTIFIED BY '${DB_PASSWORD}';

ALTER USER 'root'@'localhost' IDENTIFIED BY '${MYSQL_ROOT_PASSWORD}';

GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'localhost';
GRANT ALL PRIVILEGES ON \`${DB_NAME}\`.* TO '${DB_USER}'@'127.0.0.1';

DROP USER IF EXISTS ''@'localhost';
DROP USER IF EXISTS ''@'127.0.0.1';
DROP USER IF EXISTS ''@'%';

FLUSH PRIVILEGES;
MYSQL_EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}Erro ao configurar MariaDB${NC}"
    exit 1
fi

echo -e "${GREEN}✓ MariaDB configurado${NC}"

# Iniciar aplicação Flask
echo -e "${YELLOW}Iniciando Flask Application...${NC}"
echo -e "${GREEN}✓ Sistema pronto em http://0.0.0.0:5000${NC}"
exec python /app/app.py

