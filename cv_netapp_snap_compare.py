#!/usr/bin/python3

####################################################################################################################
# The purpose of this script is to pull active job id's from the Commvault database that have a status of either   #
# "Successful" or "Successful with issues" that have not aged out, and then compare them to the job id's listed in #
# the NetApp snapshot names.  All snapshots that do not have an "active" job id wil be listed in a generated bash  #
# shell script that can be manually verified and then run in order to delete unused snapshots.                     #
####################################################################################################################


# Datetime is being used to compare snapshot creation date vs an arbitrary date set in the script
import datetime
# pytz is for setting the timezone for this script in order to determine dates/times of snapshots
import pytz
# netapp_ontap resources for utilizing the NetApp API
from netapp_ontap import ( config, HostConnection )
from netapp_ontap.resources import ( Snapshot, Volume )
# Python ODBC driver in support of the CommServ DB query connection
import pyodbc
# Pandas is used to turn SQL output from a column into an array for string comparisons
import pandas

### Database connection setup.
# Database driver name found in /etc/odbcinst.ini
dbdriver = 'ODBC Driver 17 for SQL Server'
# Hostname of Commvault DB Server
dbhostname = 'hostname'
# If using default DB install for Commvault, this will connect to the instance instead of a specific port.  Default instance name is 'COMMVAULT'
dbinstance = 'COMMVAULT'
# The database name.  The default is 'CommServ'
dbdatabase = 'CommServ'
# Database username and password.
dbusername = 'dbusername'
dbpassword = 'dbpassword'

# Array of hostnames for each NetApp cluster.  Uses the API so account should have at least read access via API to all SVM's.
netapps = ['netapp1', 'netapp2', 'netapp3']
# Builds FQDN from netapps array and domain variable
domain = "example.com"
# NetApp username and password
nauser = 'nausername'
napasswd = 'napassword'

# Timezone needs to be set in order to use datetime command functionality
timezone = "US/Eastern"
# If you only want to check snapshots older than a week, leave this at the default of "7"
days = 7

# Sets the timezone and then sets a variable used to compare snapshot creation date/time
# The script filters out any snapshots younger than a week old to make sure there is no race condition
# as long as the CommVault report has been run within the past couple of days.
est = pytz.timezone(timezone)
snapdatenewest = est.localize(datetime.datetime.now()) - datetime.timedelta(days)

# MSSQL call to pull all jobs that aren't aged out and have a status of "successful" or "partially successful"
cnxn = pyodbc.connect('DRIVER={' + dbdriver + '};SERVER=' + dbhostname + "\\" + dbinstance + ';DATABASE=' + dbdatabase + ';UID=' + dbusername + ';PWD=' + dbpassword + ';sslverify=0')
cursor = cnxn.cursor()
cursorQuery = "SELECT jobid FROM[CommServ].[dbo].[CommCellBackupInfo] WHERE (jobstatusInt=1 OR jobstatusInt=3) AND isAged=0"
# Utilizing pandas to put all the valid job id's into a single array for a string comparison.
df = pandas.read_sql(cursorQuery, cnxn)
jobids = sorted(list(map(int, set(df['jobid'].to_csv(index=False, header=False).split()))))

# Loops through all entries in hostnames list to pull data from all NetApp clusters
for netapp in netapps:
	# Create list for use in eventual bash script outpout.  This will set the first line in the script.
	cmdsout = ['#!/usr/bin/bash']
	netappFQDN = netapp + "." + domain
	# Sets the connection info for later API calls
	config.CONNECTION = HostConnection(netappFQDN, username=nauser, password=napasswd, verify=False)
	# Uses the NetApp API to pull a list of volume names and adds the SVM info for the volume to the list of fields it parses.
	naVolumes = list(Volume.get_collection(fields="svm"))
	# Loops through a list sorted by volume names.  List is sorted to make resulting output easier to manually parse.
	for volume in sorted(naVolumes, key=lambda x: x.name):
		# Gets a list of snapshots for each volume using the uuid.
		# Also getting the snapshot creation time for each snap
		naosnapshots = list(Snapshot.get_collection(volume.uuid, fields="create_time"))
		# Loops through snapshots, sorted by snapshot name to hopefully make it easier to manually parse.
		for snapshot in sorted(naosnapshots, key=lambda x: x.name):
			# CommVault snapshots start with the characters "SP_"
			if snapshot.name.startswith("SP_"):
				# Pulls out the third field from the snapshot name, which should be the CommVault job ID
				# If the job ID doesn't exist in the jobids list and is older than a week (set in the snapdatenewest variable),
				# the script outputs an ssh command to delete the snapshot.
				if int(snapshot.name.split("_")[2]) not in jobids and snapshot.create_time < snapdatenewest:
					cmdsout.append(str('ssh admin@' + netappFQDN + ' "snapshot delete -vserver ' + volume.svm.name + ' -volume ' + volume.name + ' -snapshot ' + snapshot.name + '" #'+ str(snapshot.create_time)))

	# Takes output from the loop that creates each SSH command to delete a snap and outputs it into a bash script
	cmdsbashout = netapp + ".snapdelete.sh"
	with open (cmdsbashout, 'w') as cmdsbashoutf:
		for cmdout in cmdsout:
			print(cmdout, file=cmdsbashoutf)