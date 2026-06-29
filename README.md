# Frontier / ConDB2 API Integration

This repository contains the code and documentation related to the installation, configuration, and testing of a Frontier (server, client, cache) connection to a ConDB2 API server backend.

## FermiCloud Instance Setup

### Getting FermiCloud Access

- Submit a ticket for [Access to FermiCloud](https://fermi.servicenowservices.com/wp?id=evg_sc_cat_item&sys_id=35d4f481f98c7800a72dc20d261a4e7f)
- [FermiCloud OpenStack Docs](https://fifewiki.fnal.gov/wiki/FermiCloud_Openstack)

### Connecting to the FermiCloud OpenStack Dashboard

- You will need to either be on the local FNAL network or use a remote VPN (`vpn.fnal.gov`) connection.
  - Follow the [instructions](https://fermi.servicenowservices.com/wp?id=evg-kb-article&sys_id=567a699a1b73f0104726a8efe54bcbe3) appropriate to the system you are working on.
  - This requires installing Fermilab CA certificates.
  - The remote VPN connection requires that use the RSA Authenticator app to get a token. This requires creating a ticket to create a PIN to authenticate.
  - You will also need to use your FNAL Services credentials to connect to the VPN.
- [FermiCloud OpenStack Dashboard](https://fcl2104.fnal.gov/dashboard)
  - Dashboard authentication requires your FNAL Services credentials.

### Creating a New FermiCloud Instance

- **Note: FermiCloud instances are meant only for development and testing purposes. Production workloads are not supported.**
- Follow the [How to Start a New FermiCloud Instance](https://fifewiki.fnal.gov/wiki/How_to_Start_a_New_FermiCloud_Instance).
- For the **"Source"** image choose the most recently updated AlmaLinux 9 version with NFS.
- In **"Flavor"** select the 2 VCPU / 4GB RAM / 30GB option. *Note: This configuration mirrors Dave Dykstra's Frontier FermiCloud instance.*
- Select `ipv4` for the **"Network"** option. This makes instance access and network configuration easier.

### Accessing the Newly Created Instance

- The `mclymer-frontier-test` instance URL: `fermicloud725.fnal.gov`
- Make sure that you have [Kerberos configured](https://dune.github.io/computing-basics/setup) for SSH access to your instance.
  - Follow the instructions to generate a Kerberos ticket.
  - If remote, you will need to be connected to the VPN to `ssh` into you FermiCloud instance.
- To update system libraries and install software you will need root access permissions.
  - `sudo` does not work on FermiCloud VMs.
  - SSH into the VM directly for root access: `ssh -l root fermicloud725.fnal.gov`
  - There was an issue with being added to the correct group for root access. Needed `/root/.k5login` modified to give me access.

## Frontier "Launchpad" Server Setup on FermiCloud Test Instance

### Relevant Documentation
- [Frontier Distributed Database Caching System Overview](https://twiki.cern.ch/twiki/bin/view/Frontier/FrontierOverview)
- [Installing frontier-tomcat](https://twiki.cern.ch/twiki/bin/view/Frontier/FrontierOverview)

### Installation

- Follow the above linked installation document.
- Do not make any of the changes detailed in the "Preparation" section.
- Follow all of the steps in the "Installation" section, but substitute the `dnf` command in for `yum`.
- Before you run `[root@fermicloud725 ~]# systemctl enable frontier-tomcat` do the following:
  - As root user, you need to install `initscripts` and `chkconfig`.
    ```console
    [root@fermicloud725 ~]# dnf install initscripts chkconfig
    ```

### Configuration

- Add the following configuration to `/etc/tomcat/servlets.conf`
  ```properties
  [dune_runcon_prod]
  LongCacheExpireSeconds: 300
  ShortCacheExpireSeconds: 300
  MaxDbAcquireSeconds: 300
  MaxThreads: 5
  FileBaseDirectory: https://dbdata0vm.fnal.gov:9443/dune_runcon_prod/
  ```
- Before you run `[root@fermicloud725 ~]# systemctl start frontier-tomcat`:
  - You will need to run - `ln -s /etc/rc.d/init.d /etc/init.d` to make sure that it can find the correct startup script.
  - The `frontier-tomcat` installation creates the `tomcat` user and group, but not the associated `/home` directory.
  - Create the required directory:
    ```console
    [root@fermicloud725 ~]# mkdir /home/tomcat
    [root@fermicloud725 ~]# chown -R tomcat:tomcat /home/tomcat
    ```

- A network security group needs to be created to allow IPv4 and IPv6 ingress access to port 8080.
  - This allows for requests to be handled by the `frontier-tomcat` servlet.
  - In the OpenStack dashboard go to `Network > Security Groups`.
    - Click the "Create Security Group" button.
    ![Alt text](./docs/images/create_sec_group.png "Create Security Group Button")
    - Give the group a name and optional description. We used `internal-tomcat`.
    - Once the security group has been created, delete the "Egress" rules.
    - Then add two "Ingress" rules; one for IPv4 and one for IPv6.
    ![Alt text](./docs/images/sec_group_rules.png "Security Group Rules")
  - This security group now needs to be added to your FermiCloud instance.
    - Find your instance on the "Instances" view.
    - Select "Edit Security Groups" from the "Actions" dropdown menu.
    ![Alt text](./docs/images/edit_sec_group.png "Edit Instance Security Groups")
    - Add the security group to the list of "Instance Security Groups and save it.
    ![Alt text](./docs/images/add_instance_sec_group.png "Instance Security Groups")

### Connection Testing

- Test the connection between your `frontier-tomcat` setup and the ConDB2 API backend.
  - **Note: You will need to be on the FNAL network to run the test. See the above VPN connection details.**
  - The server should be listening on port 8080 at the domain name created for your FermiCloud instance.
  - In a terminal on a separate system, run a query to the ConDB2 API, proxied by the connected Frontier server.
  ```console
  $ curl -H "Accept: application/xml" -H "X-Frontier-Id: test" "http://fermicloud725.fnal.gov:8080/dune_runcon_prod/Frontier/type=frontier_file:1:DEFAULT&encoding=BLOB&p1=get%253ffolder%253dpdunesp.test%2526t%253d23300"
  <?xml version="1.0" encoding="US-ASCII"?>
  <!DOCTYPE frontier SYSTEM "http://frontier.fnal.gov/frontier.dtd">
  <frontier version="3.42" xmlversion="1.0">
   <transaction payloads="1">
    <payload type="frontier_file" version="1" encoding="BLOB">
     <data>BgAAAM9jaGFubmVsLHR2LHRyLGRhdGFfdHlwZSx1cGxvYWRfdGltZSxzdGFydF90aW1lLHN0b3Bf
  dGltZSxydW5fdHlwZSxzb2Z0d2FyZV92ZXJzaW9uLGJ1ZmZlcixhY19jb3VwbGUKMCwyMzMwMC4w
  LDE3MDAwNjc0MDYuOTcyODkwMSxucDAyX2NvbGRib3gsMTcwMDA2NzQwNi45NzI4NjQ2LDE3MDAw
  Njc4MDMuMCxOb25lLFRFU1QsZmQtdjQuMi4wLWM2LE5vbmUsTm9uZQoH</data>
     <quality error="0" md5="3437dff6878ab524247531f6742ee8f9" records="1" full_size="213"/>
    </payload>
   </transaction>
  </frontier>
  ```

## Frontier Squid Reverse Proxy Setup on FermiCloud Test Instance

- The relevant documentation can be found here: [Installing Squid for a Frontier launchpad](https://twiki.cern.ch/twiki/bin/view/Frontier/InstallSquidForLaunchpad)

### Set the User Group ID

- The `frontier-tomcat` install was done with the `tomcat` user and group IDs.
- The [docs](https://twiki.cern.ch/twiki/bin/view/Frontier/InstallSquidForLaunchpad#Preparation) recommend that the same user and group ID be used.
  ```console
  [root@fermicloud725 ~]# export FRONTIER_USER=tomcat
  [root@fermicloud725 ~]# export FRONTIER_GROUP=tomcat
  ```

### Squid Reverse Proxy Installation

- Install `frontier-squid`.
  ```console
  [root@fermicloud725 ~]# dnf install frontier-squid -y
  ```
- Set it to start at boot time.
  ```console
  [root@fermicloud725 ~]# systemctl enable frontier-squid
  ```

### Configuration

- Follow the configuration instructions from the documentation, but also edit `/etc/squid/customize.sh` to reflect the following.
  ```bash
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

  print
  }'
  ```

### Connection Testing

- Test the connection between your `frontier-squid` reverse proxy setup and the `frontier-tomcat` server.
  - **Note: You will need to be on the FNAL network to run the test. See the above VPN connection details.**
  - The reverse proxy should be listening on port 8000 at the domain name created for your FermiCloud instance.
  - In a terminal on a separate system, run a query to the ConDB2 API, proxied by the connected Frontier server.
  ```console
  $ curl -H "Accept: application/xml" -H "X-Frontier-Id: test" "http://fermicloud725.fnal.gov:8000/dune_runcon_prod/Frontier/type=frontier_file:1:DEFAULT&encoding=BLOB&p1=get%253ffolder%253dpdunesp.test%2526t%253d23300"
  <?xml version="1.0" encoding="US-ASCII"?>
  <!DOCTYPE frontier SYSTEM "http://frontier.fnal.gov/frontier.dtd">
  <frontier version="3.42" xmlversion="1.0">
   <transaction payloads="1">
    <payload type="frontier_file" version="1" encoding="BLOB">
     <data>BgAAAM9jaGFubmVsLHR2LHRyLGRhdGFfdHlwZSx1cGxvYWRfdGltZSxzdGFydF90aW1lLHN0b3Bf
  dGltZSxydW5fdHlwZSxzb2Z0d2FyZV92ZXJzaW9uLGJ1ZmZlcixhY19jb3VwbGUKMCwyMzMwMC4w
  LDE3MDAwNjc0MDYuOTcyODkwMSxucDAyX2NvbGRib3gsMTcwMDA2NzQwNi45NzI4NjQ2LDE3MDAw
  Njc4MDMuMCxOb25lLFRFU1QsZmQtdjQuMi4wLWM2LE5vbmUsTm9uZQoH</data>
     <quality error="0" md5="3437dff6878ab524247531f6742ee8f9" records="1" full_size="213"/>
    </payload>
   </transaction>
  </frontier>
  ```

## Frontier Squid Cache Setup on a Local Workstation

### Relevant Documentation
- [Installing a Frontier squid cache server](https://twiki.cern.ch/twiki/bin/view/Frontier/InstallSquid)

### Installation

- Follow the above linked installation document.
- Do not make any of the changes detailed in the "Preparation" section.

### Configuration

- Follow the configuration instructions from the documentation, including [Personal squid on a desktop/laptop
](https://twiki.cern.ch/twiki/bin/view/Frontier/InstallSquid#Personal_squid_on_a_desktop_lapt), but also edit `/etc/squid/customize.sh` to reflect the following.
  ```bash
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

  awk --file `dirname $0`/customhelps.awk --source '{
  setoption("acl NET_LOCAL src", "127.0.0.1/32")
  setoption("cache_mem", "256 MB")
  setoptionparameter("cache_dir", 3, "10000")
  print
  }'
  ```

### Testing the Cache

- As a first test, follow the [Testing the installation](https://twiki.cern.ch/twiki/bin/view/Frontier/InstallSquid#Testing_the_installation) instructions.
  - Make sure to replace `MY.SQUID.HOST` with `localhost` for the first `export` command.
    ```console
    $ export http_proxy=http://localhost:3128
    ```
  - If you run the `wget` command twice as instructed, you should see something like the following in `/var/log/squid/access.log`.
    ```log
    127.0.0.1 - - [03/Dec/2025:12:42:15.010 -0700] "GET http://frontier.cern.ch/ HTTP/1.1" 200 10139 TCP_MISS:HIER_DIRECT 745 "- -" "-" "Wget/1.21.1"
    127.0.0.1 - - [03/Dec/2025:12:43:05.277 -0700] "GET http://frontier.cern.ch/ HTTP/1.1" 200 10140 TCP_HIT:HIER_NONE 0 "- -" "-" "Wget/1.21.1"
    ```
- Test the connection between your local `frontier-squid` cache installation and the Frontier Launchpad server that you set up previously.
  - **Note: You will need to be on the FNAL network to run the test. See the above VPN connection details.**
  - The server should be listening on port 8000 at the domain name created for your FermiCloud instance.
  - In a terminal on a the local system, run a query to the ConDB2 API. Do this twice to see the cache miss and then hit.
  ```console
  $ curl -H "Accept: application/xml" -H "X-Frontier-Id: test" "http://fermicloud725.fnal.gov:8000/dune_runcon_prod/Frontier/type=frontier_file:1:DEFAULT&encoding=BLOB&p1=get%253ffolder%253dpdunesp.test%2526t%253d23300"
  <?xml version="1.0" encoding="US-ASCII"?>
  <!DOCTYPE frontier SYSTEM "http://frontier.fnal.gov/frontier.dtd">
  <frontier version="3.42" xmlversion="1.0">
   <transaction payloads="1">
    <payload type="frontier_file" version="1" encoding="BLOB">
     <data>BgAAAM9jaGFubmVsLHR2LHRyLGRhdGFfdHlwZSx1cGxvYWRfdGltZSxzdGFydF90aW1lLHN0b3Bf
  dGltZSxydW5fdHlwZSxzb2Z0d2FyZV92ZXJzaW9uLGJ1ZmZlcixhY19jb3VwbGUKMCwyMzMwMC4w
  LDE3MDAwNjc0MDYuOTcyODkwMSxucDAyX2NvbGRib3gsMTcwMDA2NzQwNi45NzI4NjQ2LDE3MDAw
  Njc4MDMuMCxOb25lLFRFU1QsZmQtdjQuMi4wLWM2LE5vbmUsTm9uZQoH</data>
     <quality error="0" md5="3437dff6878ab524247531f6742ee8f9" records="1" full_size="213"/>
    </payload>
   </transaction>
  </frontier>
  ```
- You should now see something like the following in `/var/log/squid/access.log`.
  ```log
  127.0.0.1 - - [03/Dec/2025:14:00:05.148 -0700] "GET http://fermicloud725.fnal.gov:8000/dune_runcon_prod/Frontier/type=frontier_file:1:DEFAULT&encoding=BLOB&p1=get%253ffolder%253dpdunesp.test%2526t%253d23300 HTTP/1.1" 200 1090 TCP_MISS:HIER_DIRECT 370 "test -" "-" "curl/7.76.1"
  127.0.0.1 - - [03/Dec/2025:14:00:26.785 -0700] "GET http://fermicloud725.fnal.gov:8000/dune_runcon_prod/Frontier/type=frontier_file:1:DEFAULT&encoding=BLOB&p1=get%253ffolder%253dpdunesp.test%2526t%253d23300 HTTP/1.1" 200 1091 TCP_HIT:HIER_NONE 0 "test -" "-" "curl/7.76.1"
  ```

## Local Frontier Client Build and Basic Query Testing

***Note: The Frontier client code build was done using GCC 14.2.1 on an AlmaLinux 9 system. The following reflects the system configuration needed to build the code.***

### Local Client Code Build

- Follow the instructions found in [Frontier Client Usage](https://frontier.cern.ch/dist/FrontierClientUsage.html).
- Steps that deviate from the above documentation are noted below.
- In a local working directory fetch the latest Frontier code:
  ```console
  $ git clone https://github.com/fermitools/frontier.git
  ```
- Install the following build dependencies (if not already installed):
  ```console
  $ sudo dnf install openssl-devel
  $ sudo dnf install zlib-devel
  $ sudo dnf install expat expat-devel
  ```
- There is not a prebuilt [Pacparser](https://github.com/manugarg/pacparser) package for RHEL / AL9.
  - You will need to download the source, then [build and install it locally](https://github.com/manugarg/pacparser/blob/main/INSTALL).
    ```console
    $ git clone https://github.com/manugarg/pacparser
    ```
  - To build it with GCC 14+, you will need to manually patch the `/<LOCALLY_CLONED_WORKING_DIR>/src/spidermonkey/js/src/jsapi.c` according to the instructions [found here](https://github.com/manugarg/pacparser/issues/194#issuecomment-2262030966).
  - Build and install locally:
    ```console
    $ make -C src
    $ sudo make -C src install
    ```
- Go to the Frontier client code directory and build the client.
  ```console
  $ cd /<LOCALLY_CLONED_WORKING_DIR>/frontier/client
  $ make
  ```

### Client Connection and ConDB2 API Query Testing

- Now that you have the client code built locally, you can test ConDB2 API queries through the entire Frontier stack that you set up in previous steps:
  ```
  Frontier client >> Squid local cache proxy >> Squid reverse proxy >> Frontier server >> ConDB2 API server
  ```
- From the local Frontier client source directory, use the `fn-fileget` CLI.
  - Make sure that `$LD_LIBRARY_PATH` includes the Frontier client directory.
    ```console
    $ export LD_LIBRARY_PATH=/<LOCALLY_CLONED_WORKING_DIR>/frontier/client:$LD_LIBRARY_PATH
    ```
  - Test the CLI to make sure it executes correctly.
    ```console
    $ ./fn-fileget
    No files requested
    Usage: fn-fileget [-c connect_string] [-r|-R] filepath ...
      -c connect_string: use given connect_string (default from environment)
      -r: request short time-to-live
      -R: request forever time-to-live
    ```
  - Test a ConDB2 API query with `fn-fileget`. *Note: This requires a FNAL VPN connection.*
    ```console
    $ ./fn-fileget -c "(serverurl=http://fermicloud725.fnal.gov:8000/dune_runcon_prod)(proxyurl=http://localhost:3128)" "get?folder=pdunesp.run_conditionstest&t=28650"
    753 bytes written to get?folder=pdunesp.run_conditionstest&t=28650
    ```
    - You should see the cache miss / hit in `/var/log/squid/access.log`.
      ```log
      127.0.0.1 - - [17/Dec/2025:10:59:41.942 -0700] "GET http://fermicloud725.fnal.gov:8000/dune_runcon_prod/Frontier/type=frontier_file:1:DEFAULT&encoding=BLOB&p1=get%253ffolder%253dpdunesp.run_conditionstest%2526t%253d28650 HTTP/1.0" 200 1847 TCP_MISS:HIER_DIRECT 355 "client 2.10.2 208346 mike(1000) -" "-" "-"

      127.0.0.1 - - [17/Dec/2025:11:01:19.396 -0700] "GET http://fermicloud725.fnal.gov:8000/dune_runcon_prod/Frontier/type=frontier_file:1:DEFAULT&encoding=BLOB&p1=get%253ffolder%253dpdunesp.run_conditionstest%2526t%253d28650 HTTP/1.0" 200 1848 TCP_HIT:HIER_NONE 0 "client 2.10.2 208792 mike(1000) -" "-" "-"
      ```
  - The response from the above query will dump a CSV file with a name reflecting the `filepath` that you provided in the CLI call; E.g., `'get?folder=pdunesp.run_conditionstest&t=28650'`.
    - Change the filename to `<something>.csv`.
    - Open the file and you should see the query results in CSV format.
