#!/usr/bin/bash
#
# Edit customize.sh as you wish to customize squid.conf.
# It will not be overwritten by upgrades.
# See customhelps.awk for information on predefined edit functions.
# In order to test changes to this, run this to regenerate squid.conf:
#       /usr/libexec/squid/frontier-squid
# and to reload the changes into a running squid use
#       systemctl reload frontier-squid
# Avoid single quotes in the awk source or you have to protect them from bash.
#

HOSTNAME=`hostname`

awk --file `dirname $0`/customhelps.awk --source '{
setoption("acl NET_LOCAL src", "10.0.0.0/8 172.16.0.0/12 192.168.0.0/16 fc00::/7 fe80::/10")
setoption("cache_mem", "128 MB")
setoptionparameter("cache_dir", 3, "10000")

setoption("http_port", "8000 accel defaultsite=127.0.0.1:8080 no-vhost")
setoption("cache_peer", "127.0.0.1 parent 8080 0 no-query originserver name=tomcat")
commentout("acl NET_LOCAL src")
commentout("http_access allow NET_LOCAL")
insertline("^http_access deny all", "http_access allow to_localhost")
setoption("read_ahead_gap", "200 MB")
setoption("shutdown_lifetime", "0 seconds")

setoption("cache_log", "<APP_STORAGE>/logs/squid/cache.log")
setoption("coredump_dir", "<APP_STORAGE>/cache/squid")
setoptionparameter("cache_dir", 2, "<APP_STORAGE>/cache/squid")
setoptionparameter("access_log", 1, "daemon:<APP_STORAGE>/logs/squid/access.log")

print
}'
