import click
import ezdnac
import osls
import tabulate
import json

settings_file = ".ezdnac_cli_settings.py"
try:
	with open(settings_file) as file:
			settings = json.load(file)
except:
	DNA_IP = None
	DNA_USER = None
	AUTHTOKEN = None
try:
	DNA_IP = settings['DNA_IP'] 
	DNA_USER = settings['DNA_USER']
	AUTHTOKEN = settings['authToken']
except:
	pass

def initDnac():
	global dnac
	if DNA_IP == None or DNA_USER == None or AUTHTOKEN == None:
		print ("Login details not set. Use login command to login first")
		exit(1)
	else:
		dnac = ezdnac.apic(DNA_IP, DNA_USER, authToken=AUTHTOKEN)


@click.group()
def cli():
    """Command line tool for deploying templates to CISCO DNA-C.
    """
    pass

@click.command()
@click.option("--ip")

def login(ip):
	DNA_USER = click.prompt("username")	
	DNA_PW = click.prompt("password", hide_input=True)
	settings = {}
	settings['DNA_IP'] = ip
	settings['DNA_USER'] = DNA_USER

	if ip == None:
		DNA_IP = click.prompt("DNA-C IP")

	dnac = ezdnac.apic(DNA_IP, DNA_USER, pw=DNA_PW)
	settings['authToken'] = dnac.authToken
	settings['DNA_IP'] = DNA_IP
	settings['DNA_USER'] = DNA_USER
	
	with open(settings_file, 'w+') as out:
		out.write(str(json.dumps(settings)))
	click.secho("Credentials set for user" + DNA_USER)

@click.group()
def show():
	initDnac()
	pass

@show.command()
def pnpq():
	initDnac()

	with open(settings_file) as file:
		settings = json.load(file)
	try:
		DNA_IP = settings['DNA_IP']
		authToken = settings['authToken']
	except:
		click.secho("Credentials not set or expired. Use ezdnac login to reset.")
	click.secho("Retrieving the devices in PnP queue.")
		
	deviceList = []
	devices = dnac.getPnpDevices()

	for device in devices:
		dev = device['deviceInfo']
		deviceData = dev['serialNumber'] , dev['pid'], dev['state']	
		try:
			deviceDat2 = (*deviceData, dev['macAddress'])
		except:
			deviceDat2 = (*deviceData, "00:00:00:00:00:00")

		deviceList.append(deviceDat2)

	headers = ["Serial Number", "Device Type", "State", "Mac"]
	click.echo(tabulate.tabulate(deviceList, headers, tablefmt="fancy_grid"))


@show.command()
def inventory():
	initDnac()
	data = dnac.getAllDevices()
	
	deviceList = []
	for device in data['response']:
		hostname = device['hostname']
		serialNumber = device['serialNumber']
		mac = device['macAddress']
		ip = device['managementIpAddress']
		pid = device['platformId']
		deviceData = [hostname, ip, mac, pid, serialNumber]
		deviceList.append(deviceData)	
	
	headers = ['Hostname', "MGMT IP", "MAC", "Pid", "Serial Number"]
	click.echo(tabulate.tabulate(deviceList, headers, tablefmt="fancy_grid"))	


@show.group()
def device():
	pass

@device.command()
def neighbors():
	initDnac()
	click.echo("show neighbors...")
	serialNumber =click.prompt("serialNumber")

	device = ezdnac.device(dnac, sn=serialNumber)
	click.secho("Retrieving the neighbors for device with serial: " + serialNumber)

	neighbors = device.getTopology()

	topo = []
	if len(neighbors) == 0:
		print ("No neighbors!")
	else:
		for neighbor in neighbors:
			neihgId = neighbor['remotenode']
			neighIntf = neighbor['remoteif']
			localIntf = neighbor['sourceif']
			neig = ezdnac.device(dnac, id=neihgId)
			
			linkData = [localIntf, neig.hostname, neighIntf]

			topo.append(linkData)
			
	headers = ['Local Interface', 'Connected to hostname', 'Neighbor Interface']
	click.echo(tabulate.tabulate(topo, headers, tablefmt="fancy_grid"))

@device.command()
def details():
	initDnac()
	serialNumber =click.prompt("serialNumber")

	device = ezdnac.device(dnac, sn=serialNumber)
	click.secho("Retrieving the neighbors for device with serial: " + serialNumber)
	
	headers = ['Hostname', 'Mgmgt IP', 'PID', 'Software', 'Version']

	print (device.initMethod)
	print (device.ip)
	exit()
	data = [[device.hostname, device.ip, device.platform, device.softwareType, device.softwareVersion]]

	click.echo(tabulate.tabulate(data, headers, tablefmt='fancy_grid'))



cli.add_command(device)
cli.add_command(show)
cli.add_command(neighbors)
cli.add_command(details)
cli.add_command(pnpq)
cli.add_command(login)

if __name__ == "__main__":
    cli()