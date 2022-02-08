# Find Commvault orphaned NetApp Snapshots

Commvault is a fantastic system for managing your backups.  As everything has quirks, one of the quirks I've run into with using Intellisnap
is that sometimes Commvault will leave orphaned snapshots on a NetApp that requires manual cleanups.  This script attempts to compare active
job id's in Commvault against the job id's used in the NetApp snapshot names.  If it finds any orphaned snapshots, it outputs a bash script
that you can visually inspect and validate the list of deletions before you run the script.  In order to use this system, you will want to
create an account on the NetApp that has at least read-only access via the API, and you will want to create an account on your Commvault DB
that has read-only access to the CommServ database.<br>

# Setting up your environment to use this script

Requires the pytz, netapp_ontap, pandas, and pyodbc libraries.<br>
The mssqlodbc driver for linux can be found at https://docs.microsoft.com/en-us/sql/connect/odbc/linux-mac/installing-the-microsoft-odbc-driver-for-sql-server<br>
Info about the netapp_ontap python library can be found at https://pypi.org/project/netapp-ontap/<br>
If you run into an SSL connection issue with trying to connect to an older release of MSSQL, try adding the following to your openssl.cnf file:<br>

At the beginning of the file:<br>
```
openssl_conf = default_conf
```
<br>
At the end of the file:<br>
```
[ default_conf ]

ssl_conf = ssl_sect

[ssl_sect]

system_default = system_default_sect

[system_default_sect]
MinProtocol = TLSv1
CipherString = DEFAULT:@SECLEVEL=1
```
<br>
Please note that you are configuring OpenSSL to utilize insecure SSL protocols by making this change, inherently making your system less secure.<br>