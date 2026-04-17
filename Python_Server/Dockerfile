FROM ubuntu:latest

RUN apt-get update && apt-get install -y python3 python3-pip python3-venv

WORKDIR /Server

COPY ./Server/ /Server/

RUN bash /Server/setup-Env.sh

CMD ["bash", "/Server/go-Server.sh"]