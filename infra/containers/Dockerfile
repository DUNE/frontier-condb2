FROM infra-config AS infra-config
FROM almalinux:9

RUN dnf -y update

# Install and configure the Frontier "launchpad" server.
ARG FRONTIER_REL="https://frontier.cern.ch/dist/rpms/RPMS/noarch/frontier-release-1.3-1.noarch.rpm"

RUN rpm -Uvh --replacefiles ${FRONTIER_REL} && \
    dnf install -y initscripts chkconfig frontier-tomcat && \
    dnf clean all

COPY --from=infra-config * /etc/tomcat/
RUN chown -R tomcat:tomcat /etc/tomcat && \
    chmod 600 /etc/tomcat/* && \
    mkdir /home/tomcat && \
    chown -R tomcat:tomcat /home/tomcat && \
    systemctl enable frontier-tomcat

EXPOSE 8080

# Podman supports running systemd in a container.
# It will set up all of the correct mount points and run
# in a confined container by running `init` in the container.
CMD [ "/usr/sbin/init" ]
