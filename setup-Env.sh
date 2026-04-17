 #!/bin/bash

PYTHON_BIN=python3

Directory_PythonEnv=.env

echo "ReCreating Python environment..."
${PYTHON_BIN} -m venv ${Directory_PythonEnv}

echo "Activating the Python environment..."
${Directory_PythonEnv}/bin/pip install Flask Flask-Session Flask-Mail flask-sqlalchemy
