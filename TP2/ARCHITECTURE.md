# ProjetoWeb-Docker - Arquitetura Transformada

## 📋 Resumo da Transformação

O sistema foi transformado conforme os objetivos solicitados:

✅ **Separação Lógica**: Persistência de dados separada da componente Web  
✅ **Comunicação JSON**: Via API REST entre web-server e data-server  
✅ **2 Contentores Docker**: `web-server` e `data-server`  
✅ **Acesso Restrito**: Apenas web-server expõe porta ao host  

---

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────┐
│           HOST (seu computador)             │
│  ┌──────────────────────────────────────┐   │
│  │  Browser → http://localhost:80 ────────┐ │
│  └──────────────────────────────────────┘   │
│           PORT 80 (exposta)                 │
└────────────┬────────────────────────────────┘
             │
      ┌──────┴──────────────────────────────────┐
      │       Docker Network (app-network)      │
      │       172.20.0.0/16                     │
      │                                         │
      │  ┌──────────────────┐                   │
      │  │  web-server      │                   │
      │  │  (Python Flask)  │                   │
      │  │  Porta: 80       │                   │
      │  └────────┬─────────┘                   │
      │           │ (JSON via HTTP)             │
      │           ↓                             │
      │  ┌──────────────────┐                   │
      │  │  data-server     │                   │
      │  │  ┌────────────┐  │                   │
      │  │  │   Flask    │  │                   │
      │  │  │ API REST   │  │                   │
      │  │  ├────────────┤  │                   │
      │  │  │ MariaDB    │  │                   │
      │  │  │   (BD)     │  │                   │
      │  │  └────────────┘  │                   │
      │  │  Porta: 5000     │                   │
      │  │  (não exposta)   │                   │
      │  └──────────────────┘                   │
      │                                         │
      └─────────────────────────────────────────┘
```

---

## 📦 Contentores

### 1. **web-server** (Python_Server/)
- **Responsabilidade**: Interface Web e Autenticação
- **Comunicação**: Faz requisições HTTP/JSON para data-server
- **Porta**: `80` (exposta ao host)
- **Endpoints públicos**: `/login`, `/register`, `/home`, `/map`, `/upload`, `/watch`

**Endpoints da API REST do web-server:**
```
GET  /login
GET  /register
POST /login (autenticação)
POST /register (criar conta)
GET  /home
GET  /map
GET  /upload
POST /upload (submeter vídeo)
GET  /watch/{id}
GET  /logout
```

---

### 2. **data-server** (Data_Server/)
- **Responsabilidade**: Persistência de Dados + MariaDB
- **Comunicação**: Recebe requisições JSON do web-server
- **Porta**: `5000` (apenas rede interna, não exposta)
- **Contém**: Aplicação Flask + MariaDB

**Endpoints da API REST do data-server:**
```
POST   /api/user/create
POST   /api/user/get
POST   /api/user/check-email
PUT    /api/user/update

POST   /api/video/create
POST   /api/video/get-by-hash
POST   /api/video/get-by-id
POST   /api/videos/get-by-uploader
GET    /api/videos/get-all
PUT    /api/video/update
GET    /api/video/count

POST   /api/activation/create
POST   /api/activation/get
DELETE /api/activation/delete

GET    /health (health check)
```

---

## 🚀 Como Usar

### Pré-requisitos
- Docker e Docker Compose instalados
- Ficheiro `.env` configurado com credenciais seguras

### 1. Configurar Variáveis de Ambiente

Edite o ficheiro `.env`:
```bash
# Segurança
SECRET_KEY=sua_chave_super_secreta_aqui

# Base de Dados
DB_NAME=projectweb_demo
DB_USER=projectweb_user
DB_PASSWORD=sua_senha_segura_aqui

# MariaDB Root
MARIADB_ROOT_PASSWORD=sua_senha_root_aqui
```

### 2. Iniciar os Contentores

```bash
# Build e iniciar
docker-compose up --build

# Ou apenas iniciar (sem rebuild)
docker-compose up

# Em background
docker-compose up -d
```

### 3. Verificar Status

```bash
# Ver contentores ativos
docker ps

# Ver logs
docker-compose logs -f

# Ver logs de um contentor específico
docker-compose logs -f web-server
docker-compose logs -f data-server
```

### 4. Testar a Aplicação

```bash
# Aceder à aplicação web
http://localhost

# Verificar saúde do data-server
curl http://localhost:5000/health
# Resposta esperada: {"status": "healthy", "database": "connected"}
```

### 5. Parar os Contentores

```bash
# Parar
docker-compose stop

# Parar e remover
docker-compose down

# Remover com volumes (cuidado - apaga BD!)
docker-compose down -v
```

---

## 🔒 Segurança

✅ **Isolamento de Rede**: Apenas web-server expõe porta  
✅ **Health Checks**: Monitorização automática da saúde dos serviços  
✅ **Logging Estruturado**: Rastreamento de todas as operações  
✅ **Validação de Entrada**: JSON obrigatório, campos validados  
✅ **Senhas em Variáveis**: Credenciais nunca estão no código  
✅ **Tratamento de Erros**: Resposta segura sem expor detalhes internos  

---

## 📊 Fluxo de Dados

### Exemplo: Login de Utilizador

1. **Navegador → web-server (HTTP POST)**
   ```
   POST http://localhost/login
   Corpo: {email: "user@example.com", password: "123456"}
   ```

2. **web-server → data-server (HTTP POST - JSON)**
   ```
   POST http://data-server:5000/api/user/get
   Corpo: {email: "user@example.com"}
   Header: Content-Type: application/json
   ```

3. **data-server → MariaDB (SQL)**
   ```sql
   SELECT * FROM users WHERE email = 'user@example.com'
   ```

4. **Resposta: MariaDB → data-server**
   ```json
   {
     "email": "user@example.com",
     "username": "joao",
     "password": "hash_do_password",
     "lang": "pt",
     "activated": true
   }
   ```

5. **Resposta: data-server → web-server (JSON)**
   ```json
   {
     "success": true,
     "email": "user@example.com",
     "username": "joao",
     "password": "hash_do_password",
     "lang": "pt",
     "activated": true
   }
   ```

6. **Resposta: web-server → Navegador (HTML)**
   ```html
   <!-- Redireciona para /home se válido -->
   ```

---

## 🛠️ Troubleshooting

### Contentor data-server não inicia
```bash
# Ver logs detalhados
docker-compose logs data-server

# Possível causa: MariaDB não inicializa
# Solução: Remover volume e reconstruir
docker-compose down -v
docker-compose up --build
```

### Erro "Connection refused" no web-server
```bash
# Verificar se data-server está saudável
docker-compose ps

# Ver se health check passou
docker inspect projectweb-api | grep -A 5 HealthStatus
```

### BD não persiste
```bash
# Verificar volume
docker volume ls | grep projectweb

# Verificar localização no host
docker inspect projectweb-api | grep -i "mounts" -A 10
```

---

## 📝 Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `DB_NAME` | projectweb | Nome da base de dados |
| `DB_USER` | projectweb | Utilizador da BD |
| `DB_PASSWORD` | projectweb | Senha do utilizador |
| `DB_HOST` | localhost | Host da BD (interno ao data-server) |
| `DB_PORT` | 3306 | Porta da BD |
| `MARIADB_ROOT_PASSWORD` | rootpass | Senha root do MariaDB |
| `SECRET_KEY` | change_me_in_production | Chave secreta Flask |
| `FLASK_ENV` | production | Ambiente (development/production) |
| `FLASK_DEBUG` | False | Debug mode (True/False) |

---

## 🔄 Comunicação via JSON

Todos os endpoints do `data-server` exigem/retornam JSON:

**Requisições:**
```bash
curl -X POST http://data-server:5000/api/user/get \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com"}'
```

**Respostas Sucesso (2xx):**
```json
{
  "success": true,
  "message": "Operação concluída",
  "data": {...}
}
```

**Respostas Erro (4xx/5xx):**
```json
{
  "success": false,
  "error": "Descrição do erro"
}
```

---

## 📚 Estrutura de Ficheiros

```
ProjetoWeb-Docker/
├── docker-compose.yml          # Orquestração dos 2 contentores
├── .env                        # Variáveis de ambiente
├── Makefile                    # Comandos úteis
├── Python_Server/
│   ├── Dockerfile              # Imagem web-server (Python 3.11)
│   └── Server/
│       ├── Server.py           # Aplicação Flask (web)
│       ├── requirements.txt    # Dependências Python
│       ├── setup-Env.sh        # Setup inicial
│       ├── go-Server.sh        # Entrypoint
│       ├── python/
│       │   ├── data_server_api.py    # Cliente API
│       │   ├── db.py                 # (não usado - BD no data-server)
│       │   ├── lang.py               # Suporte multi-idioma
│       │   └── utils.py              # Funções auxiliares
│       ├── static/              # Ficheiros estáticos (CSS, JS)
│       └── templates/           # Templates HTML
│
├── Data_Server/
│   ├── Dockerfile               # Imagem data-server (Python + MariaDB)
│   ├── entrypoint.sh            # Script de inicialização
│   ├── app.py                   # Aplicação Flask (API REST)
│   └── requirements.txt         # Dependências Python
│
├── DB/                          # Volume de dados da BD (gitignored)
└── README.md                    # Esta documentação
```

---

## ✨ Melhorias Implementadas

1. **Dockerfile melhorado**: Usa Python slim, validação de ficheiros, health checks
2. **Logging estruturado**: Todos os eventos registados com timestamps
3. **Validação de entrada**: Campos obrigatórios verificados, erros claros
4. **Health checks**: Auto-verificação da saúde dos serviços
5. **Tratamento de erros**: Erros genéricos sem expor detalhes internos
6. **Isolamento de rede**: Subnet específica, apenas web expõe porta
7. **Entrypoint.sh**: Inicializa MariaDB + Flask automaticamente
8. **Restart policy**: Contentores reiniciam automaticamente
9. **Logging docker**: Limite de tamanho de logs
10. **Documentação clara**: Arquitetura bem documentada

---

## 🎯 Próximas Melhorias

- [ ] Adicionar autenticação com tokens JWT
- [ ] Implementar rate limiting
- [ ] Adicionar HTTPS/SSL
- [ ] Backup automático da BD
- [ ] Monitoring com Prometheus/Grafana
- [ ] Tests unitários e integração
- [ ] CI/CD pipeline (GitHub Actions)

---

**Data**: 20 de Maio de 2026  
**Versão**: 1.0 - Arquitetura Separada  
**Autor**: Transformação Automática
