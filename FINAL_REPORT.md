# ProjetoWeb-Docker -- Plataforma Distribuída de Partilha Multimédia Georreferenciada

## 1. Arquitetura de Alto Nível

O presente sistema implementa uma **arquitetura multicamada (multi-tier) orientada a serviços**, orquestrada por contentores Docker e coordenada por um proxy inverso. O modelo arquitetural adotado decompõe-se em quatro contentores logicamente distintos, cada um encapsulado num contentor isolado:

| Camada | Contentor | Responsabilidade |
|--------|-----------------|------------------|
| Request Engine | `nginx` | Ponto único de entrada; encaminhamento HTTP para a camada de apresentação |
| Frontend/Backend  | `web-server` | Renderização de páginas HTML (Flask) |
| API de Comunicação com a DB | `api-server` | API REST com acesso exclusivo à base de dados |
| Base de dados | `db-server` | Sistema de gestão de base de dados relacional (MariaDB 10.11) |

A comunicação entre camadas segue o seguinte:

- **REST sobre HTTP/JSON** -- exposto pelo `api-server` (porta 5000) para operações CRUD convencionais.
- **Sockets TCP** -- o `web-server` comunica com o `api-server` através de ligações TCP na porta 9000, utilizando um protocolo de mensagens ação-payload serializado em JSON.

Adicionalmente, a Fase 3 do projeto integra um subsistema **IoT** que recorre a dois protocolos de comunicação adicionais:

- **REST sobre HTTPS** -- o `web-server` atua como proxy, contactando uma API REST externa de sensores meteorológicos.
- **MQTT (Message Queuing Telemetry Transport)** -- um cliente MQTT em segundo plano, executado numa thread dedicada do `web-server`, subscreve tópicos de um broker remoto e armazena as últimas leituras em memória.

Toda a infraestrutura de rede está confinada a uma rede bridge Docker privada (`app-network`, sub-rede `172.20.0.0/16`), sendo o Nginx o único componente com porta exposta ao host (porta 80).

**Justificação do papel de cada componente na topologia distribuída:**

- **Nginx** -- atua como ponto único de entrada (single point of contact), isolando os serviços internos do tráfego externo e permitindo escalabiblidade.
- **Python_Server (web-server)** -- Responsável pela camada de apresentação; não possui acesso direto à base de dados, delegando todas as operações de base de dados ao api-server.
- **Data_Server (api-server)** -- Encapsula a lógica de acesso a dados, expondo uma interface dupla (REST + Sockets TCP) e mantendo a única ligação à base de dados.
- **DB_Server (db-server)** -- Armazenamento persistente, acessível exclusivamente dentro da rede Docker privada.

---


## 2. Dados e pedidos

### 2.1. Comunicação Web-Server para Api-Server: Sockets TCP

A comunicação entre o `web-server` e o `api-server` é realizada **exclusivamente via sockets TCP (SOCK_STREAM)** na porta 9000. O protocolo utiliza **JSON delimitado por quebras de linha (newline-delimited JSON)**, onde cada mensagem é um objeto JSON seguido do carácter `\n`.

**Formato das mensagens de pedido (cliente para servidor):**

```json
{
  "action": "<nome_da_operacao>",
  "payload": { <dados_especificos_da_operacao> }
}
```

**Formato das mensagens de resposta (servidor para cliente):**

```json
{
  "success": true|false,
  "status": <codigo_http_equivalente>,
  "<campos_de_dados>": "..."
}
```

Cada pedido abre uma nova ligação TCP, envia uma única mensagem e aguarda a resposta. A classe `DataServerAPI` (em `data_server_api.py`) encapsula este protocolo:

```python
class DataServerAPI:
    def __init__(self):
        self.host = os.getenv('DATA_SERVER_HOST', 'data-server')
        self.port = int(os.getenv('DATA_SOCKET_PORT', '9000'))

    def _send_request(self, action, payload=None):
        req = {
            'action': action,
            'payload': payload or {}
        }
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((self.host, self.port))
            s.sendall((json.dumps(req) + '\n').encode('utf-8'))
            buffer = ""
            while '\n' not in buffer:
                data = s.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
            line = buffer.split('\n')[0]
            resp_data = json.loads(line)
            status_code = resp_data.pop('status', 200 if resp_data.get('success') else 400)
            return DummyResponse(resp_data, status_code)
```

A classe `DummyResponse` emula a interface de `requests.Response`, permitindo que o `Server.py` utilize a API de sockets com a mesma interface que usaria para chamadas HTTP.

**Ações suportadas pelo protocolo de sockets resumindo (definidas em `process_socket_request` no `app.py`):**

| Ação | Descrição | Campos do Payload |
|------|-----------|-------------------|
| `create_user` | Registo de novo utilizador | `email`, `username`, `password`, `lang`, `activated` |
| `get_user` | Obtenção de dados de utilizador | `email` |
| `check_email` | Verificação de existência de email | `email` |
| `update_user` | Atualização de dados de utilizador | `email`, campos opcionais |
| `create_video` | Registo de novo vídeo | `hash_index`, `filename`, `title`, `extension`, `uploader`, ... |
| `get_video_by_hash` | Pesquisa de vídeo por hash MD5 | `hash_index` |
| `get_video_by_id` | Pesquisa de vídeo por identificador | `id` |
| `get_videos_by_uploader` | Listagem de vídeos de um utilizador | `uploader` |
| `get_all_videos` | Listagem completa de vídeos | (nenhum) |
| `update_video` | Atualização de metadados de vídeo | `id`, `title`, `description` |
| `create_activation` | Criação de registo de ativação | `hash`, `email` |
| `get_activation` | Obtenção de registo de ativação | `hash` |
| `delete_activation` | Remoção de registo de ativação | `hash` |
| `get_video_count` | Contagem total de vídeos | (nenhum) |

<details><summary> Conjunto de todos os pedidos possíveis </summary> 

**Referência da API -- Sockets TCP / REST Equivalente**

Cada operação é descrita com os campos do payload JSON, tipos, obrigatoriedade e respostas esperadas. O cabeçalho `Content-Type: application/json` é obrigatório em todos os pedidos REST.

---

#### POST `/api/user/create` -- Ação socket: `create_user`

Registo de novo utilizador.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `email` | string | Sim | Endereço de email (chave primária) |
| `username` | string | Sim | Nome de utilizador |
| `password` | string | Sim | Hash MD5 da palavra-passe |
| `lang` | string | Sim | Código de idioma (`en`, `pt`, `es`, `fr`) |
| `activated` | boolean | Não | Estado de ativação (por omissão: `false`) |

```json
{
  "email": "utilizador@exemplo.com",
  "username": "joao",
  "password": "202cb962ac59075b964b07152d234b70",
  "lang": "pt",
  "activated": false
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 201 | `{"success": true, "message": "User criado com sucesso"}` |
| 409 | `{"success": false, "error": "Email já registado"}` |
| 400 | `{"success": false, "error": "Campos obrigatórios: email, username, ..."}` |

---

#### POST `/api/user/get` -- Ação socket: `get_user`

Obtenção de dados de um utilizador por email.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `email` | string | Sim | Endereço de email do utilizador |

```json
{
  "email": "utilizador@exemplo.com"
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "email": "...", "username": "...", "password": "...", "lang": "...", "activated": true}` |
| 404 | `{"success": false, "error": "User não encontrado"}` |

---

#### POST `/api/user/check-email` -- Ação socket: `check_email`

Verificação de existência de email na base de dados.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `email` | string | Sim | Endereço de email a verificar |

```json
{
  "email": "utilizador@exemplo.com"
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"exists": true}` ou `{"exists": false}` |

---

#### PUT `/api/user/update` -- Ação socket: `update_user`

Atualização parcial dos dados de um utilizador. Apenas os campos enviados são atualizados; os restantes mantêm o valor atual.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `email` | string | Sim | Endereço de email (identifica o utilizador a atualizar) |
| `username` | string | Não | Novo nome de utilizador |
| `password` | string | Não | Novo hash MD5 da palavra-passe |
| `lang` | string | Não | Novo código de idioma (`en`, `pt`, `es`, `fr`) |
| `activated` | boolean | Não | Novo estado de ativação |

```json
{
  "email": "utilizador@exemplo.com",
  "activated": true
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "message": "User atualizado"}` |
| 404 | `{"success": false, "error": "User não encontrado"}` |

---

#### POST `/api/video/create` -- Ação socket: `create_video`

Registo de um novo vídeo/conteúdo multimédia.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `hash_index` | string | Sim | Hash MD5 do nome do ficheiro (chave primária) |
| `filename` | string | Sim | Nome do ficheiro armazenado (ex: `1.mp4`) |
| `title` | string | Sim | Título do vídeo |
| `extension` | string | Sim | Extensão do ficheiro (`mp4`, `mp3`, `jpg`, `jpeg`, `png`) |
| `uploader` | string | Sim | Username do utilizador que fez o carregamento |
| `id` | integer | Não | Identificador numérico do vídeo (por omissão: `0`) |
| `description` | string | Não | Descrição do conteúdo (por omissão: `""`) |
| `latitude` | string | Não | Latitude geográfica (por omissão: `"0"`) |
| `longitude` | string | Não | Longitude geográfica (por omissão: `"0"`) |
| `hash` | string | Não | Hash MD5 adicional (por omissão: `""`) |

```json
{
  "hash_index": "d41d8cd98f00b204e9800998ecf8427e",
  "id": 1,
  "filename": "1.mp4",
  "title": "Vista da Ponte 25 de Abril",
  "description": "Filmagem aérea da ponte",
  "latitude": "38.6916",
  "longitude": "-9.1778",
  "extension": "mp4",
  "uploader": "joao",
  "hash": "d41d8cd98f00b204e9800998ecf8427e"
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 201 | `{"success": true, "message": "Video criado com sucesso"}` |
| 409 | `{"success": false, "error": "Video já existe"}` |
| 400 | `{"success": false, "error": "Campos obrigatórios: hash_index, filename, ..."}` |

---

#### POST `/api/video/get-by-hash` -- Ação socket: `get_video_by_hash`

Pesquisa de vídeo por hash MD5.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `hash_index` | string | Sim | Hash MD5 do nome do ficheiro |

```json
{
  "hash_index": "d41d8cd98f00b204e9800998ecf8427e"
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "hash_index": "...", "id": 1, "filename": "...", "title": "...", "description": "...", "latitude": "...", "longitude": "...", "extension": "...", "uploader": "...", "hash": "..."}` |
| 404 | `{"success": false, "error": "Video não encontrado"}` |

---

#### POST `/api/video/get-by-id` -- Ação socket: `get_video_by_id`

Pesquisa de vídeo por identificador numérico.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | integer | Sim | Identificador numérico do vídeo |

```json
{
  "id": 1
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "hash_index": "...", "id": 1, "filename": "...", "title": "...", "description": "...", "latitude": "...", "longitude": "...", "extension": "...", "uploader": "...", "hash": "..."}` |
| 404 | `{"success": false, "error": "Video não encontrado"}` |

---

#### POST `/api/videos/get-by-uploader` -- Ação socket: `get_videos_by_uploader`

Listagem de todos os vídeos carregados por um utilizador.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `uploader` | string | Sim | Username do utilizador |

```json
{
  "uploader": "joao"
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "videos": [{"hash_index": "...", "id": 1, ...}, ...]}` |

---

#### GET `/api/videos/get-all` -- Ação socket: `get_all_videos`

Listagem completa de todos os vídeos registados.

**Request Body:** Nenhum.

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "videos": [{"hash_index": "...", "id": 1, ...}, ...]}` |

---

#### PUT `/api/video/update` -- Ação socket: `update_video`

Atualização parcial dos metadados de um vídeo. Apenas os campos enviados são atualizados.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `id` | integer | Sim | Identificador numérico do vídeo a atualizar |
| `title` | string | Não | Novo título do vídeo |
| `description` | string | Não | Nova descrição do vídeo |

```json
{
  "id": 1,
  "title": "Título atualizado",
  "description": "Nova descrição"
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "message": "Video atualizado"}` |
| 404 | `{"success": false, "error": "Video não encontrado"}` |

---

#### POST `/api/activation/create` -- Ação socket: `create_activation`

Criação de um registo de ativação de conta.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `hash` | string | Sim | Hash MD5 do email (chave primária) |
| `email` | string | Sim | Endereço de email associado |

```json
{
  "hash": "0cc175b9c0f1b6a831c399e269772661",
  "email": "utilizador@exemplo.com"
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 201 | `{"success": true, "message": "Activation criada"}` |
| 400 | `{"success": false, "error": "Campos obrigatórios: hash, email"}` |

---

#### POST `/api/activation/get` -- Ação socket: `get_activation`

Obtenção de um registo de ativação por hash.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `hash` | string | Sim | Hash MD5 do email |

```json
{
  "hash": "0cc175b9c0f1b6a831c399e269772661"
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "email": "utilizador@exemplo.com"}` |
| 404 | `{"success": false, "error": "Activation não encontrada"}` |

---

#### DELETE `/api/activation/delete` -- Ação socket: `delete_activation`

Remoção de um registo de ativação.

**Request Body:**

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `hash` | string | Sim | Hash MD5 do email |

```json
{
  "hash": "0cc175b9c0f1b6a831c399e269772661"
}
```

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "message": "Activation deletada"}` |
| 404 | `{"success": false, "error": "Activation não encontrada"}` |

---

#### GET `/api/video/count` -- Ação socket: `get_video_count`

Contagem total de vídeos registados.

**Request Body:** Nenhum.

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"success": true, "count": 42}` |

---

#### GET `/health`

Verificação do estado de saúde do api-server e da ligação à base de dados. Utilizado exclusivamente pelo healthcheck do Docker.

**Request Body:** Nenhum.

**Respostas:**

| Código | Corpo |
|--------|-------|
| 200 | `{"status": "healthy", "database": "connected"}` |
| 500 | `{"status": "unhealthy", "database": "disconnected", "error": "..."}` |
</details>

### 2.2. Comunicação IoT: REST Externo e MQTT

**REST externo (Fase 3):**

O `web-server` atua como proxy para uma API REST IoT externa configurada pela variável de ambiente `IOT_REST_BASE_URL`. A função `_safe_json_response` em `Server.py` efetua pedidos HTTPS à API externa e devolve os dados ao navegador:

```python
def _safe_json_response(url):
    try:
        response = requests.get(url, timeout=5, verify=IOT_REST_VERIFY_SSL)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logging.error(f"IoT REST request failed for {url}: {e}")
        return {"error": str(e)}
```

O navegador consulta os endpoints locais `/api/iot/rest/state`, que internamente contactam `{IOT_REST_BASE_URL}/weather/values` e `{IOT_REST_BASE_URL}/weather/position`. Este mecanismo evita problemas de CORS no navegador.

**MQTT (Fase 3):**

Um cliente MQTT (`paho-mqtt`) é lançado numa thread de segundo plano no `web-server`, subscrevendo o tópico `/weather` de um broker remoto. As mensagens recebidas são armazenadas no dicionário `IOT_MQTT_STATE`:

```python
IOT_MQTT_STATE = {
    "connected": False,
    "last_error": None,
    "last_update": None,
    "topics": {}
}
IOT_MQTT_LOCK = threading.Lock()
```

O dashboard do navegador consulta o estado MQTT através do endpoint `/api/iot/mqtt/latest`. O cliente MQTT é inicializado pela função `_start_iot_mqtt_client()`, que garante uma única instância através da flag `IOT_MQTT_STARTED`.

### 2.3. Serialização de Dados

Toda a comunicação inter-nodal utiliza exclusivamente **JSON (JavaScript Object Notation)** como formato de serialização:

- **Sockets TCP**: mensagens JSON delimitadas por carácter de nova linha (`\n`), codificadas em UTF-8.
- **MQTT**: payloads de mensagens em JSON (quando emitidas pelo sensor IoT).
- **Internacionalização**: ficheiros de tradução armazenados em JSON (`lang/*.json`), carregados pelo módulo `lang.py`.

### 2.4. Diagrama de Fluxo de Comunicação

```
Navegador (Browser)
     |
     | HTTP (porta 80)
     v
+---------+
|  Nginx  | ---- Proxy inverso; encaminha todo o tráfego HTTP
+---------+
     |
     | HTTP (porta 80, rede interna)
     v
+-------------+
| web-server  |---- Sockets TCP (porta 9000) ----------> +------------+
| (Flask)     |                                           | api-server |
|             |                                           | (Flask)    |
|  [Thread    |---- MQTT (porta 1883) -----> Broker IoT   |            |
|   MQTT]     |                               externo     |            |
|             |---- HTTPS -----> API REST IoT externa     |            |
+-------------+                                           +-----+------+
                                                                |
                                                    SQLAlchemy ORM (pymysql)
                                                                |
                                                                v
                                                        +-----------+
                                                        | db-server |
                                                        | (MariaDB) |
                                                        +-----------+
```


---

## 3. Requisitos, Implementação e Execução

### 3.1. Pré-requisitos do Sistema

| Requisito | Versão Mínima | Observação |
|-----------|---------------|------------|
| Docker Engine | 20.10+ | Motor de contentorização |
| Docker Compose | 2.0+ | Orquestração multi-contentor (plugin v2) |
| Sistema Operativo | Linux, macOS ou Windows com WSL2 | Compatibilidade Docker |
| Rede | Acesso à Internet | Para pull de imagens e comunicação com broker IoT externo |

### 3.2. Configuração de Variáveis de Ambiente

Copiar o ficheiro modelo e ajustar as credenciais:

```bash
cp .env.example .env
```

Conteúdo do ficheiro `.env`:

```bash
# Credenciais da base de dados
DB_NAME=projectweb_demo
DB_USER=projectweb_user
DB_PASSWORD=projectweb_pass
MARIADB_ROOT_PASSWORD=change_me_rootpass

# Configuração IoT (Fase 3)
IOT_REST_BASE_URL=https://cjsg.ddns.net:8443
IOT_REST_VERIFY_SSL=false
IOT_MQTT_HOST=cjsg.ddns.net
IOT_MQTT_PORT=1883
IOT_MQTT_USER=
IOT_MQTT_PASSWORD=
```

### 3.3. Compilação e Arranque

**Arranque completo (build + start de todos os contentores):**

```bash
make all
```

Este comando executa internamente:

```bash
docker compose -f ./docker-compose.yml up --build
```

O Docker Compose orquestra a seguinte sequência de arranque, respeitando as dependências declaradas:

1. `db-server` (MariaDB) -- inicia primeiro; healthcheck via `mysqladmin ping`
2. `api-server` (Flask + Socket Server) -- aguarda `db-server` healthy; cria tabelas via SQLAlchemy; lança thread do servidor de sockets TCP na porta 9000
3. `web-server` (Flask Web) -- aguarda `api-server` healthy; arranca Flask na porta 80
4. `nginx` -- aguarda `web-server` healthy; expõe a porta 80 ao host

**Arranque em segundo plano (modo detached):**

```bash
docker compose -f docker-compose.yml up --build -d
```

**Verificação do estado dos contentores:**

```bash
make status
```

**Acesso à aplicação:**

```
http://localhost
```

### 3.4. Comandos de Gestão

| Comando | Descrição |
|---------|-----------|
| `make all` | Build e arranque de todos os contentores (modo interativo) |
| `make down` | Paragem e remoção dos contentores |
| `make status` | Listagem dos contentores e imagens ativas |
| `make clean` | Remoção completa de contentores, imagens, volumes e redes |
| `make deepclean` | Limpeza profunda incluindo `docker system prune` |
| `make re` | Limpeza profunda seguida de reconstrução completa |

### 3.5. Instanciação dos Contentores

Todos os contentores são instanciados automaticamente pelo Docker Compose. A relação de dependência é a seguinte:

```
nginx  -->  web-server  -->  api-server  -->  db-server
```

Cada seta indica "depende de" (condition: `service_healthy`). Os healthchecks garantem que um contentor só é considerado operacional após responder positivamente:

```yaml
# db-server: healthcheck
test: ["CMD", "mysqladmin", "ping", "-h", "localhost"]

# api-server: healthcheck (único uso do endpoint HTTP na porta 5000)
test: ["CMD", "curl", "-f", "http://localhost:5000/health"]

# web-server: healthcheck
test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:80/login').raise_for_status()"]

# nginx: healthcheck
test: ["CMD", "wget", "-q", "--spider", "http://127.0.0.1/login"]
```

---

## 4. Tratamento de Problemas Distribuídos

### 4.1. Gestão de Concorrência e Threads

O sistema apresenta vários cenários de concorrência, geridos através de threads:

**a) Servidor de Sockets TCP Multi-Threaded (`socket_server.py`):**

O `api-server` implementa um servidor de sockets TCP que cria uma nova thread para cada cliente conectado, seguindo o modelo **thread-per-connection**:

```python
def start_socket_server(process_func, host='0.0.0.0', port=9000):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen(5)

    while True:
        conn, addr = server.accept()
        client_thread = threading.Thread(
            target=handle_client,
            args=(conn, addr, process_func)
        )
        client_thread.daemon = True
        client_thread.start()
```

Cada thread de cliente processa mensagens de forma independente, lendo dados do socket num ciclo contínuo com gestão de buffer para enquadramento baseado em `\n`. As threads são configuradas como *daemon*, garantindo que terminam automaticamente quando o processo principal encerra.

**b) Thread MQTT em Segundo Plano (`Server.py`):**

O cliente MQTT é executado numa thread dedicada que invoca `client.loop_forever()`, mantendo uma ligação persistente ao broker:

```python
def _start_iot_mqtt_client():
    global IOT_MQTT_STARTED
    if IOT_MQTT_STARTED:
        return
    IOT_MQTT_STARTED = True
    # ...
    threading.Thread(target=run_client, daemon=True).start()
```

A flag `IOT_MQTT_STARTED` implementa um padrão de inicialização única, assegurando que apenas uma instância do cliente MQTT é criada durante o ciclo de vida da aplicação.

**c) Lançamento do Socket Server no Api-Server (`app.py`):**

O `api-server` lança o servidor de sockets numa thread separada da aplicação Flask, permitindo que o servidor de sockets e o endpoint de healthcheck coexistam no mesmo processo:

```python
socket_thread = threading.Thread(
    target=start_socket_server,
    args=(process_socket_request,)
)
socket_thread.daemon = True
socket_thread.start()

app.run(host='0.0.0.0', port=5000)
```

### 4.2. Exclusão Mútua e Sincronização de Estado

**a) Proteção do Estado MQTT Partilhado:**

O dicionário `IOT_MQTT_STATE` é acedido concorrentemente pela thread MQTT (escritas nos callbacks `on_message`, `on_connect`, `on_disconnect`) e pelas threads de pedidos HTTP do Flask (leituras no endpoint `/api/iot/mqtt/latest`). A sincronização é garantida por um `threading.Lock`:

```python
IOT_MQTT_LOCK = threading.Lock()

# Escrita (thread MQTT - callback on_message):
with IOT_MQTT_LOCK:
    IOT_MQTT_STATE["topics"][message.topic] = {
        "value": value,
        "received_at": time.strftime('%Y-%m-%d %H:%M:%S')
    }
    IOT_MQTT_STATE["last_update"] = time.strftime('%Y-%m-%d %H:%M:%S')

# Leitura (thread HTTP Flask - endpoint /api/iot/mqtt/latest):
with IOT_MQTT_LOCK:
    state = json.loads(json.dumps(IOT_MQTT_STATE))
```

A leitura utiliza uma cópia profunda por serialização/deserialização JSON para garantir que o dicionário retornado ao cliente não é alterado pela thread MQTT durante a serialização da resposta HTTP.

**b) Transações na Base de Dados (SQLAlchemy):**

As operações de escrita na base de dados são protegidas por transações com *rollback* em caso de exceção, tal como implementado em `process_socket_request` e nos decorators do `app.py`:

```python
try:
    db.session.add(new_user)
    db.session.commit()
except Exception as e:
    db.session.rollback()
```

### 4.3. Tolerância a Falhas

**a) Reconexão Automática de Contentores:**

Todos os serviços estão configurados com a política de reinício `restart: unless-stopped` no `docker-compose.yml`, garantindo que um contentor que falhe inesperadamente é automaticamente reiniciado pelo Docker Engine.

**b) Retry na Ligação à Base de Dados:**

O `api-server` implementa um mecanismo de tentativa repetida para a ligação inicial à base de dados, tolerando atrasos no arranque do MariaDB:

```python
max_retries = 30
for i in range(max_retries):
    try:
        db.create_all()
        logger.info("Database tables created/verified")
        break
    except Exception as e:
        logger.warning(f"Database not ready yet, retrying in 2 seconds... ({i+1}/{max_retries})")
        time.sleep(2)
else:
    logger.error("Could not connect to database after several retries.")
    exit(1)
```

Este padrão implementa um *retry* linear com intervalo de 2 segundos e um máximo de 30 tentativas (60 segundos de tolerância), terminando o processo caso a base de dados permaneça indisponível.

**c) Healthchecks e Dependências Ordenadas:**

A cadeia de dependências no `docker-compose.yml` (`db-server` -> `api-server` -> `web-server` -> `nginx`), combinada com healthchecks periódicos (intervalo de 30 segundos, 3 tentativas), assegura que um serviço só é iniciado quando as suas dependências estão operacionais.

**d) Tratamento de Erros na Comunicação por Sockets:**

O cliente TCP (`DataServerAPI`) captura exceções de ligação e devolve um objeto `DummyResponse` com código de erro 500, evitando que a falha do `api-server` provoque a terminação do `web-server`:

```python
except Exception as e:
    logging.error(f"Socket connection error: {e}")
    return DummyResponse({'success': False, 'error': str(e)}, 500)
```

No lado do servidor (`socket_server.py`), cada thread de cliente está protegida por blocos `try/except` que registam o erro e terminam a ligação sem afetar as demais:

```python
except Exception as e:
    logger.error(f"Socket error with {addr}: {e}")
    break
```

**e) Tratamento Defensivo no Cliente MQTT:**

O cliente MQTT trata cenários de indisponibilidade presentes no código:

- Ausência da biblioteca `paho-mqtt` (importação condicional com `try/except ImportError` no `Server.py`, linha 19-22).
- Credenciais não configuradas (verificação de `IOT_MQTT_USER` e `IOT_MQTT_PASSWORD` antes de tentar a ligação).
- Falhas de ligação ao broker (captura de exceções no `run_client`, registo em log e atualização de `IOT_MQTT_STATE["last_error"]`).

**f) Decorators de Validação no Api-Server (`app.py`):**

O `api-server` utiliza dois decorators para validação de pedidos recebidos via HTTP (utilizados pelo endpoint `/health` e pelos endpoints REST presentes no código):

- `@require_json` -- rejeita pedidos sem o cabeçalho `Content-Type: application/json`.
- `@handle_errors` -- captura exceções `KeyError` (campos ausentes) e `Exception` (erros genéricos), devolvendo respostas JSON estruturadas.

### 4.4. Isolamento de Rede

- Apenas a porta 80 do Nginx é exposta ao host; todos os restantes serviços comunicam exclusivamente na rede interna Docker (`app-network`, sub-rede `172.20.0.0/16`).
- O `db-server` não possui qualquer porta exposta ao host, sendo acessível apenas pelo `api-server`.
- As credenciais são injetadas via variáveis de ambiente (ficheiro `.env`) e nunca codificadas no código-fonte de produção.
- As palavras-passe dos utilizadores são armazenadas como hashes MD5 (função `hashlib.md5` em `Server.py`).


---

# 5 Resumo
## Nota sobre Utilização de Inteligência Artificial

A especificação detalhada dos endpoints da API apresentada na Secção 3.1 -- nomeadamente as tabelas de campos com tipos, obrigatoriedade, valores por omissão e exemplos de pedido/resposta em formato Swagger -- foi elaborada com recurso a um modelo de linguagem de inteligência artificial (LLM). A ferramenta foi utilizada para analisar o código-fonte do ficheiro `Data_Server/app.py` e produzir documentação estruturada que permita a um utilizador externo ao projeto consumir a API sem necessidade de consultar diretamente o código. Toda a informação gerada foi verificada e validada contra a implementação real do sistema. O restante conteúdo do documento foi igualmente assistido por IA na sua redação e formatação.

<summary><strong>Prompt utilizado</strong></summary>

```
Analisa minuciosamente os ficheiros de código-fonte deste projeto académico de Computação
Distribuída. Gera documentação dos endpoints da API em formato Swagger-like, incluindo para
cada endpoint:

- Método HTTP e caminho (extraído dos decorators @app.route no app.py)
- Ação socket equivalente (extraída da função process_socket_request)
- Tabela de campos do request body com: nome do campo, tipo de dados, se é obrigatório
  ou opcional, valor por omissão quando aplicável, e descrição funcional
- Exemplo completo de request body em JSON
- Tabela de respostas possíveis com código HTTP e corpo JSON

Especifica todos os campos opcionais de forma explícita para que alguém externo ao projeto
consiga utilizar a API sem consultar o código-fonte. Baseia-te exclusivamente no código
existente nos ficheiros fornecidos, sem inventar funcionalidades que não estejam implementadas.
```

O ProjetoWeb-Docker implementa de forma bem-sucedida os principais princípios de desenvolvimento dos sistemas distribuídos modernos. Como resultado da decomposição do sistema em camadas, bem isoladas em contentores Docker, foi possível atingir um alto nível de desacoplamento, modularidade, manutenibilidade e escalabilidade. A arquitetura utiliza a abordagem clara de separação de responsabilidades, onde a frontend e backend (web-server) não comunicam diretamente com base de dados. Apenas intermediários usando o api-server com a comunicação através de um protocolo TCP e mensagens em formato JSON. Tal decisão mostra como os fluxos de baixo nível de dados podem ser integrados efetivamente com web frameworks alto nível (Flask). Também integramos IoT na fase 3 que complementa a arquitetura mostrando a possibilidade de coexistência das vários paradigmas da comunicação populares no ambiente atual usando o clássico modelo de pedido-resposta (HTTP e REST) e utilização a eventos de modelo publicação-subscrição.
Em resumo, o atual projeto garante a implementação prática de importantes conceitos de arquitetura de sistemas, isolamento de rede privada e sincronização, resistindo também a falhas usando políticas de restart e ordered healthchecks, resultando num sólido e escalável distribuído sistema.

---

**Unidade Curricular:** Computação Distribuída -- 2.o Ano da Licenciatura