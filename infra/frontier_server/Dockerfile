FROM almalinux:9

ARG FRONTIER_REL
ARG FRONTIER_GROUP
ARG FRONTIER_USER

# Install and configure the Frontier "launchpad" server.
RUN <<EOF
    export FRONTIER_GROUP=${FRONTIER_GROUP}
    export FRONTIER_USER=${FRONTIER_USER}
    dnf -y update
    rpm -Uvh --replacefiles ${FRONTIER_REL}
    dnf install -y initscripts chkconfig frontier-tomcat frontier-squid
    dnf clean all
EOF

COPY customize.sh /etc/squid/
COPY frontier-squid /etc/sysconfig/
COPY servlets.conf servlets.passwd /etc/tomcat/

RUN <<EOF
    chmod a+x /etc/squid/customize.sh
    chown -R squid:tomcat /etc/squid
    chown -R tomcat:tomcat /etc/tomcat
    chmod 600 /etc/tomcat/*
    mkdir /home/tomcat
    chown -R tomcat:tomcat /home/tomcat
    systemctl enable frontier-tomcat
    systemctl enable frontier-squid
EOF

# Podman supports running systemd in a container.
# It will set up all of the correct mount points and run
# in a confined container when running the `init` command.
CMD [ "/usr/sbin/init" ]
