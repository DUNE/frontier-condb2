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
    --mount=type=cache,target=/root/.cache/uv
    --mount=type=bind,source=uv.lock,target=uv.lock
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml
    uv python install 3.12 --compile-bytecode
    uv sync --no-install-project --compile-bytecode --no-editable
EOF

# Copy the project into the intermediate image
COPY . /app/condb2/server/

RUN <<EOF
    --mount=type=cache,target=/root/.cache/uv
    uv sync --locked --no-editable
EOF

FROM almalinux:9-minimal
COPY --from=ghcr.io/astral-sh/uv:0.10.9 /uv /uvx /bin/

WORKDIR /app
COPY --from=build /app/condb2/server ${WORKDIR}

RUN <<EOF
    export PATH=/root/.local/bin:$PATH
    uv python install 3.12 --compile-bytecode
EOF

ENV CON_DB_CFG="/app/dune_con_prod.yml"
ENV JINJA_TEMPLATES_LOCATION="/app"

CMD ["/app/.venv/bin/uwsgi", "uwsgi.ini"]
