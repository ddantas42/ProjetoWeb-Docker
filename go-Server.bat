@echo off

set FLASK_APP=site\Server.py

set FLASK_BIN=.env\Scripts\flask

echo Iniciando o servidor...
%FLASK_BIN% run --port 80 --host="0.0.0.0"

if %errorlevel% neq 0 (
    echo Houve um erro ao iniciar o servidor.
) else (
    start http://localhost
)

pause