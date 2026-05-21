# 🚀 Quick Start - ProjetoWeb-Docker

## ⚡ 5 Passos para Rodar

### 1️⃣ Configurar Variáveis de Ambiente
```bash
# Edite o ficheiro .env com valores seguros
nano .env
```

### 2️⃣ Build dos Contentores
```bash
docker-compose build
```

### 3️⃣ Iniciar Serviços
```bash
docker-compose up -d
```

### 4️⃣ Aguardar Inicialização
```bash
# Ver logs (ctrl+c para sair)
docker-compose logs -f

# Ou verificar se está pronto
docker-compose ps
```

### 5️⃣ Aceder à Aplicação
```
👉 http://localhost
```

---

## 🐛 Comandos Úteis

```bash
# Ver status dos contentores
docker-compose ps

# Ver logs em tempo real
docker-compose logs -f

# Ver logs de um contentor específico
docker-compose logs -f web-server
docker-compose logs -f data-server

# Executar comando dentro do web-server
docker-compose exec web-server bash

# Executar comando dentro do data-server
docker-compose exec data-server bash

# Parar todos os contentores
docker-compose stop

# Remover tudo (sem apagar dados)
docker-compose down

# Remover tudo + dados da BD
docker-compose down -v

# Reiniciar um contentor
docker-compose restart web-server

# Rebuild de um serviço específico
docker-compose up --build web-server
```

---

## ✅ Checklist de Funcionamento

- [ ] `docker-compose ps` mostra 2 contentores UP
- [ ] `docker-compose logs` sem erros
- [ ] Acede a `http://localhost/login` → abre página de login
- [ ] `curl http://localhost/health` → retorna dados

---

## 🔒 Credenciais Padrão (Mude em Produção!)

```env
DB_USER=projectweb_user
DB_PASSWORD=projectweb_pass
DB_NAME=projectweb_demo
MARIADB_ROOT_PASSWORD=change_me_rootpass
SECRET_KEY=change_me_in_production
```

---

## 📱 Testar API

```bash
# Health Check
curl http://localhost:5000/health

# Criar novo utilizador
curl -X POST http://localhost:5000/api/user/create \
  -H "Content-Type: application/json" \
  -d '{
    "email": "teste@example.com",
    "username": "joao",
    "password": "123456",
    "lang": "pt",
    "activated": false
  }'

# Obter utilizador
curl -X POST http://localhost:5000/api/user/get \
  -H "Content-Type: application/json" \
  -d '{"email": "teste@example.com"}'
```

---

## 🆘 Problemas Comuns

### Erro: "Connection refused"
```bash
# Aguarde 10-15 segundos para MariaDB inicializar
# Ver logs:
docker-compose logs data-server
```

### Erro: "Port 80 already in use"
```bash
# Liberar porta ou usar outra no docker-compose.yml
# Altere: ports: - "80:80" para "8080:80"
```

### Erro: "Cannot connect to data-server"
```bash
# Verificar se data-server passou no health check
docker inspect projectweb-api | grep -i "health"
```

### Remover Volume Corrompido
```bash
# Listar volumes
docker volume ls

# Remover volume
docker volume rm projectweb-docker_db_data

# Reiniciar
docker-compose up --build
```

---

## 📚 Documentação Completa

Ver ficheiro `ARCHITECTURE.md` para detalhes:
- Arquitetura visual
- Endpoints disponíveis
- Fluxo de dados
- Troubleshooting avançado

---

**Tudo pronto! 🎉**  
Aceda a http://localhost para começar!
