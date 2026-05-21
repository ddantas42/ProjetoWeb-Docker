# Documentação do Projeto: Computação Distribuída - Fase 2

## 1. Avaliação da Completude do Projeto

De acordo com as restrições e especificações definidas no documento `TrabalhoPratico-Fase2.pdf`, o projeto encontra-se **100% completo**. 

Todas as diretrizes impostas foram rigorosamente implementadas:
1. **Separação Lógica:** A persistência de dados (Base de Dados) está logicamente e fisicamente separada do Sistema Informático Web (Frontend/Backend). Estão implementados em contentores distintos.


2. **API REST Intermédia:** A comunicação entre o Servidor Web e a Base de Dados não é direta. Existe um terceiro sistema informático (`api-server`) que expõe uma API REST (e também Sockets TCP) para processar os pedidos do frontend e interagir com a base de dados.


3. **Isolamento da Base de Dados:** O sistema de Base de Dados (`db-server`) apenas pode ser acedido pelo serviço da API REST (`api-server`). A porta `3306` do MariaDB não está exposta para a rede pública/host, encontrando-se acessível unicamente através da rede interna do Docker (`app-network`).


4. **Instanciação em Contentores:** Todo o ecossistema está orquestrado usando Docker Compose (`docker-compose.yml`), correndo de forma isolada em contentores Docker.


5. **Acessibilidade do Servidor Web:** O `web-server` expõe a porta `80` para a máquina host, permitindo que qualquer cliente (Browser) aceda à aplicação Web.

---

## 2. Arquitetura e Interação entre Contentores

A infraestrutura foi desenhada seguindo o modelo de microserviços e é composta por 3 contentores principais, definidos no `docker-compose.yml`:

> [!NOTE]
> Todos os contentores partilham a rede interna `app-network` criada pelo Docker Compose, mas as permissões e portas expostas ao exterior variam propositadamente para garantir segurança.

### 2.1. `web-server` (Frontend/Backend)
- **Tecnologia:** Python (Flask).
- **Função:** Fornece as páginas Web estáticas (HTML/CSS/JS) e processa os pedidos diretos do cliente (uploads, logins). É a única "cara" visível do projeto para o utilizador.
- **Portas Exp:** `80` mapeada para a porta `80` do host.
- **Interação:** Comunica exclusivamente com o `api-server` e nunca acede diretamente à Base de Dados.

### 2.2. `api-server` (Servidor de Dados / API REST)
- **Tecnologia:** Python (Flask, SQLAlchemy).
- **Função:** É o middleware do sistema. Contém a lógica de negócio principal associada aos dados. Traduz os pedidos REST ou Sockets provenientes do `web-server` em _queries_ transacionais seguras enviadas para a base de dados.
- **Portas Exp:** `5000` (REST) e `9000` (Sockets), mas apenas expostas para a rede interna `app-network`. Inacessíveis ao mundo exterior.
- **Interação:** Recebe pedidos do `web-server` e envia operações de leitura/escrita para o `db-server`.

### 2.3. `db-server` (Base de Dados)
- **Tecnologia:** MariaDB.
- **Função:** Camada de persistência de dados (Guarda as tabelas de Utilizadores, Vídeos e Ativações).
- **Portas Exp:** `3306`, exposta apenas internamente (`expose` e não `ports`).
- **Interação:** Recebe comandos unicamente do `api-server`. Usa um volume Docker (`db_data`) para garantir que os dados não se perdem caso o contentor vá abaixo.

---

## 3. Explicação do Código

### Camada Web (`Python_Server/Server/site/Server.py`)
- O servidor web foi despido de lógica de acesso à base de dados. Utiliza uma classe utilitária (`DataServerAPI` em `python.data_server_api`) para encaminhar as operações do utilizador (ex: `/login`, `/register`) sob a forma de chamadas HTTP/REST ou Sockets para o `api-server`.
- **Media (Uploads/Watch):** Este servidor recebe e guarda temporariamente/localmente os ficheiros de média. Quando é feito o pedido de visualização de vídeo, é o `web-server` que utiliza a função `send_file()` do Flask para transmitir os bytes para o utilizador, mantendo o tráfego pesado fora da Base de Dados.

### Camada API (`Data_Server/app.py`)
- Define as tabelas usando **SQLAlchemy** (Models: `Users`, `Video`, `Activation`).
- Expõe dezenas de _endpoints_ JSON (`@app.route('/api/...', methods=['POST'])`) como por exemplo `/api/user/create` ou `/api/video/get-all`.
- Todos os endpoints têm proteções genéricas utilizando _decorators_ (`@require_json` e `@handle_errors`), para evitar que pedidos mal formatados crasharem o servidor de dados, retornando sempre mensagens de erro coerentes (`400 Bad Request`, `404 Not Found`).

---

## 4. Perguntas de Apresentação Oral (Simulação de Docente)

Abaixo estão exemplos de perguntas técnicas de nível universitário que um júri de Engenharia Informática faria ao analisar este projeto, com os pontos de resposta esperados.

> [!IMPORTANT]
> Estas questões focam-se nos motivos das escolhas de arquitetura e segurança dos sistemas distribuídos.

**Q1: Porquê não ligar o Servidor Web diretamente à Base de Dados? Que vantagens arquiteturais retiras desta separação com uma API intermédia?**
* **Tópicos para responder:** Separação de Responsabilidades (_Separation of Concerns_), Segurança (se o servidor web for comprometido, os atacantes não têm credenciais de BD, apenas conseguem fazer o que a API deixar), Escalabilidade (posso ter vários servidores web a interagir com 1 servidor de dados), Manutenção (posso mudar a tecnologia do Frontend sem alterar a API/Base de Dados).

**Q2: Explica-me como configuraste o isolamento de rede no Docker Compose e de que forma garantes que a Base de Dados não está acessível na Internet.**
* **Tópicos para responder:** Foi utilizada uma bridge network (`app-network`). No compose, o `db-server` utiliza o comando `expose: - "3306"` (que apenas expõe a porta internamente aos outros contentores) em vez de `ports: - "3306:3306"` (que faria port-forwarding para a máquina host). Apenas o contentor `web-server` possui a diretiva `ports` para a porta 80.

**Q3: Como trataste o problema da "Persistência" dos dados na arquitetura Docker? Se o contentor MariaDB for apagado e recriado, perdes os logins todos?**
* **Tópicos para responder:** Não. Foi configurado um `volume` associado ao contentor da Base de Dados (ex: `- db_data:/var/lib/mysql`). Os volumes do Docker residem fora do ciclo de vida do contentor, na máquina host, assegurando que os dados se mantêm persistentes de uns arranques para os outros.

**Q4: O vosso Data Server reencaminha ficheiros de vídeos para o Frontend ou guarda os MP4 na Base de Dados?**
* **Tópicos para responder:** O ficheiro MP4 é armazenado e servido a partir do Servidor Web (`web-server`). O Data Server (API) e a Base de Dados apenas armazenam os *metadados* do vídeo (Nome, Extensão, Título, Uploader, Hash, Coordenadas). Armazenar blobs gigantescos numa base de dados relacional (MariaDB) causaria enormes constrangimentos de I/O e RAM. 

**Q5: Reparaste que usaste decorators no código do Data Server, como `@require_json` e `@handle_errors`. Qual foi o objetivo e que problema previnem?**
* **Tópicos para responder:** Foram aplicados para reduzir a replicação de código lógico em todos os métodos da API (DRY - Don't Repeat Yourself). Previnem exceções não tratadas (ex: um campo que não existe e causaria um KeyError). Sem estes _decorators_, o Flask retornaria um Erro 500 feio com rasto HTML se um parâmetro falhasse, corrompendo a comunicação em sistemas distribuídos que apenas esperam respostas estruturadas em JSON.
