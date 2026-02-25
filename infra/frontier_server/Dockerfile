FROM frontier-server AS frontier-server
FROM almalinux:9

# Install and configure the Frontier "launchpad" server.
ARG FRONTIER_REL="https://frontier.cern.ch/dist/rpms/RPMS/noarch/frontier-release-1.3-1.noarch.rpm"

RUN <<EOF
    export FRONTIER_USER=tomcat
    export FRONTIER_GROUP=tomcat
    dnf -y update
    rpm -Uvh --replacefiles ${FRONTIER_REL}
    dnf install -y initscripts chkconfig frontier-tomcat frontier-squid
    dnf clean all
EOF

COPY --from=frontier-server customize.sh /etc/squid/
COPY --from=frontier-server frontier-squid /etc/sysconfig/
COPY --from=frontier-server servlets.conf servlets.passwd /etc/tomcat/

RUN <<EOF
    chown -R squid:tomcat /etc/squid
    chmod a+x /etc/squid/customize.sh
    chown -R tomcat:tomcat /etc/tomcat
    chmod 600 /etc/tomcat/*
    mkdir /home/tomcat
    chown -R tomcat:tomcat /home/tomcat
    systemctl enable frontier-tomcat
    systemctl enable frontier-squid
EOF

EXPOSE 8000

# Podman supports running systemd in a container.
# It will set up all of the correct mount points and run
# in a confined container by running `init` in the container.
CMD [ "/usr/sbin/init" ]
