# Fase 3 - Dashboard IoT

## Objetivo

Foi acrescentada ao projeto uma pagina de dashboard IoT para cumprir a Fase 3 do trabalho pratico.

O enunciado pede:

- uma interface de frontend para sensores/atuadores IoT;
- acesso a sensores por API REST;
- acesso a sensores por MQTT;
- cuidado com CORS;
- utilizacao do ambiente IoT apresentado nos slides `08-MQTT-IoT.pdf`.

## Ambiente IoT usado

Dos slides e do teste feito no browser, o sensor confirmado como disponivel e o Weather/AHT10:

- pagina visual: `https://cjsg.ddns.net:8443/weather/status.html`
- valores REST: `https://cjsg.ddns.net:8443/weather/values`
- posicao REST: `https://cjsg.ddns.net:8443/weather/position`
- topico MQTT previsto: `/weather`
- broker MQTT: `cjsg.ddns.net:1883`

O REST responde sem credenciais. O MQTT rejeita ligacao anonima com codigo `5`, ou seja, `not authorized`.
Como nao foram fornecidas credenciais MQTT, a dashboard mostra o estado MQTT como nao configurado.

## Arquitetura implementada

Antes:

```text
Browser -> web-server -> api-server -> db-server
```

Agora:

```text
Browser -> nginx -> web-server -> api-server -> db-server
                    |
                    +-> REST IoT Weather
                    +-> MQTT broker, quando houver credenciais
```

O Nginx passou a ser o unico servico exposto ao host na porta 80. O Flask web, a API interna e a base de dados ficam apenas dentro da rede Docker.

## Ficheiros criados

- `FASE3_IOT_DASHBOARD.md`
- `Nginx/nginx.conf`
- `Python_Server/Server/site/templates/dashboard.html`
- `Python_Server/Server/site/static/css/Dashboard.css`
- `Python_Server/Server/site/static/js/Dashboard.js`

## Ficheiros alterados

- `.env`
- `.env.example`
- `docker-compose.yml`
- `Python_Server/Server/requirements.txt`
- `Python_Server/Server/setup-Env.sh`
- `Python_Server/Server/site/Server.py`
- `Python_Server/Server/site/templates/home.html`

## Funcionalidades REST

Foi criada uma rota Flask para servir como proxy REST:

```text
GET /api/iot/rest/state
```

Essa rota chama:

```text
GET https://cjsg.ddns.net:8443/weather/values
GET https://cjsg.ddns.net:8443/weather/position
```

Isto evita problemas de CORS, porque o browser chama o proprio Flask e o Flask e que chama a API externa.

## Funcionalidades MQTT

Foi preparado um cliente MQTT no backend Flask com `paho-mqtt`.

Endpoint exposto para a dashboard:

```text
GET /api/iot/mqtt/latest
```

O cliente tenta subscrever o topico:

```text
/weather
```

No entanto, enquanto estas variaveis estiverem vazias, o MQTT fica intencionalmente inativo:

```env
IOT_MQTT_USER=
IOT_MQTT_PASSWORD=
```

Isto acontece porque o broker rejeita ligacoes anonimas.

## Variaveis de ambiente

Foram adicionadas ao `.env`:

```env
SECRET_KEY=change_me_in_production

IOT_REST_BASE_URL=https://cjsg.ddns.net:8443
IOT_REST_VERIFY_SSL=false
IOT_MQTT_HOST=cjsg.ddns.net
IOT_MQTT_PORT=1883
IOT_MQTT_USER=
IOT_MQTT_PASSWORD=
```

`IOT_REST_VERIFY_SSL=false` foi necessario porque o Python dentro do container nao valida corretamente a cadeia do certificado desse ambiente da UC.

## Dashboard

A pagina nova fica em:

```text
http://localhost/dashboard
```

Mostra:

- temperatura via REST;
- humidade via REST;
- uptime do sensor via REST;
- latitude/longitude via REST;
- estado MQTT;
- ultimo payload MQTT, quando houver credenciais;
- historico simples de temperatura, quando chegarem mensagens MQTT.

## Nginx

Foi criado um reverse proxy Nginx:

```text
Nginx/nginx.conf
```

Ele recebe pedidos em `http://localhost` e encaminha para o Flask web interno:

```text
nginx:80 -> web-server:80
```

No `docker-compose.yml`, so o Nginx publica porta no host:

```yaml
ports:
  - "80:80"
```

## Como correr

Abrir o Docker Desktop e correr:

```bash
make
```

Ou diretamente:

```bash
docker compose up --build
```

Depois abrir:

```text
http://localhost
http://localhost/dashboard
```

## Grafana

A dashboard criada no site e uma dashboard propria, inspirada no tipo de visualizacao do Grafana, mas nao instala Grafana.

Para concluir Grafana de forma correta seria preciso acrescentar:

1. um collector que le MQTT;
2. uma base de dados temporal, normalmente InfluxDB;
3. um servico Grafana no `docker-compose.yml`;
4. datasource Grafana ligado ao InfluxDB;
5. paineis para temperatura, humidade e uptime.

Sem credenciais MQTT, o Grafana tambem nao conseguiria recolher dados MQTT reais do broker da UC.

## Estado atual

Concluido:

- dashboard IoT integrada no site;
- proxy REST sem CORS;
- leitura REST do sensor Weather/AHT10;
- estrutura MQTT preparada;
- Nginx como entrada publica;
- configuracao por `.env`;
- validacao de sintaxe Python;
- validacao do `docker compose config`.

Pendente por depender de dados externos:

- credenciais MQTT reais;
- integracao Grafana com dados historicos reais.
