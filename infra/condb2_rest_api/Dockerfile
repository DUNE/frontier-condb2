FROM almalinux:9 as builder

WORKDIR /app

RUN <<EOF
    dnf update -y
    dnf group install "Development Tools" -y
    dnf install git -y
    git clone https://github.com/fermisda/condb2.git
    git clone https://github.com/fermisda/wsdbtools.git
    cp -R /app/wsdbtools/wsdbtools /app/condb2/server/
    ls -alR /app/condb2/server/
    cd condb2
    dnf install python3-devel -y
    dnf clean all
    python3 --version
    pip3 --version
    pip3 install uwsgi pyyaml requests webpie jinja2
    pip3 install git+https://github.com/fermisda/condb2.git
EOF

COPY ["dune_con_prod.yml", "uwsgi.ini", "/app/condb2/server/"]

WORKDIR /app/condb2/server

ENV CON_DB_CFG="/app/condb2/server/dune_con_prod.yml"
ENV JINJA_TEMPLATES_LOCATION="/app/condb2/server"

CMD ["/usr/local/bin/uwsgi", "uwsgi.ini"]
