FROM docker.io/almalinux:9 as build
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

ARG APP_HOME=/app
ARG APP_STORAGE
ARG CONDB2_SERVICE_PORT
ARG FRONTIER_GROUP
ARG FRONTIER_USER
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

    groupadd -g 1000 ${FRONTIER_GROUP}
    useradd -u 1000 -g ${FRONTIER_GROUP} ${FRONTIER_USER}
    chown -R ${FRONTIER_USER}:${FRONTIER_GROUP} ${APP_HOME}
EOF

WORKDIR ${SERVER_HOME}
COPY ["dune_runcon_prod.yaml", "pyproject.toml", "README.md", "uwsgi.ini", "${WORKDIR}"]
# COPY ["dune_con_prod.local.yml", "pyproject.toml", "README.md", "uwsgi.ini", "${WORKDIR}"]

USER ${FRONTIER_USER}

RUN <<EOF
    sed -i "s+<APP_STORAGE>+${APP_STORAGE}+" ${SERVER_HOME}/uwsgi.ini
    sed -i "s+<CONDB2_SERVICE_PORT>+${CONDB2_SERVICE_PORT}+" ${SERVER_HOME}/uwsgi.ini

    export PATH=/home/${FRONTIER_USER}/.local/bin:${PATH}
    uv python install 3.12 --compile-bytecode
    uv sync --no-install-project --compile-bytecode --no-editable
    uv sync --locked --no-editable
EOF

FROM docker.io/almalinux:9-minimal
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/
LABEL org.opencontainers.image.source=https://github.com/DUNE/frontier-condb2

ARG APP_HOME=/app
ARG FRONTIER_GROUP
ARG FRONTIER_USER
ARG SERVER_HOME=${APP_HOME}/condb2/server/
ENV CON_DB_CFG=${APP_HOME}/dune_runcon_prod.yaml
# ENV CON_DB_CFG=${APP_HOME}/dune_con_prod.local.yml
ENV JINJA_TEMPLATES_LOCATION=${APP_HOME}

WORKDIR ${APP_HOME}
COPY --from=build ${SERVER_HOME} ${WORKDIR}

RUN <<EOF
    groupadd -g 1000 ${FRONTIER_GROUP}
    useradd -u 1000 -g ${FRONTIER_GROUP} ${FRONTIER_USER}
    chown -R ${FRONTIER_USER}:${FRONTIER_GROUP} ${APP_HOME}
EOF

USER ${FRONTIER_USER}

RUN <<EOF
    export PATH=/home/${FRONTIER_USER}/.local/bin:${PATH}
    uv python install 3.12 --compile-bytecode
EOF

CMD ["/app/.venv/bin/uwsgi", "uwsgi.ini"]
