# frontier-condb2-test
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
