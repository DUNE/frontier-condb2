FROM almalinux:9 as build
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

WORKDIR /app

RUN <<EOF
    dnf update -y
    dnf install git -y
    dnf group install "Development Tools" -y
    dnf clean all
    git clone https://github.com/fermisda/condb2.git
    git clone https://github.com/fermisda/wsdbtools.git
    cp -R /app/wsdbtools/wsdbtools /app/condb2/server/
EOF

WORKDIR /app/condb2/server/
COPY ["dune_con_prod.yml", "pyproject.toml", "README.md", "uwsgi.ini", "${WORKDIR}"]

RUN <<EOF
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

WORKDIR /app
COPY --from=build /app/condb2/server ${WORKDIR}

RUN <<EOF
    export PATH=/root/.local/bin:$PATH
    uv python install 3.12 --compile-bytecode
EOF

ENV CON_DB_CFG="/app/dune_con_prod.yml"
ENV JINJA_TEMPLATES_LOCATION="/app"

CMD ["/app/.venv/bin/uwsgi", "uwsgi.ini"]
