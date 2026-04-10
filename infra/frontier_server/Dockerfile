FROM almalinux:9
LABEL org.opencontainers.image.source=https://github.com/DUNE/frontier-condb2

ARG APP_STORAGE=${APP_STORAGE}
ARG CONDB2_SERVICE_PORT=${CONDB2_SERVICE_PORT}
ARG CONDB2_SERVICE_URL=${CONDB2_SERVICE_URL}
ARG FRONTIER_REL=${FRONTIER_REL}
ARG FRONTIER_GROUP=${FRONTIER_GROUP}
ARG FRONTIER_USER=${FRONTIER_USER}

# Install and configure the Frontier "launchpad" server stack.
RUN <<EOF
    export FRONTIER_GROUP=${FRONTIER_GROUP}
    export FRONTIER_USER=${FRONTIER_USER}
    useradd -g ${FRONTIER_GROUP} ${FRONTIER_USER}
    dnf -y update
    rpm -Uvh --replacefiles ${FRONTIER_REL}
    dnf install -y initscripts chkconfig frontier-tomcat frontier-squid
    dnf clean all
EOF

COPY customize.sh squidconf /etc/squid/
COPY frontier-squid /etc/sysconfig/
COPY servlets.conf servlets.passwd tomcat.conf /etc/tomcat/

RUN <<EOF
    sed -i "s+<APP_STORAGE>+${APP_STORAGE}+" /etc/squid/customize.sh
    sed -i "s/FRONTIER_USER=<FRONTIER_USER>/FRONTIER_USER=${FRONTIER_USER}/" /etc/squid/squidconf
    sed -i "s/FRONTIER_GROUP=<FRONTIER_GROUP>/FRONTIER_GROUP=${FRONTIER_GROUP}/" /etc/squid/squidconf
    sed -i "s+<CONDB2_SERVICE_URL>:<CONDB2_SERVICE_PORT>+${CONDB2_SERVICE_URL}:${CONDB2_SERVICE_PORT}+" \
        /etc/tomcat/servlets.conf
    sed -i "s+<APP_STORAGE>+${APP_STORAGE}+" /etc/tomcat/tomcat.conf
    sed -i "s/FRONTIER_USER=<FRONTIER_USER>/FRONTIER_USER=${FRONTIER_USER}/" /etc/tomcat/tomcat.conf
    sed -i "s/FRONTIER_GROUP=<FRONTIER_GROUP>/FRONTIER_GROUP=${FRONTIER_GROUP}/" /etc/tomcat/tomcat.conf

    awk 1 /etc/squid/customize.sh
    awk 1 /etc/squid/squidconf
    awk 1 /etc/tomcat/servlets.conf
    awk 1 /etc/tomcat/tomcat.conf

    chmod a+x /etc/squid/customize.sh
    chown -R ${FRONTIER_USER}:${FRONTIER_GROUP} /etc/squid
    chown -R ${FRONTIER_USER}:${FRONTIER_GROUP} /etc/tomcat
    chmod 600 /etc/tomcat/*
    mkdir /home/tomcat
    chown -R ${FRONTIER_USER}:${FRONTIER_GROUP} /home/tomcat
    systemctl enable frontier-tomcat
    systemctl enable frontier-squid
EOF

# Podman supports running systemd in a container.
# It will set up all of the correct mount points and run
# in a confined container when running the `init` command.
CMD [ "/usr/sbin/init" ]
