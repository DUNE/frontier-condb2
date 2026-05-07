FROM docker.io/almalinux/9-init:latest
LABEL org.opencontainers.image.source=https://github.com/DUNE/frontier-condb2

ARG APP_STORAGE
ARG CONDB2_SERVICE_PORT
ARG CONDB2_SERVICE_URL
ARG FRONTIER_REL
ARG FRONTIER_GROUP
ARG FRONTIER_USER

RUN <<EOF
    groupadd -g 1000 ${FRONTIER_GROUP}
    useradd -u 1000 -g ${FRONTIER_GROUP} --system --no-create-home --shell /usr/sbin/nologin ${FRONTIER_USER}
    mkdir -p /etc/cron.d/
    mkdir -p /etc/squid/
    mkdir -p /etc/tomcat/
EOF

COPY customize.sh squidconf /etc/squid/
COPY frontier-squid /etc/sysconfig/
COPY servlets.conf servlets.passwd tomcat.conf /etc/tomcat/

# Install and configure the Frontier "launchpad" server stack.
RUN <<EOF
    export FRONTIER_GROUP=${FRONTIER_GROUP}
    export FRONTIER_USER=${FRONTIER_USER}

    mkdir -p ${APP_STORAGE}/cache/squid
    mkdir -p ${APP_STORAGE}/logs/squid
    mkdir -p ${APP_STORAGE}/logs/tomcat
    chown -R ${FRONTIER_USER}:${FRONTIER_GROUP} ${APP_STORAGE}

    sed -i "s+<APP_STORAGE>+${APP_STORAGE}+" /etc/squid/customize.sh
    sed -i "s/FRONTIER_USER=<FRONTIER_USER>/FRONTIER_USER=${FRONTIER_USER}/" /etc/squid/squidconf
    sed -i "s/FRONTIER_GROUP=<FRONTIER_GROUP>/FRONTIER_GROUP=${FRONTIER_GROUP}/" /etc/squid/squidconf
    sed -i "s/<CONDB2_SERVICE_URL>:<CONDB2_SERVICE_PORT>/${CONDB2_SERVICE_URL}:${CONDB2_SERVICE_PORT}/" \
        /etc/tomcat/servlets.conf
    sed -i "s+<APP_STORAGE>+${APP_STORAGE}+" /etc/tomcat/tomcat.conf
    sed -i "s/FRONTIER_USER=<FRONTIER_USER>/FRONTIER_USER=${FRONTIER_USER}/" /etc/tomcat/tomcat.conf
    sed -i "s/FRONTIER_GROUP=<FRONTIER_GROUP>/FRONTIER_GROUP=${FRONTIER_GROUP}/" /etc/tomcat/tomcat.conf

    dnf -y update
    rpm -Uvh --replacefiles ${FRONTIER_REL}
    dnf install -y initscripts chkconfig frontier-tomcat frontier-squid sudo
    dnf clean all

    chown -R ${FRONTIER_USER}:${FRONTIER_GROUP} /etc/squid
    chown -R ${FRONTIER_USER}:${FRONTIER_GROUP} /etc/tomcat
    chmod a+x /etc/squid/customize.sh
    chmod 600 /etc/tomcat/*

    systemctl enable frontier-tomcat
    systemctl enable frontier-squid
EOF

CMD [ "/usr/sbin/init" ]
