import sys
import json
import requests
import getpass
from imcsdk.imchandle import ImcHandle

if __name__ == "__main__":
    try:
        # settings are pulled from settings file passed in as arg1
        if len(sys.argv) < 2:
            print "Usage: %s <settings_file>" % sys.argv[0]
            sys.exit(0)
        f = open(sys.argv[1], 'r')
        settings_file = json.load(f)
	is_secure = True

        # Redfish API operations
	# ----------------------
	base_uri = "https://%s" % settings_file['ip']
	
	systems_uri = "%s/redfish/v1/Systems" % base_uri
	ro = requests.get(systems_uri, verify=False, auth=(settings_file['user'], settings_file['pw']))
	ro_json = ro.json()
	
	# query system and print Model, SerialNumber, and BiosVersion
	system0_uri = "%s%s" % (base_uri, ro_json['Members'][0]['@odata.id'])
	print "Query System 0, URI %s" % system0_uri
       	ro = requests.get(system0_uri, verify=False, auth=(settings_file['user'], settings_file['pw']))
	ro_json = ro.json()
	print "  Model: %s" % ro_json['Model']
	print "  SerialNumber: %s" % ro_json['SerialNumber']
	print "  BiosVersion: %s" % ro_json['BiosVersion']
	pause = raw_input()
	
	# query storage controller and print disk info
	simple_storage_uri = "%s%s" % (base_uri, ro_json['SimpleStorage']['@odata.id'])
       	ro = requests.get(simple_storage_uri, verify=False, auth=(settings_file['user'], settings_file['pw']))
	ro_json = ro.json()
	storage0_uri = "%s%s" % (base_uri, ro_json['Members'][0]['@odata.id'])
	print "Query Storage 0, URI %s" % storage0_uri
       	ro = requests.get(storage0_uri, verify=False, auth=(settings_file['user'], settings_file['pw']))
	ro_json = ro.json()
	print "  Storage 0 Name: %s" % ro_json['Name']
	num_good_disks = 0
	for device in ro_json['Devices']:
	    if device['Status']['State'] == 'Enabled' and device['Status']['Health'] == 'OK':
                print "    Disk %s is Enabled and OK" % device['Name']
		num_good_disks += 1
	print "  Number of Enabled, OK disks: %d" % num_good_disks
	pause = raw_input('')

        # IMC XML API operations
	# ----------------------
	# setup RAID as specified in settings file
	handle = ImcHandle(settings_file['ip'], settings_file['user'], settings_file['pw'], secure=is_secure)
        handle.login()

	from imcsdk.mometa.storage.StorageVirtualDriveCreatorUsingUnusedPhysicalDrive import StorageVirtualDriveCreatorUsingUnusedPhysicalDrive
	
	for raid_params in settings_file['raid_config']:
	    print "Create virtual drive %s with RAID level %s" % (raid_params['drive_name'], raid_params['raid_level'])
	    mo = StorageVirtualDriveCreatorUsingUnusedPhysicalDrive(parent_mo_or_dn=raid_params['dn'], virtual_drive_name=raid_params['drive_name'], raid_level=raid_params['raid_level'], size=raid_params['size'], drive_group=raid_params['drive_group'], write_policy="Write Through", admin_state="trigger")
            handle.set_mo(mo)
            
	    if raid_params['boot_drive'] == 'yes':
	       print "Set virtual drive %s as boot drive" % raid_params['drive_name']
	       from imcsdk.mometa.storage.StorageVirtualDrive import StorageVirtualDrive
	       mo = StorageVirtualDrive(parent_mo_or_dn=raid_params['dn'], id="0", admin_action="set-boot-drive")
               handle.set_mo(mo)
        handle.logout()
	pause = raw_input('')
        
	
	# Redfish API operations
        # ----------------------
        # check CIMC fw version and update if not at desired version
	cimc_uri = "%s/redfish/v1/Managers/CIMC" % base_uri
       	ro = requests.get(cimc_uri, verify=False, auth=(settings_file['user'], settings_file['pw']))
	ro_json = ro.json()
        if ro_json['FirmwareVersion'] != settings_file['fw_config']['cimc_version']:
	    print "Current CIMC version %s, but desired version is %s" % (ro_json['FirmwareVersion'], settings_file['fw_config']['cimc_version'])
	    do_update = raw_input('Do you want to perform a CIMC update (y/N) ')
	    if do_update == 'y':
	        fwu_user = raw_input('Enter remote server username: ')
		fwu_pass = getpass.getpass('Enter remote server password: ')

	        print "Updating CIMC to version %s" % settings_file['fw_config']['cimc_version']
	        cimc_update_uri = "%s/redfish/v1/Managers/CIMC/Actions/Oem.BmcFwUpdate" % base_uri
            
	        fo = {'Protocol': settings_file['fw_config']['protocol'], 'RemoteUsername': fwu_user, 'RemotePath': settings_file['fw_config']['fwu_path'], 'RemoteHostname': settings_file['fw_config']['fwu_ip'], 'RemotePassword': fwu_pass }
	    
	        ro = requests.post(cimc_update_uri, json=fo, verify=False, auth=(settings_file['user'], settings_file['pw']))
	        print "Status Code:     {}".format(ro.status_code)
	
	pause = raw_input('')

    except Exception, err:
        print "Exception:", str(err)
        import traceback, sys
        print '-'*60
        traceback.print_exc(file=sys.stdout)
        print '-'*60
	if 'handle' in locals() or 'handle' in globals():
	    handle.logout()
