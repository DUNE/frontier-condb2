FROM almalinux:9 as build
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

ARG CONDB2_SERVICE_PORT=${CONDB2_SERVICE_PORT}
ARG APP_HOME=/app
ARG SERVER_HOME=${APP_HOME}/condb2/server/

WORKDIR ${APP_HOME}

RUN <<EOF
    dnf update -y
    dnf install git -y
    dnf group install "Development Tools" -y
    dnf clean all
    git clone https://github.com/fermisda/condb2.git
    git clone https://github.com/fermisda/wsdbtools.git
    cp -R ${APP_HOME}/wsdbtools/wsdbtools ${SERVER_HOME}
EOF

WORKDIR ${SERVER_HOME}
COPY ["dune_con_prod.yml", "pyproject.toml", "README.md", "uwsgi.ini", "${WORKDIR}"]

RUN <<EOF
    sed -i "s/<CONDB2_SERVICE_PORT>/${CONDB2_SERVICE_PORT}/" ${SERVER_HOME}/uwsgi.ini
    export PATH=/root/.local/bin:$PATH
    uv python install 3.12 --compile-bytecode
    uv sync --no-install-project --compile-bytecode --no-editable
EOF

# Copy the project into the intermediate image
COPY . ${WORKDIR}

RUN uv sync --locked --no-editable

FROM almalinux:9-minimal
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/
LABEL org.opencontainers.image.source=https://github.com/DUNE/frontier-condb2

ARG APP_HOME=/app
ARG SERVER_HOME=${APP_HOME}/condb2/server/
ENV CON_DB_CFG=${APP_HOME}/dune_con_prod.yml
ENV JINJA_TEMPLATES_LOCATION=${APP_HOME}

WORKDIR ${APP_HOME}
COPY --from=build ${SERVER_HOME} ${WORKDIR}

RUN <<EOF
    export PATH=/root/.local/bin:$PATH
    uv python install 3.12 --compile-bytecode
EOF

CMD ["/app/.venv/bin/uwsgi", "uwsgi.ini"]
